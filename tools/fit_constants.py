#!/usr/bin/env python3
"""Fit the launcher's VRAM constants (configs/vram-model.json) to a fit-sweep table.

    python tools/fit_constants.py reports/strata-bench/fit-sweep/<stamp>-nokvgrow [--apply]

Reads results.json of a sweep run WITHOUT --kv-grow (python tools/fit_sweep.py --no-kv-grow), the semantics tools/strata_fit_launch.py assumes.
For every model it takes, per window W, the largest amount of VRAM used by other programs (O) at which the engine still started and the
largest at which it also survived the long request. The launcher's rule is  O_max(W) = 8192 - A - KV(W)  with A = dense + draft head + reserve +
minimum expert cache, so each W gives an interval for A; the intervals are intersected (their midpoint is used; when they disagree the median
of the lower bounds). The difference between the 'starts' and the 'survives the long request' thresholds is proposed as the safety margin.
Writes <run>/fitted-vram-model.json and <run>/fit-report.md; with --apply it also writes configs/vram-model.json (the old file is kept as
configs/vram-model.previous.json). The sweep grid is coarse (a step of 200 MiB), so the constants are good to roughly +-100 MiB.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOTAL = 8192
MODEL_OF = {"coder": "qwen3.8-flash-next-coder-iq1_m", "iq2": "qwen3.8-flash-next-iq2_xs", "iq3": "qwen3.8-flash-next-iq3_xxs"}


def kv(model: dict, window: int) -> float:
    k = model["kv_q4_0"]
    return k["base_mib"] + k["per_token_mib"] * window


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--fast", action="store_true", help="the sweep was run with --head-alias: store the result as fast_dense_mib (the launcher's --fast mode) and leave dense_mib alone")
    a = ap.parse_args()
    run = Path(a.run)
    rows = json.loads((run / "results.json").read_text(encoding="utf-8"))
    table_path = REPO / "configs" / "vram-model.json"
    table = json.loads(table_path.read_text(encoding="utf-8"))
    L = ["# Fit of the launcher constants", "", f"Sweep: `{run.name}`. Grid step about 200 MiB.", ""]
    for key, name in MODEL_OF.items():
        m = table["models"][name]
        start_a, long_a = [], []
        L += [f"## {name}", "", "| Window | highest 'others' (MiB) where it starts | where it also survives the long request |", "| ---: | ---: | ---: |"]
        for w in sorted({int(r["setup"].split("-")[1]) for r in rows if r["setup"].startswith(key + "-")}):
            rs = [r for r in rows if r["setup"] == f"{key}-{w}" and "others_mib" in r]
            starts = [r["others_mib"] for r in rs if not str(r["result"]).startswith("does not start")]
            longs = [r["others_mib"] for r in rs if r["result"] in ("ok", "answered, word not found")]
            fails = [r["others_mib"] for r in rs if str(r["result"]).startswith("does not start")]
            o_s, o_l = (max(starts) if starts else None), (max(longs) if longs else None)
            L.append(f"| {w} | {o_s if o_s is not None else 'never'} | {o_l if o_l is not None else 'never'} |")
            lo = (o_s + kv(m, w)) if o_s is not None else None          # A >= highest success + KV
            hi = (min(fails) + kv(m, w)) if fails else None              # A < lowest failure + KV (also when nothing started at that window)
            if lo is not None or hi is not None:
                start_a.append((lo, hi))
            if o_l is not None:
                long_a.append(o_l + kv(m, w))
        if not start_a:
            L += ["", "Nothing started: no fit possible.", ""]
            continue
        lows = [lo for lo, _ in start_a if lo is not None]
        highs = [hi for _, hi in start_a if hi is not None]
        lo, hi = (max(lows) if lows else None), (min(highs) if highs else None)
        if lo is not None and hi is not None and hi >= lo:
            a_est = (lo + hi) / 2
        elif lo is not None:
            a_est = statistics.median(lows) if hi is None else lo
        else:
            a_est = hi - 100
        dense = round(TOTAL - a_est - m["draft_head_mib"]["cjk"] - 1024 - m["min_expert_cache_mib"])
        margin = round(max(0.0, a_est - statistics.median(long_a))) if long_a else None
        L += ["", f"A (everything that must fit besides KV and the desktop) = {a_est:.0f} MiB (interval {lo:.0f} to {hi if hi is None else round(hi)}); "
              f"proposed dense_mib = {dense} (now {m['dense_mib']}); proposed safety margin = {margin} MiB (the launcher default is 150).", ""]
        if a.fast:
            m["fast_dense_mib"] = dense
        else:
            m["dense_mib"] = dense
            if margin is not None:
                m["suggested_margin_mib"] = margin
    table["_fitted_from"] = run.name
    (run / "fitted-vram-model.json").write_text(json.dumps(table, indent=1), encoding="utf-8")
    (run / "fit-report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    if a.apply:
        prev = REPO / "configs" / "vram-model.previous.json"
        if not prev.exists():                                     # keep the very first (hand-derived) numbers
            prev.write_text(table_path.read_text(encoding="utf-8"), encoding="utf-8")
        table_path.write_text(json.dumps(table, indent=1), encoding="utf-8")
        print("Applied to configs/vram-model.json (previous kept as vram-model.previous.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
