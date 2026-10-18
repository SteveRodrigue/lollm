#!/usr/bin/env python3
"""How much GPU memory can the desktop use before a Strata setup stops fitting?

    python tools/fit_sweep.py [--targets 600,800,1000,1200,1400] [--prompt-tokens 24000] [--only coder-131072,iq2-131072]

For every setup (model x context window) and every target amount of "other" VRAM use, it adds a ballast (tools/vram_ballast.py) so that
the GPU memory used by everything except Strata equals the target, starts a fresh Strata server, sends a short request (starts the engine),
then ONE long needle prompt, and records: did the engine start, did the long request answer (code word found) or did the engine exit
(HTTP 503), and the 'only N MiB of VRAM free' figure from the server log. A setup is skipped for higher targets after two failures to
start in a row. Needs the GPU to itself (takes the GPU lock) and a desktop that already uses less than the lowest target.
Output: reports/strata-bench/fit-sweep/<stamp>/results.json and README.md (a table: setup x other-VRAM-use).
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "runtimes" / "strata" / "tools"))
sys.path.insert(0, str(REPO / "tools"))
import crash_probe                         # noqa: E402  (post, wait_gpu_idle)
import gpu_guard                           # noqa: E402
import needle_bench                        # noqa: E402
import strata_bench                        # noqa: E402
import strata_bench_matrix as mx           # noqa: E402

CODER, IQ2 = str(REPO / "configs" / "strata-coder-iq1_m.json"), str(REPO / "configs" / "strata-iq2_xs.json")
IQ3 = str(REPO / "configs" / "strata-iq3_xxs.json")
SETUPS = {f"{m}-{c}": (cfg, c) for m, cfg in (("coder", CODER), ("iq2", IQ2), ("iq3", IQ3)) for c in (196608, 163840, 131072, 65536, 32768)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targets", default="600,800,1000,1200,1400", help="total MiB used by everything except Strata")
    ap.add_argument("--prompt-tokens", type=int, default=24000)
    ap.add_argument("--only", help="comma-separated setup names, e.g. coder-131072,iq2-65536")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-kv-grow", action="store_true",
                    help="remove --kv-grow (the KV cache is reserved up front): the semantics tools/strata_fit_launch.py assumes")
    ap.add_argument("--head-alias", action="store_true", help="add --short-read 0 --prefill-head-alias (the fast mode); combine with --no-kv-grow")
    a = ap.parse_args()
    targets = [int(x) for x in a.targets.split(",")]
    out = REPO / "reports" / "strata-bench" / "fit-sweep" / f"{datetime.datetime.now():%Y%m%d-%H%M}{'-nokvgrow' if a.no_kv_grow else ''}{'-headalias' if a.head_alias else ''}"
    out.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{a.port}"
    text = needle_bench.haystack(int(a.prompt_tokens * needle_bench.CHARS_PER_TOKEN))
    rnd = random.Random(5)
    total_mib = int(subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], capture_output=True,
                                   text=True, stdin=subprocess.DEVNULL).stdout.split()[0])
    rows = []
    names = [n for n in SETUPS if not a.only or n in a.only.split(",")]
    for name in names:
        cfg_path, ctx = SETUPS[name]
        fails_in_a_row = 0
        for target in targets:
            if fails_in_a_row >= 2:
                rows.append({"setup": name, "target_mib": target, "result": "skipped (two failures below)"})
                continue
            gpu_guard.require_free_port(a.port)
            with gpu_guard.GpuLock(f"fit-sweep:{name}:{target}", wait_s=36000):
                desktop = gpu_guard.gpu_used_mib() or 0
                row = {"setup": name, "target_mib": target, "desktop_mib": desktop}
                ballast = None
                log = out / f"{name}-{target}.server.log"
                if desktop > target:
                    row["result"] = "desktop already above target"
                else:
                    need = (target - desktop) // 64 * 64
                    if need:
                        ballast = subprocess.Popen([sys.executable, str(REPO / "tools" / "vram_ballast.py"), "--mib", str(need)],
                                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, stdin=subprocess.DEVNULL)
                        ballast.stdout.readline()                    # READY
                    time.sleep(3)
                    row["others_mib"] = gpu_guard.gpu_used_mib()
                    cfg = mx.absolutize(json.loads(Path(cfg_path).read_text(encoding="utf-8-sig")), REPO)
                    cfg["args"] = mx.set_flag(cfg["args"], "--max-context", str(ctx))
                    if a.no_kv_grow:
                        cfg["args"] = mx.drop_flag(cfg["args"], "--kv-grow")
                    if a.head_alias:
                        cfg["args"] = mx.set_flag(cfg["args"], "--short-read", "0") + ["--prefill-head-alias"]
                    mx.apply_draft_vocab(cfg)
                    cfg_file = out / f"{name}-{target}.config.json"
                    cfg_file.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
                    proc = strata_bench.start_server(cfg_file, a.port, None, log)
                    try:
                        if not strata_bench.wait_ready(base, "", proc, 900):
                            row["result"] = "does not start"
                        else:
                            hello, _ = crash_probe.post(base, "Say hello.", 16, 1800)
                            if hello != 200:
                                row["result"] = "does not start (engine exit on the first request)"
                            else:
                                word = f"{rnd.choice(needle_bench.WORDS)}-{rnd.choice(needle_bench.WORDS)}-{rnd.randint(100, 999)}"
                                cut = text.rfind("\n", 0, len(text) // 2) + 1
                                prompt = (text[:cut] + f"\nThe secret code word for this text is: {word}. Remember it.\n" + text[cut:] +
                                          "\n\nWhat is the secret code word mentioned in the text above? Reply with the code word only.")
                                t0 = time.time()
                                status, answer = crash_probe.post(base, prompt, 40, 3600)
                                row.update(status=status, seconds=round(time.time() - t0))
                                if status == 200:
                                    row["result"] = "ok" if word in answer else "answered, word not found"
                                else:
                                    row["result"] = "starts, engine exits on the long request" if status == 503 else f"error {status}"
                    finally:
                        strata_bench.stop_server(proc)
                        if ballast:
                            ballast.terminate()
                    try:
                        m = re.findall(r"only (\d+) MiB of VRAM free", log.read_text(encoding="utf-8", errors="replace"))
                        row["vram_free_at_request_mib"] = int(m[-1]) if m else None
                    except OSError:
                        pass
            if not str(row["result"]).startswith("desktop"):             # a target below the desktop's own use is unavailable, not a failure
                fails_in_a_row = fails_in_a_row + 1 if str(row["result"]).startswith("does not start") else 0
            rows.append(row)
            print(f"{name} with {total_mib - target} MiB available (others {target}): {row['result']} (free at request: {row.get('vram_free_at_request_mib')})", flush=True)
            (out / "results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    L = ["# Fit sweep: GPU memory used by everything except Strata vs what still works", "",
         f"Date {datetime.date.today()}. One fresh server per cell, a short request, then one {a.prompt_tokens}-token needle prompt.", "",
         "Columns: the VRAM that was AVAILABLE (free) when Strata started (the card's total minus everything else).", "",
         "| Setup | " + " | ".join(f"{total_mib - t} MiB available" for t in targets) + " |", "| --- | " + " | ".join("---" for _ in targets) + " |"]
    for name in names:
        cells = {r["target_mib"]: r["result"] for r in rows if r["setup"] == name}
        L.append(f"| {name} | " + " | ".join(cells.get(t, "") for t in targets) + " |")
    (out / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
