#!/usr/bin/env python3
"""Compare TS project test runs (built by tools/ts_project_tests.py) side by side, without any TS project source or file names.

    .venv\\Scripts\\python.exe tools\\ts_project_compare.py NAME=logs\\ts-project-tests\\wide-iq2-baseline NAME2=logs\\ts-project-tests\\wide-coder [--out docs\\ts-project-comparison.md]

For every test id and size it shows each run's mean score (out of 4 for a bug: 1 diff applies, +1 touches the right file,
+1 target test passes, +1 full suite passes), the number of repeats, how many answers ended without a usable diff
(`no diff`, usually the output budget was used up by reasoning), the server's real prompt tokens and the median decode
speed. A summary per size gives the share of repeats that fully fixed the bug (4/4). Only runs with the same prompts
(same key.json test ids) are comparable.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def load(run: Path) -> dict:
    key = json.loads((run / "key.json").read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = {}
    for f in sorted((run / "results").glob("*.json")):
        stem = f.stem.rsplit("-r", 1)[0]                       # bug-1-16000 -> bug-1@16000
        item = next((i for i in key["items"] if i.replace("@", "-") == stem), None)
        if item:
            rows.setdefault(item, []).append(json.loads(f.read_text(encoding="utf-8")))
    return {"key": key, "rows": rows}


def cell(rs: list[dict] | None) -> str:
    if not rs:
        return "n/a"
    mx = rs[0]["max"]
    mean = statistics.mean(r["score"] for r in rs)
    err = sum(1 for r in rs if r.get("error"))                                   # the request itself failed (engine exit, HTTP error)
    nodiff = sum(1 for r in rs if r.get("diff_found") is False and not r.get("error"))
    full = sum(1 for r in rs if r["score"] == mx)
    extra = (f", {nodiff} no diff" if nodiff else "") + (f", {err} request error" if err else "")
    return f"{mean:.2f}/{mx} ({full}/{len(rs)} full{extra})"


def speed(rs: list[dict] | None) -> str:
    if not rs:
        return ""
    d = [r["decode_tps"] for r in rs if r.get("decode_tps")]
    p = [r["prompt_tokens"] for r in rs if r.get("prompt_tokens")]
    w = [r["wall_s"] for r in rs if r.get("wall_s")]
    t = f", {statistics.median(w) / 60:.1f} min" if w else ""
    return f"{statistics.median(d):.0f} tok/s, {statistics.median(p) / 1000:.0f}K tokens{t}" if d and p else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="NAME=run folder")
    ap.add_argument("--out")
    a = ap.parse_args()
    runs = {}
    for spec in a.runs:
        name, _, path = spec.partition("=")
        runs[name] = load(Path(path))
    ids = sorted({i for r in runs.values() for i in r["rows"]}, key=lambda s: (s.split("@")[1].zfill(7), s))
    names = list(runs)
    L = ["# TS project tests: side-by-side", "",
         "Score per bug test: 4 = the diff applies (strict, ignoring whitespace, or by its changed lines) and the whole test suite passes (a different fix that works counts); "
         "below that: 1 = applies, +1 touches the right file, +1 the target test passes. The speed column gives the median decode speed, the prompt size and the median time per request (minutes). "
         "`no diff` = the model produced no usable diff (typically its output budget went to reasoning). Recall tests score 1 per correct answer.", "",
         "| Test | " + " | ".join(f"{n}: score" for n in names) + " | " + " | ".join(f"{n}: speed" for n in names) + " |",
         "| --- | " + " | ".join(["---"] * (2 * len(names))) + " |"]
    for i in ids:
        L.append(f"| {i} | " + " | ".join(cell(runs[n]["rows"].get(i)) for n in names) + " | " + " | ".join(speed(runs[n]["rows"].get(i)) for n in names) + " |")
    L += ["", "## Share of repeats that fully fixed the bug (bug tests only)", "", "| Size | " + " | ".join(names) + " |", "| --- | " + " | ".join("---" for _ in names) + " |"]
    sizes = sorted({i.split("@")[1] for i in ids}, key=int)
    for sz in sizes:
        cells = []
        for n in names:
            rs = [r for i, v in runs[n]["rows"].items() if i.startswith("bug-") and i.endswith("@" + sz) for r in v]
            cells.append(f"{sum(1 for r in rs if r['score'] == r['max'])}/{len(rs)}" if rs else "n/a")
        L.append(f"| {sz} | " + " | ".join(cells) + " |")
    L += ["", "## Time per request (all tests of a size, minutes)", "", "| Size | " + " | ".join(f"{n}: median / total" for n in names) + " |", "| --- | " + " | ".join("---" for _ in names) + " |"]
    for sz in sizes:
        cells = []
        for n in names:
            w = [r["wall_s"] for i, v in runs[n]["rows"].items() if i.endswith("@" + sz) for r in v if r.get("wall_s")]
            cells.append(f"{statistics.median(w) / 60:.1f} / {sum(w) / 60:.0f} ({len(w)} requests)" if w else "n/a")
        L.append(f"| {sz} | " + " | ".join(cells) + " |")
    L += ["", "## Minutes per full fix (total time of all bug attempts / attempts that fully fixed the bug; lower wins when accuracy is level)", "",
          "| Size | " + " | ".join(n for n in names) + " |", "| --- | " + " | ".join("---" for _ in names) + " |"]
    for sz in sizes:
        cells = []
        for n in names:
            rs = [r for i, v in runs[n]["rows"].items() if i.startswith("bug-") and i.endswith("@" + sz) for r in v]
            full = sum(1 for r in rs if r["score"] == r["max"])
            cells.append(f"{sum(r.get('wall_s') or 0 for r in rs) / 60 / full:.1f}" if rs and full else "n/a")
        L.append(f"| {sz} | " + " | ".join(cells) + " |")
    both = [i for i in ids if i.startswith("bug-") and all(runs[n]["rows"].get(i) and all(r["score"] == r["max"] for r in runs[n]["rows"][i]) for n in names)]
    if both:
        L += ["", "## Bugs that every attempt of every model fixed: median minutes per request (the fastest model wins these)", "",
              "| Test | " + " | ".join(names) + " |", "| --- | " + " | ".join("---" for _ in names) + " |"]
        for i in both:
            L.append(f"| {i} | " + " | ".join(f"{statistics.median(r['wall_s'] for r in runs[n]['rows'][i] if r.get('wall_s')) / 60:.1f}" for n in names) + " |")
    text = "\n".join(L) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
