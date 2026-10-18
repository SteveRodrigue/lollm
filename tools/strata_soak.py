#!/usr/bin/env python3
"""Hello and soak test for a Strata config: does it start, answer, and stay healthy under steady use?

    .venv\\Scripts\\python.exe tools\\strata_soak.py --config configs\\strata-coder-iq1_m.json [--variant no-kv-grow] [--minutes 15]

Starts Strata with the config (optionally a variant of tools/strata_bench_matrix.py), sends a hello, then a steady stream
of short coding questions (one at a time, temperature 0) for --minutes. Records for every request the latency, the
engine's own decode speed, and any error; samples system RAM and GPU memory every 5 s. Passes when the server stays up,
no request fails, no answer is empty or all '!' (NaN logits), and the decode speed does not collapse.
Output: reports/strata-bench/soak/<stamp>-<name>/results.json and README.md
"""
from __future__ import annotations

import argparse
import datetime
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "runtimes" / "strata" / "tools"))
sys.path.insert(0, str(REPO / "tools"))
import strata_bench                      # noqa: E402
import strata_bench_matrix as mx         # noqa: E402
import strata_longctx                    # noqa: E402
import gpu_guard                         # noqa: E402

PROMPTS = [
    "Hello! Reply with one short sentence confirming you are ready.",
    "Write a Python function is_palindrome(s) that ignores case and punctuation. Code only.",
    "Explain in three sentences what a race condition is and give one way to avoid it.",
    "Write a JavaScript function debounce(fn, ms). Code only, with a one-line comment.",
    "What is the time complexity of binary search and why? Two sentences.",
    "Write a SQL query that returns the top 3 customers by total order value from tables customers(id, name) and orders(customer_id, total).",
    "Fix this TypeScript: const xs: number[] = [1,2,3]; const s: string = xs.map(x => x * 2); Show the corrected line only.",
]


def ask(base: str, prompt: str, timeout: float = 900) -> dict:
    body = {"model": "strata", "max_tokens": 200, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read())
    except Exception as e:                                          # noqa: BLE001
        return {"ok": False, "error": repr(e)[:200], "latency_s": round(time.perf_counter() - t0, 2)}
    text = (j["choices"][0]["message"].get("content") or "").strip()
    tm = j.get("timings") or {}
    bad = (not text) or set(text) <= {"!"}
    return {"ok": not bad, "error": "empty or NaN answer" if bad else None, "latency_s": round(time.perf_counter() - t0, 2),
            "decode_tps": tm.get("predicted_per_second"), "prompt_tps": tm.get("prompt_per_second"),
            "completion_tokens": (j.get("usage") or {}).get("completion_tokens"), "text": text[:160]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--variant", default="baseline")
    ap.add_argument("--minutes", type=float, default=15)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--ready-timeout", type=float, default=1800)
    a = ap.parse_args()

    cfg = mx.absolutize(json.loads(Path(a.config).read_text(encoding="utf-8-sig")), REPO)
    mx.VARIANTS[a.variant][1](cfg)
    mx.apply_draft_vocab(cfg)
    name = f"{Path(a.config).stem}-{a.variant}"
    out = REPO / "reports" / "strata-bench" / "soak" / f"{datetime.datetime.now():%Y%m%d-%H%M}-{name}"
    out.mkdir(parents=True, exist_ok=True)
    cfg_file = out / "config.json"
    cfg_file.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    base = f"http://127.0.0.1:{a.port}"
    gpu_guard.require_free_port(a.port)
    lock = gpu_guard.GpuLock("soak").__enter__()
    mon = strata_longctx.Monitor()
    mon.start()
    t0 = time.time()
    proc = strata_bench.start_server(cfg_file, a.port, None, out / "server.log")
    res: dict = {"available_vram_mib_before_start": gpu_guard.gpu_free_mib(), "desktop_vram_used_mib_before_start": gpu_guard.gpu_used_mib(), "config": name, "date": datetime.date.today().isoformat(), "requests": []}
    try:
        res["started"] = strata_bench.wait_ready(base, "", proc, a.ready_timeout)
        res["load_s"] = round(time.time() - t0)
        if res["started"]:
            res["identity"] = gpu_guard.verify_identity(base, cfg)
        if not res["started"]:
            res["server_log_tail"] = strata_bench.log_excerpt(out / "server.log", 30)
        else:
            res["hello"] = ask(base, PROMPTS[0])
            end, i = time.time() + a.minutes * 60, 0
            while time.time() < end:
                r = ask(base, PROMPTS[i % len(PROMPTS)])
                r["t_s"] = round(time.time() - t0)
                res["requests"].append(r)
                i += 1
                if proc.poll() is not None:
                    res["server_died"] = True
                    break
    finally:
        mon.stop_flag.set()
        strata_bench.stop_server(proc)
    rq = res["requests"]
    tps = [r["decode_tps"] for r in rq if r.get("decode_tps")]
    third = max(1, len(tps) // 3)
    res["summary"] = {
        "requests": len(rq), "failures": sum(1 for r in rq if not r["ok"]), "server_died": res.get("server_died", False),
        "decode_tps_median": round(statistics.median(tps), 1) if tps else None,
        "decode_tps_first_third": round(statistics.median(tps[:third]), 1) if tps else None,
        "decode_tps_last_third": round(statistics.median(tps[-third:]), 1) if tps else None,
        "latency_p95_s": round(sorted(r["latency_s"] for r in rq)[int(0.95 * (len(rq) - 1))], 1) if rq else None,
        "peak_ram_used_gib": round(mon.ram, 1), "peak_vram_used_mib": mon.vram}
    s = res["summary"]
    res["warnings"] = gpu_guard.sanity_warnings(peak_ram_gib=mon.ram, started=bool(res.get("started")))
    lock.release()
    res["passed"] = bool(res.get("started") and res["hello"]["ok"] and rq and not s["failures"] and not s["server_died"]
                         and tps and s["decode_tps_last_third"] >= 0.6 * s["decode_tps_first_third"])
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = [f"# Soak test: {name}", "", f"Started: {res.get('started')} (load {res.get('load_s')} s). Hello: {res.get('hello', {}).get('text')!r}", "",
         f"**{'PASS' if res['passed'] else 'FAIL'}**", "", "| Metric | Value |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in s.items()]
    (out / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nWrote {out}")
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
