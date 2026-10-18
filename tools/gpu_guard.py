"""Guardrails for anything that starts a Strata server and measures it.

Two overlapping jobs once shared port 8080 (Windows lets two processes listen on one port) and mixed their results.
Every tool that starts a server now uses these three checks:

  require_free_port(port)      refuse to start when something already listens on the port
  GpuLock(name)                one GPU job at a time (lock file with PID; a lock of a dead PID is ignored)
  verify_identity(base, cfg)   after startup, the server that answers must be the model and context we configured

and sanity_warnings(...) to flag numbers that look wrong. Exit code 3 means "refused by a guardrail".
"""
from __future__ import annotations

import atexit
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = REPO / "logs" / ".gpu-lock"


def gpu_used_mib() -> int | None:
    """GPU memory in use right now (the desktop's share, before we start a server). Recorded in results: a setup that only
    just fits can start or fail depending on how many apps use the GPU."""
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL).stdout
    try:
        return int(out.split()[0])
    except (ValueError, IndexError):
        return None


def gpu_free_mib() -> int | None:
    """GPU memory that is free (available) right now, as nvidia-smi reports it. THIS is the figure that decides what fits: what the
    desktop uses does not matter, only what is left."""
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL).stdout
    try:
        return int(out.split()[0])
    except (ValueError, IndexError):
        return None


def refuse(msg: str) -> None:
    print(f"[guardrail] {msg}", file=sys.stderr, flush=True)
    raise SystemExit(3)


def port_listeners(port: int) -> list[int]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL).stdout
    pids = []
    for line in out.splitlines():
        m = re.search(rf"[:.]{port}\s+\S+\s+LISTENING\s+(\d+)", line)
        if m:
            pids.append(int(m.group(1)))
    return pids


def require_free_port(port: int, wait_s: float = 45) -> None:
    """Refuse when something listens on the port. A server that was just stopped needs a few seconds to let go, so wait a little first."""
    t0 = time.time()
    pids = port_listeners(port)
    while pids and time.time() - t0 < wait_s:
        time.sleep(3)
        pids = port_listeners(port)
    if pids:
        refuse(f"port {port} already has a listener (PID {', '.join(map(str, pids))}): another server is running; not starting")


def pid_alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL).stdout
    return bool(re.search(rf"\b{pid}\b", out))


class GpuLock:
    """with GpuLock('soak'): ...   Takes logs/.gpu-lock; refuses (or waits wait_s seconds) when a live job holds it."""

    def __init__(self, name: str, wait_s: float = 0):
        self.name, self.wait_s = name, wait_s

    def __enter__(self):
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        while True:
            try:
                held = json.loads(LOCK.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                held = None
            if held and held.get("pid") != os.getpid() and pid_alive(int(held["pid"])):
                if time.time() - t0 >= self.wait_s:
                    refuse(f"the GPU lock is held by '{held.get('name')}' (PID {held['pid']}, since {held.get('since')}); not starting")
                time.sleep(15)
                continue
            break
        LOCK.write_text(json.dumps({"pid": os.getpid(), "name": self.name, "since": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
        atexit.register(self.release)
        return self

    def release(self):
        try:
            held = json.loads(LOCK.read_text(encoding="utf-8"))
            if held.get("pid") == os.getpid():
                LOCK.unlink()
        except (OSError, ValueError):
            pass

    def __exit__(self, *exc):
        self.release()
        return False


def verify_identity(base: str, cfg: dict, api_key: str = "") -> dict:
    """The server answering on `base` must serve cfg['model_name'] with the configured context. Returns what it reported."""
    req = urllib.request.Request(base + "/health", headers={"Authorization": "Bearer " + api_key} if api_key else {})
    with urllib.request.urlopen(req, timeout=15) as r:
        h = json.loads(r.read())
    args = cfg.get("args") or []
    want_ctx = int(args[args.index("--max-context") + 1]) if "--max-context" in args[:-1] else None
    want_model = cfg.get("model_name")
    if h.get("service") != "strata":
        refuse(f"{base} is not a Strata server")
    if want_model and h.get("model") != want_model:
        refuse(f"the server answers as '{h.get('model')}', not the configured '{want_model}': another server is on this port")
    if want_ctx and h.get("max_context") != want_ctx:
        refuse(f"the server has context {h.get('max_context')}, not the configured {want_ctx}: another server is on this port")
    return {"model": h.get("model"), "max_context": h.get("max_context")}


def sanity_warnings(peak_ram_gib: float | None = None, total_ram_gib: float = 32.0,
                    started_expected: bool = True, started: bool = True) -> list[str]:
    """Plain-language flags for results that look suspicious. Empty list = nothing odd."""
    w = []
    if started_expected and not started:
        w.append("the server we tried to start did not start")
    if peak_ram_gib is not None and peak_ram_gib > 0.97 * total_ram_gib:
        w.append(f"peak RAM in use {peak_ram_gib:.1f} GiB is at the machine's limit: expect paging and noisy timings")
    return w
