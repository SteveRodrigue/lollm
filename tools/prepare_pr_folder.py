#!/usr/bin/env python3
"""Build the results folder for the Strata pull request from the repository's docs (safe to run again after new results).

    .venv\\Scripts\\python.exe tools\\prepare_pr_folder.py [--name 2026-10-15-community-rtx-3060-ti-8gb]

Writes docs/strata-submission-draft/pr-folder/<name>/ with README.md (the main report, findings first), the raw per-variant data,
the Coder and TS project comparison tables, the changelog of discarded runs and the hardware probe output; then runs the privacy scan on it.
Copy that folder to bench/results/ in your fork of Niko1221/Strata. Nothing is uploaded.
"""
from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default=f"{datetime.date.today()}-community-rtx-3060-ti-8gb")
    a = ap.parse_args()
    dest = DOCS / "strata-submission-draft" / "pr-folder" / a.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copy2(DOCS / "strata-benchmarks.md", dest / "README.md")
    for name in ("strata-benchmark-changelog.md", "ts-project-comparison.md", "ts-project-comparison-120k.md", "strata-benchmarks-coder-mirror.md", "vram-requirements.md", "vram-requirements-0.1.44.1.md", "vram-requirements-0.1.44.1-fast.md",
                 "ts-project-comparison-3way.md", "ts-project-comparison-fast-mode.md", "ts-project-comparison-fast-mode-3way.md", "ts-project-comparison-fast-mode-98k.md", "strata-findings.md"):
        if (DOCS / name).exists():
            shutil.copy2(DOCS / name, dest / name)
    for d in ("strata-benchmarks-data", "strata-benchmarks-coder-mirror-data"):
        if (DOCS / d).exists():
            shutil.copytree(DOCS / d, dest / d)
    hw = REPO / "reports" / "strata-bench" / "full-0.1.43.1" / "hardware.json"
    if hw.exists():
        shutil.copy2(hw, dest / "hardware.json")
    files = sum(1 for _ in dest.rglob("*") if _.is_file())
    print(f"Built {dest.relative_to(REPO)} with {files} files")
    return subprocess.run([sys.executable, str(REPO / "tools" / "scan_private.py"), str(dest)]).returncode


if __name__ == "__main__":
    sys.exit(main())
