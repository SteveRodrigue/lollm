#!/usr/bin/env python3
"""Benchmark Strata settings on this machine, one change at a time, and write a shareable markdown report.

    .venv\\Scripts\\python.exe tools\\strata_bench_matrix.py [--config configs/strata-iq2_xs.json]
        [--only baseline,no-mtp] [--runs 3] [--long] [--out reports/strata-bench/<stamp>] [--report docs/strata-benchmarks.md]
    .venv\\Scripts\\python.exe tools\\strata_bench_matrix.py --report-only reports/strata-bench/<stamp>

For every variant it writes a modified copy of the config, starts Strata with it through Strata's own
`tools/strata_bench.py` (fixed suite over the HTTP API: chat decode, 4K/16K fresh prompts, agent session with
conversation cache; medians of --runs runs), and keeps each variant's results.json. Variants that are finished
are skipped when you run it again with the same --out (use --force to redo). The baseline runs again at the end
to show drift (thermals, background load). Hardware facts and measured RAM/VRAM/PCIe/disk bandwidth come from
tools/strata_hwinfo.py. The final report is docs/strata-benchmarks.md (host and user names, absolute paths are
not written).
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STRATA = REPO / "runtimes" / "strata"
BENCH = STRATA / "tools" / "strata_bench.py"
HWINFO = REPO / "tools" / "strata_hwinfo.py"


# ----------------------------------------------------------------------------------------------- config edits
def drop_flag(args: list, flag: str) -> list:
    """Remove `flag` and its value (when the next item is not another flag)."""
    out, i = [], 0
    while i < len(args):
        if args[i] == flag:
            i += 2 if i + 1 < len(args) and not str(args[i + 1]).startswith("--") else 1
        else:
            out.append(args[i])
            i += 1
    return out


def set_flag(args: list, flag: str, value: str) -> list:
    args = list(args)
    if flag in args[:-1]:
        args[args.index(flag) + 1] = value
        return args
    return args + [flag, value]


def v_baseline(c):
    return c


def v_no_kv_grow(c):
    c["args"] = drop_flag(c["args"], "--kv-grow")


def v_k8v4(c):
    c["args"] = set_flag(c["args"], "--kv", "k8v4")


def v_no_mtp(c):
    c["args"] = drop_flag(c["args"], "--mtp")      # a native pack needs --spec T >= 2, so only the draft layer goes


def v_reserve(mib):
    def f(c):
        c["args"] = set_flag(c["args"], "--vram-reserve-mib", str(mib))
    return f


def v_ctx(n):
    def f(c):
        c["args"] = set_flag(c["args"], "--max-context", str(n))
    return f


def v_env(**kv):
    def f(c):
        c.setdefault("env", {}).update(kv)
    return f


def v_draft_en(c):
    c["draft_vocab"] = "en"


def chain(*fns):
    def f(c):
        for fn in fns:
            fn(c)
    return f


# name -> (what changes vs the current config, edit function)
VARIANTS = {
    "baseline": ("the config as it is now (`--spec 4 --mtp`, `--kv q4_0`, `--kv-grow`, reserve 1024 MiB, 131072 context)", v_baseline),
    "no-kv-grow": ("without `--kv-grow` (documented as incompatible with the low-RAM/mmap mode)", v_no_kv_grow),
    "kv-k8v4": ("`--kv k8v4` instead of `q4_0` (docs: 23% less KV than 8-bit, better quality than 4-bit)", v_k8v4),
    "no-mtp": ("no `--mtp` (`--spec 4` stays: a native pack requires it): frees the draft layer's 0.7-1 GiB for the expert cache", v_no_mtp),
    "reserve-700": ("`--vram-reserve-mib 700` (default-ish) instead of 1024", v_reserve(700)),
    "reserve-1200": ("`--vram-reserve-mib 1200`", v_reserve(1200)),
    "reserve-1300": ("`--vram-reserve-mib 1300`", v_reserve(1300)),
    "reserve-1400": ("`--vram-reserve-mib 1400`", v_reserve(1400)),
    "ctx64k-r1400": ("`--max-context 65536` + `--vram-reserve-mib 1400` (a smaller window so the KV cache has less room to grow into VRAM)", chain(v_ctx(65536), v_reserve(1400))),
    "spec07": ("`--spec-min-p 0.7` (Strata's calibration picked it: +6% decode in its own measurement, default 0.5)", lambda c: c.__setitem__("args", set_flag(c["args"], "--spec-min-p", "0.7"))),
    "calib": ("both calibration picks: `--spec-min-p 0.7` and `--pcie-frac 0.35` (default 0.36, measured by the engine)",
              lambda c: c.__setitem__("args", set_flag(set_flag(c["args"], "--spec-min-p", "0.7"), "--pcie-frac", "0.35"))),
    "conservative": ("very conservative: `--max-context 32768`, no `--kv-grow` (the KV cache is small and reserved up front, so it cannot squeeze the VRAM later), English draft vocabulary (~215 MiB less VRAM)",
                     chain(v_no_kv_grow, v_ctx(32768), v_draft_en)),
    "iq3-64k": ("no `--kv-grow`, `--max-context 65536`, English draft vocabulary: the smallest setup that still holds the 64K TS project prompts (fallback when the default does not start)",
                chain(v_no_kv_grow, v_ctx(65536), v_draft_en)),
    "head-alias": ("`--prefill-head-alias` (engine 0.1.44+, opt-in, 8 GB cards): the output head's VRAM holds the prompt buffers while a prompt is read; docs/PREFILL_HEAD_ALIAS.md",
                   lambda c: c.__setitem__("args", set_flag(c["args"], "--short-read", "0") + ["--prefill-head-alias"])),   # the engine refuses the flag unless --short-read is 0
    "ha-nkg-64k": ("`--prefill-head-alias` (+ `--short-read 0`) without `--kv-grow`, window 65536 (to tell whether the head-alias crash on real prompts depends on `--kv-grow`)",
                   chain(v_no_kv_grow, v_ctx(65536), lambda c: c.__setitem__("args", set_flag(c["args"], "--short-read", "0") + ["--prefill-head-alias"]))),
    "ha-nkg-96k": ("fast mode (`--prefill-head-alias --short-read 0`, no `--kv-grow`) with a 98,304-token window: leaves ~40K tokens of output room after a 57K prompt (the 65,536 window left only 6 to 10K and cut long reasoning short)",
                   chain(v_no_kv_grow, v_ctx(98304), lambda c: c.__setitem__("args", set_flag(c["args"], "--short-read", "0") + ["--prefill-head-alias"]))),
    "ha-nkg-128k": ("fast mode (`--prefill-head-alias --short-read 0`, no `--kv-grow`) with a 131,072-token window: leaves ~73K tokens of output room after a 57K prompt (IQ3_XXS's largest verified window)",
                   chain(v_no_kv_grow, v_ctx(131072), lambda c: c.__setitem__("args", set_flag(c["args"], "--short-read", "0") + ["--prefill-head-alias"]))),
    "reserve-1600": ("`--vram-reserve-mib 1600` (the value the engine itself suggests when VRAM is nearly full at the start of a long request)", v_reserve(1600)),
    "reserve-2048": ("`--vram-reserve-mib 2048` (hypothesis: more free VRAM for the prompt path, fewer cached experts)", v_reserve(2048)),
    "reserve-3072": ("`--vram-reserve-mib 3072`", v_reserve(3072)),
    "reserve-1536": ("`--vram-reserve-mib 1536`", v_reserve(1536)),
    "ctx-32k": ("`--max-context 32768` instead of 131072", v_ctx(32768)),
    "draft-vocab-en": ("`draft_vocab: en` (saves ~110 MiB VRAM; fewer drafts for non-English)", v_draft_en),
    "tail-skip-off": ("`STRATA_ROUTE_TAIL_SKIP=0`: exact routing, no skipped missed experts", v_env(STRATA_ROUTE_TAIL_SKIP="0")),
    "file-release": ("`STRATA_FILE_RELEASE=1` (Windows: trim mapped expert pages after upload)", v_env(STRATA_FILE_RELEASE="1")),
    "ram-cap": ("RAM capped for a 32 GB PC: `--resident-budget-gib 20`, `STRATA_RESIDENT_HEADROOM_GIB=2`, `STRATA_RESIDENT_PIN=0` (pageable)",
                chain(lambda c: c.__setitem__("args", c["args"] + ["--resident-budget-gib", "20"]),
                      v_env(STRATA_RESIDENT_HEADROOM_GIB="2", STRATA_RESIDENT_PIN="0"))),
    # "combo" (k8v4 without --kv-grow) was tried and does not start: the engine reports no VRAM left for the expert cache
    "nkg-reserve-700": ("no `--kv-grow` + `--vram-reserve-mib 700`", chain(v_no_kv_grow, v_reserve(700))),
    "nkg-no-mtp": ("no `--kv-grow` + no `--mtp` (`--spec 4` stays)", chain(v_no_kv_grow, v_no_mtp)),
    "nkg-ctx-64k": ("no `--kv-grow` + `--max-context 65536`", chain(v_no_kv_grow, v_ctx(65536))),
    "long-300": ("no `--kv-grow` + `--vram-reserve-mib 300` (the engine says 300 is enough on a small card): room for a 160K window", chain(v_no_kv_grow, v_reserve(300))),
    "long-300-en": ("`long-300` + `draft_vocab: en` (saves ~143 MiB): room for a 192K window", chain(v_no_kv_grow, v_reserve(300), v_draft_en)),
    "nkg-en": ("no `--kv-grow` + the English draft vocabulary actually applied (`draft_vocab: en`, ~215 MiB less VRAM)", chain(v_no_kv_grow, v_draft_en)),
    "nkg-recheck": ("no `--kv-grow` again, last: drift check for the best setting", v_no_kv_grow),
}
DEFAULT_ORDER = ["baseline", "no-kv-grow", "kv-k8v4", "no-mtp", "reserve-700", "ctx-32k", "tail-skip-off", "ram-cap",
                 "nkg-reserve-700", "nkg-no-mtp", "nkg-ctx-64k", "nkg-recheck"]


def apply_draft_vocab(cfg: dict) -> None:
    """The config's `draft_vocab` key is only honoured by Strata's setup.py start path; we start serve/server.py directly,
    so copy the chosen subset (default cjk) into the draft folder ourselves before every start."""
    args = cfg["args"]
    if "--mtp" not in args[:-1]:
        return
    sys.path.insert(0, str(STRATA))
    import setup as strata_setup
    strata_setup.refresh_draft_vocab(Path(args[args.index("--mtp") + 1]), cfg.get("draft_vocab", "cjk"))


def absolutize(cfg: dict, base: Path) -> dict:
    """Paths in the config are relative to the repo; Strata's bench runs from the Strata folder."""
    def fix(v):
        if isinstance(v, str) and not Path(v).is_absolute() and (base / v).exists():
            return str((base / v).resolve())
        return v
    cfg = copy.deepcopy(cfg)
    cfg["exe"] = fix(cfg["exe"])
    cfg["args"] = [fix(a) if isinstance(a, str) else a for a in cfg["args"]]
    for k in ("tokenizer",):
        if k in cfg:
            cfg[k] = fix(cfg[k])
    cfg["lib_dirs"] = [fix(d) for d in cfg.get("lib_dirs", [])]
    cfg["cwd"] = str(base.resolve())
    cfg["log"] = str((base / "logs" / "strata-bench.log").resolve())
    return cfg


# ---------------------------------------------------------------------------------------------------- running
def run_variant(name: str, cfg: dict, out: Path, a) -> dict | None:
    apply_draft_vocab(cfg)
    cfg_file = out / "configs" / f"{name}.json"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    rdir = out / "runs" / name
    cmd = [sys.executable, str(BENCH), "--config", str(cfg_file), "--out", str(rdir), "--runs", str(a.runs),
           "--ready-timeout", str(a.ready_timeout)]
    if a.long:
        cmd.append("--long")
    print(f"\n=== {name}: starting ({datetime.datetime.now():%H:%M:%S}) ===", flush=True)
    t0 = time.time()
    log = out / "runs" / f"{name}.console.txt"
    log.parent.mkdir(parents=True, exist_ok=True)
    import psutil
    import gpu_guard
    port = int(cfg.get("port", 8080))
    gpu_guard.require_free_port(port)
    lock = gpu_guard.GpuLock(f"matrix:{name}").__enter__()
    peak = {"used": 0.0, "commit": 0.0}
    with open(log, "w", encoding="utf-8", errors="replace") as lf:
        proc = subprocess.Popen(cmd, cwd=str(STRATA), stdout=lf, stderr=subprocess.STDOUT)
        while proc.poll() is None:
            vm = psutil.virtual_memory()
            peak["used"] = max(peak["used"], (vm.total - vm.available) / 2 ** 30)
            time.sleep(2)
        rc = proc.returncode
    lock.release()
    (out / "runs" / f"{name}.peak-ram.json").write_text(json.dumps({"peak_ram_used_gib": round(peak["used"], 1)}), encoding="utf-8")
    found = sorted(rdir.glob("*/results.json"))
    if found:                                               # identity check: the benchmark must have started and measured OUR model
        r0 = json.loads(found[-1].read_text(encoding="utf-8"))
        why = []
        if not r0["params"].get("started_server"):
            why.append("the benchmark used a server that was already running")
        if cfg.get("model_name") and r0["machine"].get("model") != cfg["model_name"]:
            why.append(f"it measured '{r0['machine'].get('model')}', not '{cfg['model_name']}'")
        if why:
            bad = out / "invalid" / f"{name}-{datetime.datetime.now():%H%M}"
            bad.parent.mkdir(exist_ok=True)
            shutil.move(str(rdir), str(bad))
            print(f"    INVALID, moved to {bad.name}: {'; '.join(why)}", flush=True)
            found = []
    print(f"    exit {rc}, {time.time() - t0:.0f} s, {'results saved' if found else 'NO RESULTS (see ' + log.name + ')'}", flush=True)
    return json.loads(found[-1].read_text(encoding="utf-8")) if found else None


def export_data(out: Path, dest: Path) -> None:
    """Keep the raw, already-redacted results beside the report (results.json, per-variant README, log excerpt,
    peak RAM, hardware.json).  Configs and console logs hold absolute paths and are not copied."""
    dest.mkdir(parents=True, exist_ok=True)
    for f in (out / "runs").glob("*/*/*"):
        if f.name in ("results.json", "README.md", "engine-log-excerpt.txt"):
            t = dest / f.parent.parent.name
            t.mkdir(exist_ok=True)
            shutil.copy2(f, t / f.name)
    for f in (out / "runs").glob("*.peak-ram.json"):
        shutil.copy2(f, dest / f.name)
    if (out / "hardware.json").exists():
        shutil.copy2(out / "hardware.json", dest / "hardware.json")


def load_all(out: Path) -> dict:
    res = {}
    for f in sorted((out / "runs").glob("*/*/results.json")):
        res[f.parent.parent.name] = json.loads(f.read_text(encoding="utf-8"))
    return res


# ----------------------------------------------------------------------------------------------------- report
def med(stat, d=1):
    return f"{stat['median']:.{d}f}" if stat else "n/a"


def rng(stat, d=1):
    return f"{stat['median']:.{d}f} ({stat['min']:.{d}f}-{stat['max']:.{d}f})" if stat else "n/a"


def pct(new, old):
    if not new or not old or not old.get("median"):
        return ""
    return f" ({(new['median'] / old['median'] - 1) * 100:+.1f}%)"


def peak_ram(out: Path, name: str) -> str:
    f = out / "runs" / f"{name}.peak-ram.json"
    try:
        return str(json.loads(f.read_text(encoding="utf-8"))["peak_ram_used_gib"])
    except (OSError, ValueError, KeyError):
        return "n/a"


def metrics(r: dict) -> dict:
    o = r["results"]
    p = o.get("prompts", {})
    a = o.get("agent") or {}
    return {"chat_dec": o["chat"].get("decode_tps"), "chat_ttft": o["chat"].get("ttft_s"),
            "p4": (p.get("4K") or {}).get("prompt_tps"), "p4_ttft": (p.get("4K") or {}).get("ttft_s"),
            "p16": (p.get("16K") or {}).get("prompt_tps"), "p16_ttft": (p.get("16K") or {}).get("ttft_s"),
            "p32": (p.get("32K") or {}).get("prompt_tps"),
            "ag_dec": a.get("turn_decode_tps"), "ag_ttft": a.get("turn_ttft_s"), "ag_hit": a.get("hit_pct")}


def render_report(out: Path, results: dict, hw: dict | None, args_meta: dict, planned: list | None = None, findings: str | None = None) -> str:
    sys.path.insert(0, str(REPO / "tools"))
    import strata_hwinfo
    base = results.get("baseline")
    first = next(iter(results.values()))
    mc = first["machine"]
    L = ["# Strata on an 8 GB GPU: setting-by-setting benchmark", "",
         f"Measured {first['date']} on a consumer desktop with an **{' + '.join(mc.get('gpu') or ['?'])}** "
         f"({(mc.get('gpu_vram_mib') or 0) // 1024} GiB VRAM) and {mc.get('ram_gib')} GiB RAM. Strata project {mc.get('strata_version')}, "
         f"commit `{mc.get('strata_commit')}`, engine {mc.get('engine_version')}. Model: {mc.get('model')} ({mc.get('quant')}), "
         f"{mc.get('context')}-token context. Each variant changes one thing from the baseline config; "
         f"{first['params']['runs']} run(s) per test, medians with ranges. Speed only: no output-quality check was run.", "",
         *([findings.strip(), ""] if findings else []),
         "## Hardware", ""]
    L.append(strata_hwinfo.render_markdown(hw) if hw else "_Hardware details not collected._")
    L += ["", "Bandwidths are measured with `tools/strata_hwinfo.py` (RAM: 8 threads numpy read/copy; VRAM: `cudaMemcpy` "
          "device-to-device, counting read+write traffic; PCIe: 256 MiB `cudaMemcpy`, link read from `nvidia-smi` while copying; "
          "disk: unbuffered sequential read from the middle of the model file). Background load was not controlled.", ""]
    L += ["## Results", "",
          "Decode = tokens generated per second; prompt = prompt tokens ingested per second on a fresh (uncached) prompt; "
          "TTFT = time to first token. Peak RAM = highest system memory in use (total minus available, file cache excluded) while the variant ran. Percentages are relative to the first baseline run.", "",
          "| Variant | Chat decode tok/s | Chat TTFT s | 4K prompt tok/s | 16K prompt tok/s | 16K TTFT s | Agent decode tok/s | Agent TTFT s | Agent cache hit % | Peak RAM in use GiB |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    bm = metrics(base) if base else None
    planned = planned or []
    order = [k for k in planned if k in results] + [k for k in results if k not in planned]
    pending = [k for k in planned if k not in results and k not in args_meta.get("failed", [])]
    for name in planned + [k for k in order if k not in planned]:
        if name in pending:
            L.append(f"| {name} | " + " | ".join(["Pending..."] * 9) + " |")
            continue
        if name not in results:
            if name in args_meta.get("failed", []):
                L.append(f"| {name} | " + " | ".join(["Failed (see below)"] * 9) + " |")
            continue
        m = metrics(results[name])
        label = name
        L.append(f"| {label} | {rng(m['chat_dec'])}{pct(m['chat_dec'], bm and bm['chat_dec']) if name != 'baseline' else ''} | "
                 f"{rng(m['chat_ttft'], 2)} | {rng(m['p4'], 0)}{pct(m['p4'], bm and bm['p4']) if name != 'baseline' else ''} | "
                 f"{rng(m['p16'], 0)}{pct(m['p16'], bm and bm['p16']) if name != 'baseline' else ''} | {rng(m['p16_ttft'], 1)} | "
                 f"{rng(m['ag_dec'])}{pct(m['ag_dec'], bm and bm['ag_dec']) if name != 'baseline' else ''} | {rng(m['ag_ttft'], 2)} | {med(m['ag_hit'])} | {peak_ram(out, name)} |")
    if "baseline-recheck" in results and bm:
        r = metrics(results["baseline-recheck"])
        L += ["", f"Drift check: the baseline re-run at the end differs by {pct(r['chat_dec'], bm['chat_dec']).strip(' ()') or 'n/a'} in chat decode and "
              f"{pct(r['p16'], bm['p16']).strip(' ()') or 'n/a'} in 16K prompt speed; differences smaller than that are noise."]
    L += ["", "## What each variant changes", ""]
    order = order + pending
    for name in order:
        desc = VARIANTS.get(name, (name, None))[0] if name != "baseline-recheck" else "the baseline again, last (drift check)"
        L.append(f"- **{name}**: {desc}")
    L += ["", "## Launch line and settings of the baseline", ""]
    if base and base["machine"].get("launch"):
        L += ["```text", base["machine"]["launch"], "```", ""]
    cfgv = (base or first)["machine"].get("config") or {}
    extra = {k: v for k, v in cfgv.items() if k not in ("exe", "args", "lib_dirs", "env")}
    if extra:
        L += ["Server settings: " + ", ".join(f"`{k}={v}`" for k, v in extra.items() if k != "env"), ""]
    L += ["## Failures and skipped tests", ""]
    bad = False
    for name in order:
        if name not in results:
            continue
        o = results[name]["results"]
        for k, v in (o.get("skipped") or {}).items():
            L.append(f"- {name}: skipped {k}: {v}")
            bad = True
        for f in o.get("failures") or []:
            L.append(f"- {name}: failed {f['where']}: {f['error']}")
            bad = True
    for name in args_meta.get("failed", []):
        L.append(f"- {name}: the server did not start or no result was produced")
        bad = True
    if not bad:
        L.append("None.")
    L += ["", "## Method and limits", "",
          "- Tool: Strata's `tools/strata_bench.py` (suite described in its docs/COMMUNITY_BENCHMARKS.md), driven by "
          "`tools/strata_bench_matrix.py`, which restarts the server for every variant with a modified copy of the config.",
          "- Thinking is off, temperature 0. The agent session reuses the model's own replies, so token counts vary slightly per run.",
          "- Strata's route-tail skip (on by default since 0.1.42) changes answers slightly; no correctness check was run here.",
          "- One machine, one model pack, one OS session per variant; ranges show run-to-run spread, not a statistical test.",
          "- Hostname, user name, absolute paths and IP addresses are not recorded.", "",
          "## Reproduce", "",
          "```text", "python tools/strata_bench_matrix.py --only baseline,kv-k8v4,no-mtp", "```", ""]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(REPO / "configs" / "strata-iq2_xs.json"))
    ap.add_argument("--only", help="comma-separated variants; available: " + ", ".join(VARIANTS))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--long", action="store_true", help="also the 32K prompt test (slower)")
    ap.add_argument("--out", help="working folder (default reports/strata-bench/<timestamp>)")
    ap.add_argument("--report", default=str(REPO / "docs" / "strata-benchmarks.md"))
    ap.add_argument("--report-only", metavar="OUTDIR", help="rebuild the report from an earlier run folder and stop")
    ap.add_argument("--force", action="store_true", help="redo variants that already have results")
    ap.add_argument("--no-recheck", action="store_true", help="skip the final baseline re-run")
    ap.add_argument("--ready-timeout", type=int, default=1800)
    ap.add_argument("--skip-hw", action="store_true")
    a = ap.parse_args()

    out = Path(a.report_only or a.out or REPO / "reports" / "strata-bench" / datetime.datetime.now().strftime("%Y%m%d-%H%M")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg0 = json.loads(Path(a.config).read_text(encoding="utf-8-sig"))
    failed: list[str] = []

    names = [n.strip() for n in a.only.split(",")] if a.only else DEFAULT_ORDER
    bad = [n for n in names if n not in VARIANTS]
    if bad:
        ap.error(f"unknown variant(s): {', '.join(bad)}")
    todo = list(names) + ([] if a.no_recheck or "baseline" not in names else ["baseline-recheck"])
    hwf = out / "hardware.json"

    def write_report() -> bool:
        res = load_all(out)
        if not res:
            return False
        hw = json.loads(hwf.read_text(encoding="utf-8")) if hwf.exists() else None
        fpath = REPO / "docs" / "strata-findings.md"
        findings = fpath.read_text(encoding="utf-8") if fpath.exists() and Path(a.report).name == "strata-benchmarks.md" else None
        md = render_report(out, res, hw, {"failed": failed}, todo, findings)
        for p in (out / "strata-benchmarks.md", Path(a.report)):
            p.write_text(md, encoding="utf-8")
        export_data(out, Path(a.report).with_name(Path(a.report).stem + "-data"))
        return True

    if not a.report_only:
        if not a.skip_hw and (a.force or not hwf.exists()):
            model = next((x for x in cfg0["args"] if isinstance(x, str) and x.endswith(".gguf")), None)
            subprocess.run([sys.executable, str(HWINFO), "--json", str(hwf)] + (["--model-file", str(REPO / model)] if model else []),
                           cwd=str(REPO), stdout=subprocess.DEVNULL)
        for name in todo:
            if not a.force and list((out / "runs" / name).glob("*/results.json")):
                print(f"=== {name}: already done, skipping", flush=True)
                continue
            cfg = absolutize(cfg0, REPO)
            VARIANTS[name.replace("baseline-recheck", "baseline")][1](cfg)
            if run_variant(name, cfg, out, a) is None:
                failed.append(name)
            write_report()                       # refreshed after every variant; unfinished ones show "Pending..."

    if not write_report():
        print("No results to report.", file=sys.stderr)
        return 1
    print(f"\nReport written: {Path(a.report).relative_to(REPO) if Path(a.report).is_relative_to(REPO) else a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
