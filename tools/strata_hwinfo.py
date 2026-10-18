#!/usr/bin/env python3
"""Collect the hardware facts that decide how Strata runs, for the shareable benchmark report.

    .venv\\Scripts\\python.exe tools\\strata_hwinfo.py [--json OUT.json] [--model-file FILE]

Reads (nothing is changed): CPU, installed RAM modules and their configured speed, GPU, driver, PCIe link
(generation/width, idle and under load), VRAM size and clocks, and measures
  - host RAM bandwidth (multi-threaded read and copy),
  - GPU VRAM bandwidth (device-to-device copy),
  - PCIe bandwidth host<->GPU (pinned and pageable, both directions),
  - sequential read speed of the drive holding the model (unbuffered, so the OS cache does not inflate it).
Host name, user name, serial numbers and absolute paths are never recorded.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

GIB = 2 ** 30
NT = os.name == "nt"


def run(cmd, timeout=30) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def ps_json(script: str):
    out = run(["powershell", "-NoProfile", "-Command", script + " | ConvertTo-Json -Compress"], 60)
    try:
        v = json.loads(out)
    except ValueError:
        return []
    return v if isinstance(v, list) else [v]


# ------------------------------------------------------------------------------------------------ CPU and RAM
def cpu_info() -> dict:
    info = {"name": platform.processor(), "logical": os.cpu_count()}
    if NT:
        p = ps_json("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,"
                    "MaxClockSpeed,L2CacheSize,L3CacheSize")
        if p:
            p = p[0]
            info.update(name=(p.get("Name") or "").strip(), cores=p.get("NumberOfCores"), logical=p.get("NumberOfLogicalProcessors"),
                        max_mhz=p.get("MaxClockSpeed"), l3_mib=round((p.get("L3CacheSize") or 0) / 1024, 1))
    return info


DDR_TYPES = {20: "DDR", 21: "DDR2", 24: "DDR3", 26: "DDR4", 34: "DDR5", 35: "LPDDR5"}


def ram_info() -> dict:
    info = {"modules": []}
    try:
        import psutil
        info["total_gib"] = round(psutil.virtual_memory().total / GIB, 1)
    except ImportError:
        pass
    if NT:
        for m in ps_json("Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed,ConfiguredClockSpeed,"
                         "SMBIOSMemoryType,DataWidth,TotalWidth"):
            info["modules"].append({
                "gib": round((m.get("Capacity") or 0) / GIB), "type": DDR_TYPES.get(m.get("SMBIOSMemoryType"), str(m.get("SMBIOSMemoryType"))),
                "rated_mts": m.get("Speed"), "configured_mts": m.get("ConfiguredClockSpeed"), "ecc": (m.get("TotalWidth") or 0) > (m.get("DataWidth") or 0)})
    mods = info["modules"]
    if mods:
        speed = min((m["configured_mts"] or m["rated_mts"] or 0) for m in mods)
        channels = min(len(mods), 2)          # consumer boards have two channels; this is an assumption, not read
        info["theoretical_gbs"] = round(speed * 8 * channels / 1000, 1) if speed else None
        info["theoretical_note"] = f"{speed} MT/s x 8 B x {channels} channels (assumed)"
    return info


def _bw_thread(fn, nthreads):
    ts = [threading.Thread(target=fn) for _ in range(nthreads)]
    t0 = time.perf_counter()
    [t.start() for t in ts]
    [t.join() for t in ts]
    return time.perf_counter() - t0


def ram_bandwidth(threads: int | None = None, mib_per_thread: int = 512, repeats: int = 3) -> dict:
    """Multi-threaded numpy read (sum) and copy.  Copy GB/s counts read + write traffic.  Best of `repeats`."""
    try:
        import numpy as np
    except ImportError:
        return {"error": "numpy missing"}
    n = threads or max(1, (os.cpu_count() or 8) // 2)
    elems = mib_per_thread * 2 ** 20 // 8
    src = [np.ones(elems) for _ in range(n)]
    dst = [np.empty(elems) for _ in range(n)]
    idx = iter(range(10 ** 6))
    lock = threading.Lock()

    def take():
        with lock:
            return next(idx) % n
    out = {"threads": n, "buffer_mib_per_thread": mib_per_thread}
    best_r = best_c = 0.0
    total = n * elems * 8
    for _ in range(repeats):
        i = iter(range(n))

        def rd():
            with lock:
                k = next(i)
            src[k].sum()
        best_r = max(best_r, total / _bw_thread(rd, n) / 1e9)
        i = iter(range(n))

        def cp():
            with lock:
                k = next(i)
            np.copyto(dst[k], src[k])
        best_c = max(best_c, 2 * total / _bw_thread(cp, n) / 1e9)
    out.update(read_gbs=round(best_r, 1), copy_gbs=round(best_c, 1))
    return out


# ------------------------------------------------------------------------------------------------------ GPU
SMI_FIELDS = ["name", "driver_version", "memory.total", "pcie.link.gen.current", "pcie.link.gen.max", "pcie.link.width.current",
              "pcie.link.width.max", "clocks.sm", "clocks.max.sm", "clocks.mem", "clocks.max.mem", "power.limit",
              "power.default_limit", "power.max_limit", "pstate", "temperature.gpu"]


def smi_query() -> dict:
    out = run(["nvidia-smi", f"--query-gpu={','.join(SMI_FIELDS)}", "--format=csv,noheader,nounits"])
    line = out.strip().splitlines()[0] if out.strip() else ""
    vals = [x.strip() for x in line.split(",")]
    return dict(zip(SMI_FIELDS, vals)) if len(vals) == len(SMI_FIELDS) else {}


def bar1_mib() -> int | None:
    m = re.search(r"BAR1 Memory Usage\s*\n\s*Total\s*:\s*(\d+)", run(["nvidia-smi", "-q", "-d", "MEMORY"]))
    return int(m.group(1)) if m else None


def find_cudart(strata_root: Path | None) -> str | None:
    cands = []
    if strata_root:
        cands += sorted((strata_root / "engine").glob("cudart64_*.dll" if NT else "libcudart.so*"), reverse=True)
    for p in sys.path + [sys.prefix]:
        cands += sorted(Path(p).glob("**/nvidia/cu13/bin/**/cudart64_*.dll"), reverse=True) if NT and p else []
    return str(cands[0]) if cands else None


class Cuda:
    def __init__(self, path: str):
        os.add_dll_directory(str(Path(path).parent)) if NT else None
        self.lib = ctypes.CDLL(path)

    def check(self, rc, what):
        if rc != 0:
            raise RuntimeError(f"{what} failed ({rc})")

    def attr(self, a, dev=0):
        v = ctypes.c_int()
        self.check(self.lib.cudaDeviceGetAttribute(ctypes.byref(v), a, dev), f"attribute {a}")
        return v.value

    def malloc(self, n):
        p = ctypes.c_void_p()
        self.check(self.lib.cudaMalloc(ctypes.byref(p), ctypes.c_size_t(n)), "cudaMalloc")
        return p

    def malloc_host(self, n):
        p = ctypes.c_void_p()
        self.check(self.lib.cudaMallocHost(ctypes.byref(p), ctypes.c_size_t(n)), "cudaMallocHost")
        return p

    def copy(self, dst, src, n, kind):
        self.check(self.lib.cudaMemcpy(dst, src, ctypes.c_size_t(n), kind), "cudaMemcpy")

    def sync(self):
        self.check(self.lib.cudaDeviceSynchronize(), "sync")


H2D, D2H, D2D = 1, 2, 3


def timed_copy(cu: Cuda, dst, src, n, kind, reps) -> float:
    cu.copy(dst, src, n, kind)
    cu.sync()
    t0 = time.perf_counter()
    for _ in range(reps):
        cu.copy(dst, src, n, kind)
    cu.sync()
    return n * reps / (time.perf_counter() - t0) / 1e9


def gpu_bandwidth(strata_root: Path | None) -> dict:
    path = find_cudart(strata_root)
    if not path:
        return {"error": "cudart not found"}
    try:
        cu = Cuda(path)
        res = {}
        n = 256 * 2 ** 20
        dev, dev2 = cu.malloc(n), cu.malloc(n)
        pinned = cu.malloc_host(n)
        page = ctypes.create_string_buffer(n)
        try:
            res["bus_width_bits"] = cu.attr(37)
        except RuntimeError:
            pass
        res["sm_count"] = cu.attr(16)
        res["l2_mib"] = round(cu.attr(38) / 2 ** 20, 1)
        res["vram_d2d_gbs"] = round(2 * timed_copy(cu, dev2, dev, n, D2D, 30), 1)          # read + write traffic
        smi_during = {}

        def sample():                                    # the link renegotiates up under load: read it while copying
            time.sleep(0.4)
            smi_during.update(smi_query())
        t = threading.Thread(target=sample)
        t.start()
        res["pcie_h2d_pinned_gbs"] = round(timed_copy(cu, dev, pinned, n, H2D, 60), 2)
        t.join()
        res["pcie_d2h_pinned_gbs"] = round(timed_copy(cu, pinned, dev, n, D2H, 30), 2)
        res["pcie_h2d_pageable_gbs"] = round(timed_copy(cu, dev, page, n, H2D, 15), 2)
        res["pcie_d2h_pageable_gbs"] = round(timed_copy(cu, page, dev, n, D2H, 15), 2)
        res["smi_under_load"] = smi_during
        return res
    except (OSError, RuntimeError, AttributeError) as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------------------------------- storage
def drive_info(path: Path) -> dict:
    path = path.resolve()
    info = {}
    if NT and path.drive:
        letter = path.drive[0]
        d = ps_json(f"Get-Partition -DriveLetter {letter} | Get-Disk | Get-PhysicalDisk | "
                    "Select-Object FriendlyName,MediaType,BusType,Size")
        if d:
            info = {"model": (d[0].get("FriendlyName") or "").strip(), "media": d[0].get("MediaType"), "bus": d[0].get("BusType"),
                    "size_gib": round((d[0].get("Size") or 0) / GIB)}
        try:
            import shutil
            info["free_gib"] = round(shutil.disk_usage(path).free / GIB)
        except OSError:
            pass
    return info


def read_speed_unbuffered(path: Path, total_mib: int = 2048, block_mib: int = 8) -> float | None:
    """Sequential read with FILE_FLAG_NO_BUFFERING, from the middle of the file (cold pages)."""
    if not NT or not path.is_file():
        return None
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.VirtualAlloc.restype = ctypes.c_void_p
    k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
    h = k32.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x20000000 | 0x08000000, None)
    if h in (None, ctypes.c_void_p(-1).value):
        return None
    block = block_mib * 2 ** 20
    buf = k32.VirtualAlloc(None, block, 0x3000, 4)
    size = path.stat().st_size
    start = max(0, (size // 2) // block * block)
    li = ctypes.c_longlong(start)
    k32.SetFilePointerEx(ctypes.c_void_p(h), li, None, 0)
    got, n = 0, ctypes.c_ulong()
    t0 = time.perf_counter()
    while got < total_mib * 2 ** 20:
        if not k32.ReadFile(ctypes.c_void_p(h), ctypes.c_void_p(buf), block, ctypes.byref(n), None) or n.value == 0:
            break
        got += n.value
    dt = time.perf_counter() - t0
    k32.CloseHandle(ctypes.c_void_p(h))
    return round(got / dt / 1e9, 2) if got else None


# --------------------------------------------------------------------------------------------------------- main
def collect(strata_root: Path | None, model_file: Path | None) -> dict:
    smi = smi_query()
    hw = {"os": f"{platform.system()} {platform.release()} ({platform.version()})", "python": platform.python_version(),
          "cpu": cpu_info(), "ram": ram_info(), "ram_bandwidth": ram_bandwidth(),
          "gpu": {"smi_idle": smi, "bar1_mib": bar1_mib(), **gpu_bandwidth(strata_root)}}
    if NT:
        plan = run(["powercfg", "/getactivescheme"])
        g = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", plan, re.I)
        names = {"381b4222-f694-41f0-9685-ff5bb260df2e": "Balanced", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "High performance",
                 "a1841308-3541-4fab-bc81-f71556f20b4a": "Power saver", "e9a42b02-d5df-448d-aa00-03f14749eb61": "Ultimate performance"}
        hw["power_plan"] = names.get(g.group(1).lower(), g.group(1)) if g else None            # GUID, so the language of Windows does not matter
    if model_file:
        hw["storage"] = {**drive_info(model_file), "seq_read_gbs_unbuffered": read_speed_unbuffered(model_file)}
    return hw


def render_markdown(hw: dict) -> str:
    c, r, g, rb = hw["cpu"], hw["ram"], hw["gpu"], hw["ram_bandwidth"]
    s = g.get("smi_idle") or {}
    load = g.get("smi_under_load") or {}
    mods = r.get("modules") or []
    mod_txt = ", ".join(f"{m['gib']} GiB {m['type']}-{m['configured_mts'] or m['rated_mts']}" for m in mods) or "not read"
    L = ["| Component | Details |", "| --- | --- |",
         f"| CPU | {c.get('name')} ({c.get('cores', '?')} cores / {c.get('logical')} threads, base {c.get('max_mhz', '?')} MHz, L3 {c.get('l3_mib', '?')} MiB) |",
         f"| RAM | {r.get('total_gib', '?')} GiB total: {len(mods)} module(s): {mod_txt}; rated "
         f"{'/'.join(sorted({str(m['rated_mts']) for m in mods})) or '?'} MT/s, running {'/'.join(sorted({str(m['configured_mts']) for m in mods})) or '?'} MT/s |",
         f"| RAM bandwidth (measured) | read {rb.get('read_gbs', '?')} GB/s, copy {rb.get('copy_gbs', '?')} GB/s (read+write traffic), {rb.get('threads', '?')} threads; "
         f"theoretical {r.get('theoretical_gbs', '?')} GB/s ({r.get('theoretical_note', '')}) |",
         f"| GPU | {s.get('name')}: {s.get('memory.total')} MiB VRAM, {g.get('sm_count', '?')} SMs, L2 {g.get('l2_mib', '?')} MiB, "
         f"{g.get('bus_width_bits', '?')}-bit bus, memory clock up to {s.get('clocks.max.mem')} MHz, SM clock up to {s.get('clocks.max.sm')} MHz |",
         f"| VRAM bandwidth (measured) | {g.get('vram_d2d_gbs', '?')} GB/s device-to-device copy (read+write traffic) |",
         f"| GPU power limit | {s.get('power.limit')} W (default {s.get('power.default_limit')} W, max {s.get('power.max_limit')} W) |",
         f"| PCIe link | max Gen{s.get('pcie.link.gen.max')} x{s.get('pcie.link.width.max')}; idle Gen{s.get('pcie.link.gen.current')} x{s.get('pcie.link.width.current')}; "
         f"under load Gen{load.get('pcie.link.gen.current', '?')} x{load.get('pcie.link.width.current', '?')} |",
         f"| PCIe bandwidth (measured) | host to GPU {g.get('pcie_h2d_pinned_gbs', '?')} GB/s pinned, {g.get('pcie_h2d_pageable_gbs', '?')} GB/s pageable; "
         f"GPU to host {g.get('pcie_d2h_pinned_gbs', '?')} GB/s pinned, {g.get('pcie_d2h_pageable_gbs', '?')} GB/s pageable |",
         f"| Resizable BAR | BAR1 {g.get('bar1_mib', '?')} MiB ({'enabled (BAR >= VRAM)' if (g.get('bar1_mib') or 0) >= int(s.get('memory.total') or 10**9) else 'not full-size'}) |",
         f"| GPU driver | {s.get('driver_version')} |"]
    st = hw.get("storage")
    if st:
        L.append(f"| Model drive | {st.get('model', '?')} ({st.get('bus', '?')} {st.get('media', '')}, {st.get('size_gib', '?')} GiB); "
                 f"sequential read {st.get('seq_read_gbs_unbuffered', '?')} GB/s (unbuffered, 2 GiB) |")
    plan = {"Utilisation normale": "Balanced", "Performances élevées": "High performance", "Économie d’énergie": "Power saver"}.get(hw.get("power_plan"), hw.get("power_plan"))
    L += [f"| OS | {hw['os']}; power plan: {plan or '?'} |"]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="write the raw result here")
    ap.add_argument("--strata", default=str(Path(__file__).resolve().parents[1] / "runtimes" / "strata"))
    ap.add_argument("--model-file", help="a large model file; its drive is described and read-tested")
    a = ap.parse_args()
    hw = collect(Path(a.strata), Path(a.model_file) if a.model_file else None)
    if a.json:
        Path(a.json).write_text(json.dumps(hw, indent=1), encoding="utf-8")
    print(render_markdown(hw))
    return 0


if __name__ == "__main__":
    sys.exit(main())
