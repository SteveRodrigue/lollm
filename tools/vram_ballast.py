#!/usr/bin/env python3
"""Hold a fixed amount of GPU memory (a ballast) to imitate a busier desktop.

    python tools/vram_ballast.py --mib 400 [--seconds 3600]

Allocates --mib MiB of device memory with cudaMalloc in 64 MiB pieces, prints READY, then sleeps until killed or --seconds pass.
Uses the CUDA runtime DLL shipped with Strata's engine. Used by tools/fit_sweep.py; it never writes anything.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mib", type=int, required=True)
    ap.add_argument("--seconds", type=int, default=24 * 3600)
    a = ap.parse_args()
    dll = next(iter(sorted((REPO / "runtimes" / "strata" / "engine").glob("cudart64_*.dll"), reverse=True)), None)
    if dll is None:
        print("cudart not found", file=sys.stderr)
        return 2
    os.add_dll_directory(str(dll.parent))
    cu = ctypes.CDLL(str(dll))
    held = []
    for _ in range(max(0, a.mib) // 64):
        p = ctypes.c_void_p()
        if cu.cudaMalloc(ctypes.byref(p), ctypes.c_size_t(64 * 2 ** 20)) != 0:
            print("cudaMalloc failed", file=sys.stderr)
            return 3
        held.append(p)
    # touch the pages so the driver really commits them
    for p in held:
        cu.cudaMemset(p, 1, ctypes.c_size_t(64 * 2 ** 20))
    cu.cudaDeviceSynchronize()
    print(f"READY {len(held) * 64} MiB", flush=True)
    time.sleep(a.seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
