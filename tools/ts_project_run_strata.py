#!/usr/bin/env python3
"""Run the TS project prompts of a built run folder against Strata: start the server, send the prompts, check, report.

    .venv\\Scripts\\python.exe tools\\ts_project_run_strata.py --run logs\\ts-project-tests\\run1 --variant no-kv-grow --plan 16000:3,64000:2,110000:1

--plan SIZE:REPEATS,...  how many repeats per prompt size (the biggest prompts take about half an hour each at
~65 tok/s, so they get fewer repeats). Finished responses are kept, so an interrupted run can be started again.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "runtimes" / "strata" / "tools"))
sys.path.insert(0, str(REPO / "tools"))
import ts_project_tests                          # noqa: E402
import strata_bench                       # noqa: E402
import strata_bench_matrix as mx          # noqa: E402
import gpu_guard                       # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--variant", default="no-kv-grow")
    ap.add_argument("--config", default=str(REPO / "configs" / "strata-iq2_xs.json"), help="the base Strata config")
    ap.add_argument("--context", type=int, help="override --max-context")
    ap.add_argument("--plan", default="16000:3,64000:2,110000:1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--only", help="comma-separated substrings of test ids instead of the whole size (e.g. bug-2@64000,bug-4@64000)")
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--ready-timeout", type=float, default=1800)
    a = ap.parse_args()
    run = Path(a.run).resolve()
    cfg = mx.absolutize(json.loads(Path(a.config).read_text(encoding="utf-8-sig")), REPO)
    mx.VARIANTS[a.variant][1](cfg)
    if a.context:
        cfg["args"] = mx.set_flag(cfg["args"], "--max-context", str(a.context))
    mx.apply_draft_vocab(cfg)
    cfg_file = run / "strata-config.json"
    cfg_file.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    base = f"http://127.0.0.1:{a.port}"
    gpu_guard.require_free_port(a.port)
    desktop_vram = gpu_guard.gpu_used_mib()
    free_vram = gpu_guard.gpu_free_mib()
    lock = gpu_guard.GpuLock("ts-project-run").__enter__()
    proc = strata_bench.start_server(cfg_file, a.port, None, run / "server.log")
    try:
        if not strata_bench.wait_ready(base, "", proc, a.ready_timeout):
            print("The server did not become ready:\n" + "\n".join(strata_bench.log_excerpt(run / "server.log", 20)), file=sys.stderr)
            return 1
        ident = gpu_guard.verify_identity(base, cfg)
        ident["available_vram_mib_before_start"] = free_vram
        ident["desktop_vram_used_mib_before_start"] = desktop_vram
        (run / "identity.json").write_text(json.dumps(ident), encoding="utf-8")
        for part in a.plan.split(","):
            size, reps = part.split(":")
            print(f"--- size {size}, {reps} repeat(s) ({time.strftime('%H:%M')})", flush=True)
            ts_project_tests.cmd_run(SimpleNamespace(run=str(run), url=base, model="strata", repeats=int(reps), only=a.only or f"@{size}",
                                              max_tokens=a.max_tokens, timeout=14400))
    finally:
        strata_bench.stop_server(proc)
        lock.release()
    ts_project_tests.cmd_check(SimpleNamespace(run=str(run)))
    ts_project_tests.cmd_report(SimpleNamespace(run=str(run)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
