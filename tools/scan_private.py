#!/usr/bin/env python3
"""Search files for private information before they are committed or shared (see AGENTS.md).

    .venv\\Scripts\\python.exe tools\\scan_private.py [PATH ...]      (default: the files git would add: untracked + modified)

Looks for: this machine's user name, host name and home folder (read at run time, so nothing private is written in this
file), any C:\\Users\\<name> or /home/<name> path, drive-letter absolute paths, e-mail addresses, IPv4 addresses that are
not loopback, and strings that look like keys or tokens. Prints file:line and the kind of match, not the secret itself.
Exit code 1 when something is found.
"""
from __future__ import annotations

import getpass
import re
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "models", "runtimes", "logs", "reports", "cache"}
TEXT_EXT = {".md", ".txt", ".json", ".py", ".bat", ".sh", ".yaml", ".yml", ".toml", ".cfg", ".csv", ".js", ".ts", ".html"}


def patterns() -> list[tuple[str, re.Pattern]]:
    p: list[tuple[str, re.Pattern]] = []
    for label, val in (("user name", getpass.getuser()), ("host name", socket.gethostname()), ("home folder", str(Path.home()))):
        if val and len(val) >= 3:
            p.append((label, re.compile(re.escape(val).replace(r"\\", r"[\\/]"), re.I)))
    p += [
        ("user-profile path", re.compile(r"(?i)[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>|]+")),
        ("home path", re.compile(r"(?i)/(?:home|Users)/[a-z0-9._-]+/")),
        ("absolute drive path", re.compile(r"\b[A-Za-z]:[\\/](?!Users)[\w .-]+[\\/]")),
        ("e-mail address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
        # four dotted numbers, not starting with 0 (versions like 0.1.43.1) and not followed by more dots/digits
        ("IPv4 address", re.compile(r"(?<![\w.])(?!127\.0\.0\.1(?![\w.]))(?!0\.)(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.])")),
        ("key/token-like string", re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})\b")),
        ("bearer/api key assignment", re.compile(r"(?i)(?:api[_-]?key|token|secret|password)\s*[:=]\s*[\"'][^\"']{8,}[\"']")),
    ]
    return p


def candidate_files(args: list[str]) -> list[Path]:
    if args:
        out = []
        for a in args:
            q = (REPO / a) if not Path(a).is_absolute() else Path(a)
            out += [f for f in (q.rglob("*") if q.is_dir() else [q]) if f.is_file()]
        return out
    r = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "-uall"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    files = []
    for line in r.stdout.splitlines():
        name = line[3:].strip().strip('"')
        if name:
            files.append(REPO / name)
    return files


def main() -> int:
    pats = patterns()
    hits = 0
    for f in candidate_files(sys.argv[1:]):
        rel = f.relative_to(REPO) if f.is_relative_to(REPO) else f
        if SKIP_DIRS & set(rel.parts) or f.suffix.lower() not in TEXT_EXT or not f.is_file():
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for label, pat in pats:
                if pat.search(line):
                    hits += 1
                    print(f"{rel.as_posix()}:{n}: {label}")
    print(f"{hits} possible private item(s) found" if hits else "nothing private found")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
