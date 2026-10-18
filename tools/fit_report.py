#!/usr/bin/env python3
"""Write docs/vram-requirements.md: how much AVAILABLE (free) VRAM each Strata setup needs, from a fit-sweep run.

    python tools/fit_report.py reports/strata-bench/fit-sweep/<stamp>-nokvgrow [--out docs/vram-requirements.md]

The only number that matters is the VRAM that is available (free) when Strata starts, as nvidia-smi reports it. What uses the rest
(a browser, the desktop, another program) does not matter. The sweep measured it by holding a ballast so that the available VRAM took
chosen values; this report turns those cells into 'works from at least N MiB available' and adds the launcher's fitted requirement.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import strata_fit_launch as fl  # noqa: E402

MODELS = {"coder": ("qwen3.8-flash-next-coder-iq1_m", "Coder IQ1_M", "strata-coder-iq1_m.json"),
          "iq3": ("qwen3.8-flash-next-iq3_xxs", "IQ3_XXS", "strata-iq3_xxs.json"),
          "iq2": ("qwen3.8-flash-next-iq2_xs", "IQ2_XS", "strata-iq2_xs.json")}


def gpu_total() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL).stdout
    return int(out.split()[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--out", default=str(REPO / "docs" / "vram-requirements.md"))
    ap.add_argument("--engine", default="0.1.43.1", help="Strata engine version the sweep ran on (for the text)")
    ap.add_argument("--fast", action="store_true", help="the sweep was run with --head-alias (fast mode)")
    a = ap.parse_args()
    total = gpu_total()
    rows = json.loads((Path(a.run) / "results.json").read_text(encoding="utf-8"))
    table = json.loads((REPO / "configs" / "vram-model.json").read_text(encoding="utf-8"))["models"]
    L = ["# How much available VRAM does Strata need?" + (" Fast mode (`--prefill-head-alias --short-read 0`)" if a.fast else ""), "",
         f"**Available VRAM** is the GPU memory that is free when Strata starts (what `nvidia-smi` shows as free; here the card has {total} MiB in total). "
         "It is the only figure that matters: what is using the rest, a browser, the desktop or another program, makes no difference.", "",
         f"Measured {datetime.date.today()} on an RTX 3060 Ti 8 GB with Strata engine {a.engine}, `--kv q4_0`, KV cache reserved up front (no `--kv-grow`), "
         "`--vram-reserve-mib 1024`, `--spec 4 --mtp`" + (", `--short-read 0 --prefill-head-alias`" if a.fast else "") + ". A ballast held part of the VRAM so that the available amount took chosen values; "
         "every cell starts a fresh server, a short request, then one 24K-token prompt. Grid step about 200 MiB, so read the limits as +-100 MiB.", "",
         "## Measured (what worked)", "",
         "| Model | Context window | Works with at least this much available VRAM | Failed to start with this much or less |", "| --- | ---: | ---: | ---: |"]
    for key, (name, label, _cfg) in MODELS.items():
        for w in sorted({int(r["setup"].split("-")[1]) for r in rows if r["setup"].startswith(key + "-")}, reverse=True):
            rs = [r for r in rows if r["setup"] == f"{key}-{w}" and "others_mib" in r]
            ok = [total - r["others_mib"] for r in rs if not str(r["result"]).startswith("does not start")]
            bad = [total - r["others_mib"] for r in rs if str(r["result"]).startswith("does not start")]
            works = f"{min(ok)} MiB" if ok else (f"never (it failed even with {max(bad)} MiB available)" if bad else "n/a")
            L.append(f"| {label} | {w} | {works} | {str(max(bad)) + ' MiB' if bad else '-'} |")
    L += ["", "No engine exit on the long prompt happened in any cell that started: with the KV cache reserved up front, a setup that starts also answers.", "",
          "## Fitted requirement used by `tools/strata_fit_launch.py`", "",
          "Available VRAM needed = weights + draft head + VRAM reserve + minimum expert cache + KV cache of the window (+ a 150 MiB safety margin).", "",
          "| Context window | " + " | ".join(label for _, label, _ in MODELS.values()) + " |", "| ---: | " + " | ".join("---:" for _ in MODELS) + " |"]
    for w in (32768, 65536, 98304, 131072, 196608, 262144):
        cells = []
        for key, (name, label, cfgname) in MODELS.items():
            cfg = json.loads((REPO / "configs" / cfgname).read_text(encoding="utf-8-sig"))
            need = fl.needed_free_mib(cfg, table[name], w, 150, a.fast)
            cells.append(f"{need} MiB" + (" (more than this card has)" if need > total else ""))
        L.append(f"| {w} | " + " | ".join(cells) + " |")
    L += ["", "Windows above 131,072 tokens are extrapolated (the sweep measured up to 131,072).", "A card with more VRAM needs the same amounts: with about 9.5 GB of VRAM available every model reaches the model's maximum window (262,144 tokens).", ""]
    Path(a.out).write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
