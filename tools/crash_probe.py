#!/usr/bin/env python3
"""Does a warm-up request or a bigger VRAM reserve avoid the engine exit on the first long request?

    .venv\\Scripts\\python.exe tools\\crash_probe.py [--trials 3] [--tokens 32768] [--config configs\\strata-coder-iq1_m.json]

For every condition and trial it starts a fresh Strata server, optionally sends a short warm-up request, then sends ONE
long needle prompt (about --tokens tokens, from Strata's needle_bench) and records whether the answer came back or the
engine exited (HTTP 503 / 'stopped unexpectedly'), the 'only N MiB of VRAM free' figure from the server log and the GPU
memory the desktop used before the start. Conditions: cold reserve 1024 (control), warm-up reserve 1024, cold reserve 1200,
cold reserve 1300, warm-up reserve 1300. The answer text is checked for the hidden code word.
Output: reports/strata-bench/crash-probe/<stamp>/results.json and README.md
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "runtimes" / "strata" / "tools"))
sys.path.insert(0, str(REPO / "tools"))
import gpu_guard                          # noqa: E402
import needle_bench                       # noqa: E402
import strata_bench                       # noqa: E402
import strata_bench_matrix as mx          # noqa: E402

CONDITIONS = [("cold-1024", "baseline", False), ("warmup-1024", "baseline", True), ("cold-1200", "reserve-1200", False),
              ("cold-1300", "reserve-1300", False), ("warmup-1300", "reserve-1300", True)]


def post(base: str, prompt: str, max_tokens: int, timeout: float) -> tuple[int, str]:
    body = json.dumps({"model": "strata", "max_tokens": max_tokens, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read())
        return 200, (j["choices"][0]["message"].get("content") or "")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:                                         # noqa: BLE001
        return -1, repr(e)[:150]


def wait_gpu_idle(baseline_mib: int | None, timeout: float = 180) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        used = gpu_guard.gpu_used_mib()
        if used is None or baseline_mib is None or used <= baseline_mib + 150:
            return
        time.sleep(5)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(REPO / "configs" / "strata-coder-iq1_m.json"))
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--tokens", type=int, default=32768)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--only", help="comma-separated condition names")
    ap.add_argument("--wait-desktop-below", type=int, default=0, metavar="MIB",
                    help="before each trial wait (up to --max-wait-h hours) until the desktop uses less GPU memory than this, so the trials are comparable")
    ap.add_argument("--max-wait-h", type=float, default=10)
    a = ap.parse_args()
    base_cfg = json.loads(Path(a.config).read_text(encoding="utf-8-sig"))
    out = REPO / "reports" / "strata-bench" / "crash-probe" / f"{datetime.datetime.now():%Y%m%d-%H%M}"
    out.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{a.port}"
    rnd = random.Random(11)
    text = needle_bench.haystack(int(a.tokens * 0.98 * needle_bench.CHARS_PER_TOKEN))
    rows = []
    idle = gpu_guard.gpu_used_mib()
    conds = [c for c in CONDITIONS if not a.only or c[0] in a.only.split(",")]
    for name, variant, warm in conds:
        for trial in range(1, a.trials + 1):
            gpu_guard.require_free_port(a.port)
            t_wait = time.time()
            while a.wait_desktop_below and (gpu_guard.gpu_used_mib() or 0) >= a.wait_desktop_below and time.time() - t_wait < a.max_wait_h * 3600:
                time.sleep(60)
            with gpu_guard.GpuLock(f"crash-probe:{name}", wait_s=36000):
                wait_gpu_idle(idle)
                desktop = gpu_guard.gpu_used_mib()
                cfg = mx.absolutize(base_cfg, REPO)
                mx.VARIANTS[variant][1](cfg)
                mx.apply_draft_vocab(cfg)
                cfg_file = out / f"{name}-{trial}.config.json"
                cfg_file.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
                log = out / f"{name}-{trial}.server.log"
                proc = strata_bench.start_server(cfg_file, a.port, None, log)
                row = {"condition": name, "trial": trial, "desktop_vram_mib": desktop, "available_vram_mib": gpu_guard.gpu_free_mib()}
                try:
                    if not strata_bench.wait_ready(base, "", proc, 900):
                        row["result"] = "did not start"
                    else:
                        gpu_guard.verify_identity(base, cfg)
                        if warm:
                            row["warmup_status"] = post(base, "Say hello.", 16, 1800)[0]
                        word = f"{rnd.choice(needle_bench.WORDS)}-{rnd.choice(needle_bench.WORDS)}-{rnd.randint(100, 999)}"
                        cut = text.rfind("\n", 0, len(text) // 2) + 1
                        prompt = (text[:cut] + f"\nThe secret code word for this text is: {word}. Remember it.\n" + text[cut:] +
                                  "\n\nWhat is the secret code word mentioned in the text above? Reply with the code word only.")
                        t0 = time.time()
                        status, answer = post(base, prompt, 40, 3600)
                        row.update(status=status, seconds=round(time.time() - t0), found=(word in answer))
                        row["result"] = "ok" if status == 200 else ("engine exit (503)" if status == 503 else f"error {status}")
                finally:
                    strata_bench.stop_server(proc)
                try:
                    m = re.findall(r"only (\d+) MiB of VRAM free", log.read_text(encoding="utf-8", errors="replace"))
                    row["vram_free_at_request_mib"] = int(m[-1]) if m else None
                except OSError:
                    pass
            rows.append(row)
            print(f"{name} trial {trial}: {row.get('result')} (desktop {desktop} MiB, free at request {row.get('vram_free_at_request_mib')})", flush=True)
            (out / "results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    L = [f"# Crash probe: first long request after a fresh start ({a.tokens} tokens)", "", f"Date {datetime.date.today()}, config {Path(a.config).name}.", "",
         "| Condition | Trials | OK | Engine exit (503) | Other | Available VRAM at the start (MiB) |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for name, _, _ in conds:
        rs = [r for r in rows if r["condition"] == name]
        ok = sum(r.get("result") == "ok" for r in rs)
        ex = sum(r.get("result") == "engine exit (503)" for r in rs)
        L.append(f"| {name} | {len(rs)} | {ok} | {ex} | {len(rs) - ok - ex} | {', '.join(str(r['available_vram_mib']) for r in rs)} |")
    (out / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
