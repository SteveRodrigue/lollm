#!/usr/bin/env python3
"""Long-context tests for Strata: 128K recall, and "128K + N" (a 128K prompt, then a very long answer).

    .venv\\Scripts\\python.exe tools\\strata_longctx.py --variant no-kv-grow --stages needle
    .venv\\Scripts\\python.exe tools\\strata_longctx.py --variant no-kv-grow --stages gen --context 163840 --gen 32768
    .venv\\Scripts\\python.exe tools\\strata_longctx.py --variant no-kv-grow --stages gen --context 196608 --gen 65536

Starts Strata with a variant of the project config (the variants of tools/strata_bench_matrix.py) and, for `needle`,
runs Strata's tools/needle_bench.py at 32K and 128K (does the server start at 131072, how long is the prompt, is the
hidden code word found). For `gen` it sends a ~128K prompt with a unique tag (so no cached prefix helps) and asks for a
very long answer, streaming it: it records the time to the first token (= prompt ingestion), decode speed per 2,048
tokens as the context fills, how far the answer got and why it stopped, a repetition check (a long answer that loops
shows a low share of distinct 8-grams), and peak RAM and VRAM. One run each: these are long.
Output: reports/strata-bench/longctx/<stamp>-<variant>-<stage>-<context>/results.json and README.md
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STRATA = REPO / "runtimes" / "strata"
sys.path.insert(0, str(STRATA / "tools"))
sys.path.insert(0, str(REPO / "tools"))
import needle_bench                          # noqa: E402
import strata_bench                          # noqa: E402
import strata_bench_matrix as mx             # noqa: E402
import gpu_guard                              # noqa: E402

SLICE = 2048


class Monitor(threading.Thread):
    """Peak system RAM in use and peak GPU memory used, sampled every 5 s."""

    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = threading.Event()
        self.ram = 0.0
        self.vram = 0

    def run(self):
        import psutil
        while not self.stop_flag.is_set():
            vm = psutil.virtual_memory()
            self.ram = max(self.ram, (vm.total - vm.available) / 2 ** 30)
            out = strata_bench.run_cmd(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"])
            try:
                self.vram = max(self.vram, int(out.split()[0]))
            except (ValueError, IndexError):
                pass
            self.stop_flag.wait(5)


def stream_long(url: str, prompt: str, max_tokens: int, timeout: float) -> dict:
    body = {"model": "strata", "stream": True, "max_tokens": max_tokens, "temperature": 0.7, "top_p": 0.95,
            "chat_template_kwargs": {"enable_thinking": False}, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(url + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first, pieces, marks, text, finish, usage, timings, err = None, 0, [], [], None, None, None, None
    last_t = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                d = line[5:].strip()
                if d == "[DONE]":
                    break
                try:
                    j = json.loads(d)
                except ValueError:
                    continue
                if j.get("error"):
                    err = str(j["error"])[:300]
                for ch in j.get("choices") or []:
                    dl = ch.get("delta") or {}
                    piece = (dl.get("content") or "") + (dl.get("reasoning_content") or "")
                    if piece:
                        now = time.perf_counter() - t0
                        if first is None:
                            first = last_t = now
                        pieces += 1
                        text.append(dl.get("content") or "")
                        if pieces % SLICE == 0:
                            marks.append({"tokens": pieces, "slice_tps": round(SLICE / (now - last_t), 2), "elapsed_s": round(now, 1)})
                            last_t = now
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
                if j.get("usage"):
                    usage = j["usage"]
                if j.get("timings"):
                    timings = j["timings"]
    except Exception as e:                                   # noqa: BLE001
        err = repr(e)[:300]
    full = "".join(text)
    words = full.split()
    grams = [" ".join(words[i:i + 8]) for i in range(0, max(0, len(words) - 8))]
    return {"first_token_s": round(first, 1) if first else None, "total_s": round(time.perf_counter() - t0, 1), "pieces": pieces,
            "slices": marks, "finish_reason": finish, "usage": usage, "timings": timings, "error": err, "words": len(words),
            "distinct_8gram_share": round(len(set(grams)) / len(grams), 3) if grams else None, "tail": full[-400:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", default="no-kv-grow", help="a variant of strata_bench_matrix.VARIANTS")
    ap.add_argument("--stages", default="needle", help="needle, gen or needle,gen")
    ap.add_argument("--context", type=int, help="override --max-context (e.g. 163840 for 128K+32K, 196608 for 128K+64K)")
    ap.add_argument("--gen", type=int, default=32768, help="max tokens to generate in the gen stage")
    ap.add_argument("--prompt-tokens", type=int, default=128000)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--warmup", action="store_true", help="send one short request first, so the engine is up before the long prompt")
    ap.add_argument("--config", default=str(REPO / "configs" / "strata-iq2_xs.json"))
    ap.add_argument("--ready-timeout", type=float, default=1800)
    ap.add_argument("--timeout", type=float, default=14400)
    a = ap.parse_args()

    cfg = mx.absolutize(json.loads(Path(a.config).read_text(encoding="utf-8-sig")), REPO)
    mx.VARIANTS[a.variant][1](cfg)
    if a.context:
        cfg["args"] = mx.set_flag(cfg["args"], "--max-context", str(a.context))
    mx.apply_draft_vocab(cfg)
    ctx = int(cfg["args"][cfg["args"].index("--max-context") + 1])
    stamp = f"{datetime.datetime.now():%Y%m%d-%H%M}"
    out = REPO / "reports" / "strata-bench" / "longctx" / f"{stamp}-{a.variant}-{a.stages.replace(',', '+')}-{ctx}"
    out.mkdir(parents=True, exist_ok=True)
    cfg_file = out / "config.json"
    cfg_file.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    base = f"http://127.0.0.1:{a.port}"
    log = out / "server.log"
    res: dict = {"variant": a.variant, "context": ctx, "stages": a.stages, "date": datetime.date.today().isoformat(),
                 "launch": strata_bench.launch_line(strata_bench.config_view(cfg))}
    gpu_guard.require_free_port(a.port)
    res["available_vram_mib_before_start"] = gpu_guard.gpu_free_mib()
    res["desktop_vram_used_mib_before_start"] = gpu_guard.gpu_used_mib()
    lock = gpu_guard.GpuLock("longctx").__enter__()
    mon = Monitor()
    mon.start()
    t0 = time.time()
    proc = strata_bench.start_server(cfg_file, a.port, None, log)
    try:
        res["started"] = strata_bench.wait_ready(base, "", proc, a.ready_timeout)
        res["load_s"] = round(time.time() - t0)
        if res["started"]:
            res["identity"] = gpu_guard.verify_identity(base, cfg)
        if not res["started"]:
            res["server_log_tail"] = strata_bench.log_excerpt(log, 30)
        else:
            if a.warmup:                                     # the engine starts on the first request: start it with a short one
                wb = json.dumps({"model": "strata", "max_tokens": 16, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False},
                                 "messages": [{"role": "user", "content": "Say hello."}]}).encode()
                try:
                    urllib.request.urlopen(urllib.request.Request(base + "/v1/chat/completions", data=wb, headers={"Content-Type": "application/json"}), timeout=1800).read()
                    res["warmup"] = "ok"
                except Exception as e:                       # noqa: BLE001
                    res["warmup"] = repr(e)[:200]
            if "needle" in a.stages:
                nfile = out / "needle.json"
                r = subprocess.run([sys.executable, str(STRATA / "tools" / "needle_bench.py"), "--url", base, "--lengths", "32k,128k",
                                    "--depths", "50", "--timeout", str(a.timeout), "--out", str(nfile)], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
                res["needle_console"] = r.stdout[-1500:]
                res["needle"] = json.loads(nfile.read_text(encoding="utf-8")) if nfile.exists() else None
            if "gen" in a.stages:
                tag = f"Session tag {random.Random().randint(10**8, 10**9)}\n\n"
                text = needle_bench.haystack(int(a.prompt_tokens * needle_bench.CHARS_PER_TOKEN))
                prompt = (tag + text + f"\n\nUsing everything above as background, write an exhaustive, deeply detailed technical manual about "
                          f"this system. Cover every component in its own numbered section with subsections, examples and code. Do not "
                          f"summarise and do not stop; keep writing new material until you have written at least {a.gen // 2} words.")
                res["gen"] = stream_long(base, prompt, a.gen, a.timeout)
    finally:
        mon.stop_flag.set()
        strata_bench.stop_server(proc)
    lock.release()
    res["warnings"] = gpu_guard.sanity_warnings(peak_ram_gib=mon.ram, started=bool(res.get("started")))
    res["peak_ram_used_gib"] = round(mon.ram, 1)
    res["peak_vram_used_mib"] = mon.vram
    (out / "results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = [f"# Long-context run: {a.variant}, context {ctx}", "", f"Stages: {a.stages}. Date {res['date']}. Started: {res.get('started')}, load {res.get('load_s')} s.",
         f"Peak RAM in use {res['peak_ram_used_gib']} GiB, peak GPU memory {res['peak_vram_used_mib']} MiB.", ""]
    if res.get("needle"):
        L += ["## Needle recall (depth 50%)", "", "| Length | Found | Prompt tokens | Seconds |", "| --- | --- | ---: | ---: |"]
        L += [f"| {n.get('length')} | {n.get('found')} | {n.get('prompt_tokens', '-')} | {n.get('seconds', '-')} |" for n in res["needle"]]
        L.append("")
    g = res.get("gen")
    if g:
        u = g.get("usage") or {}
        L += ["## Long answer", "", f"Prompt tokens {u.get('prompt_tokens')}, generated {g['pieces']}, stopped: {g['finish_reason']}, error: {g['error']}.",
              f"First token after {g['first_token_s']} s (prompt ingestion); total {g['total_s']} s; distinct 8-grams {g['distinct_8gram_share']}.", "",
              "| Generated tokens | Decode tok/s (last 2,048) | Elapsed s |", "| ---: | ---: | ---: |"]
        L += [f"| {m['tokens']} | {m['slice_tps']} | {m['elapsed_s']} |" for m in g["slices"]]
    (out / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
