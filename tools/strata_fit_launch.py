#!/usr/bin/env python3
"""Start Strata with the largest context window that fits the GPU memory that is free right now.

    python tools/strata_fit_launch.py --config configs/strata-iq2_xs.json            # compute, show it, ask, then start the server (fast mode is on; --no-fast turns it off)
    python tools/strata_fit_launch.py --config configs/strata-iq2_xs.json --always-start   # no question (still refuses below the minimum)
    python tools/strata_fit_launch.py --config configs/strata-coder-iq1_m.json --dry-run
    python tools/strata_fit_launch.py --config configs/strata-iq2_xs.json --verify    # start, check, shrink if the engine says no
    python tools/strata_fit_launch.py --config configs/strata-coder-iq1_m.json --allow-kv-grow   # KV cache grows on demand: bigger window, risk of engine exits

How the window is computed (all in MiB; numbers per model in configs/vram-model.json):
    free      = GPU total - GPU memory used by everything else (the desktop)
    budget    = free - dense weights - draft head - VRAM reserve - minimum expert cache - safety margin
    window    = (budget - KV base) / KV per token      (rounded down to a multiple of 4096; at least --min-window (default 32768:
                a smaller window is of little use for coding) and at most --max-window (default: the model's maximum, 262144))
Everything is read from the GPU at start time, so a bigger card gives a bigger window and a busier desktop a smaller one.
The computed window is shown BEFORE anything starts and you are asked to confirm (y, n, or a smaller number of tokens) unless --always-start is given.
The KV cache is reserved up front (`--kv-grow` is removed), so nothing can grow into the margin later; that is what made the engine
exit on the first long request when `--kv-grow` was on. With --verify the script starts the server, sends a short request, and when the engine
reports 'about K MiB more than this card has free' it shrinks the window by that amount and tries again (up to 5 times).
With --allow-kv-grow the KV cache is NOT reserved up front: only the minimum window's KV has to fit when Strata starts, and the window is the model's
verified maximum. The Coder reached 119K-token prompts only this way (it does not start at 65,536 with the KV reserved), but the engine may exit with
"only N MiB VRAM free at request start" on a long request when the VRAM is tight (HTTP 503; Strata restarts it by itself and a retry goes through).
It cannot be combined with --fast (the head alias crashes the engine with --kv-grow on).
The window shrinks when your desktop uses more GPU memory, and grows back when it uses less. Below --min-window it refuses and says
how much memory is missing. The cost model is provisional: tools/fit_sweep.py measures the real limits to refine it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "runtimes" / "strata" / "tools"))
import gpu_guard                          # noqa: E402

STEP = 4096


def gpu_memory() -> tuple[int, int]:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader,nounits"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL).stdout
    total, used = (int(x) for x in out.splitlines()[0].split(","))
    return total, used


def arg_value(args: list, flag: str, default=None):
    return args[args.index(flag) + 1] if flag in args[:-1] else default


def dense_of(model: dict, fast: bool) -> int:
    """Weights + fixed buffers in MiB. The fast mode (head alias) lends the output head's VRAM to the prompt path, so it needs less."""
    return int(model.get("fast_dense_mib", model["dense_mib"])) if fast else int(model["dense_mib"])


def compute(cfg: dict, model: dict, total: int, used: int, margin: int, max_window: int, min_window: int, fast: bool = False, kv_grow: bool = False) -> dict:
    args = cfg["args"]
    reserve = int(arg_value(args, "--vram-reserve-mib", 1024))
    kv = model["kv_q4_0"] if arg_value(args, "--kv", "q4_0") == "q4_0" else None
    if kv is None:
        raise SystemExit("this cost model only knows --kv q4_0; change the config or extend configs/vram-model.json")
    vocab = cfg.get("draft_vocab", "cjk")
    draft = model["draft_head_mib"].get(vocab, max(model["draft_head_mib"].values())) if "--mtp" in args else 0
    free = total - used
    budget = free - dense_of(model, fast) - draft - reserve - model["min_expert_cache_mib"] - margin
    window = int((budget - kv["base_mib"]) / kv["per_token_mib"]) if budget > kv["base_mib"] else 0
    window = min(max_window, window // STEP * STEP)
    if kv_grow and window >= min_window:                           # the KV cache grows on demand: only the minimum window's KV is needed at the start
        window = min(max_window, int(model.get("verified_max_window", 131072)))
    short = 0
    if window < min_window:                                        # how much memory the minimum window would need
        short = max(0, math.ceil(kv["base_mib"] + kv["per_token_mib"] * min_window - budget))
    return {"free_mib": free, "used_by_others_mib": used, "dense_mib": dense_of(model, fast), "draft_head_mib": draft, "reserve_mib": reserve,
            "min_expert_cache_mib": model["min_expert_cache_mib"], "margin_mib": margin, "budget_for_kv_mib": budget,
            "window": window, "short_mib_for_min_window": short, "kv_per_token_mib": kv["per_token_mib"]}


def confirm_window(window: int, minimum: int, always: bool, ask=input, interactive=None) -> int | None:
    """-> the window to start with, or None when the user declines. y/Enter accepts, n declines, a number (tokens, k allowed) picks a smaller one."""
    if always:
        return window
    if interactive is None:
        interactive = sys.stdin is not None and sys.stdin.isatty()
    if not interactive:
        print("No console to ask on: pass --always-start to start without confirmation.")
        return None
    while True:
        answer = ask(f"Start Strata with a context window of {window} tokens? [Y/n, or a smaller number of tokens, at least {minimum}] ").strip().lower()
        if answer in ("", "y", "yes"):
            return window
        if answer in ("n", "no"):
            return None
        m = re.fullmatch(r"(\d+)\s*(k?)", answer)
        if m:
            n = int(m.group(1)) * (1024 if m.group(2) else 1)
            if minimum <= n <= window:
                return n // 1 if n % STEP == 0 else n // STEP * STEP
            print(f"Pick a number between {minimum} and {window}.")
        else:
            print("Answer y, n or a number of tokens (for example 49152 or 48k).")


def needed_free_mib(cfg: dict, model: dict, window: int, margin: int, fast: bool = False) -> int:
    """The available (free) VRAM a window needs before Strata starts: everything that must fit plus the KV cache of that window."""
    args = cfg["args"]
    reserve = int(arg_value(args, "--vram-reserve-mib", 1024))
    draft = model["draft_head_mib"].get(cfg.get("draft_vocab", "cjk"), max(model["draft_head_mib"].values())) if "--mtp" in args else 0
    k = model["kv_q4_0"]
    return math.ceil(dense_of(model, fast) + draft + reserve + model["min_expert_cache_mib"] + margin + k["base_mib"] + k["per_token_mib"] * window)


def write_config(cfg: dict, window: int, port: int | None, fast: bool = False, kv_grow: bool = False) -> Path:
    """A temporary copy with absolute paths and --max-context set; --kv-grow is removed (KV reserved up front) unless kv_grow is True, which keeps/adds it."""
    import strata_bench_matrix as mx
    c = mx.absolutize(cfg, REPO)
    c["args"] = mx.drop_flag(c["args"], "--kv-grow")
    if kv_grow:
        c["args"] = c["args"] + ["--kv-grow"]
    c["args"] = mx.set_flag(c["args"], "--max-context", str(window))
    if fast and "--prefill-head-alias" not in c["args"]:       # the engine needs --short-read 0 for it
        c["args"] = mx.set_flag(c["args"], "--short-read", "0") + ["--prefill-head-alias"]
    if port:
        c["port"] = port
    mx.apply_draft_vocab(c)
    f = Path(tempfile.mkdtemp(prefix="strata-fit-")) / "config.json"
    f.write_text(json.dumps(c, indent=1), encoding="utf-8")
    return f


def find_opencode() -> str | None:
    """OPENCODE_EXE, else the Windows desktop app (OpenCode.exe), else 'opencode' on the PATH. The PATH is not changed."""
    import shutil
    env = os.environ.get("OPENCODE_EXE")
    if env and Path(env).is_file():
        return env
    local = os.environ.get("LOCALAPPDATA")
    if local:
        app = Path(local) / "Programs" / "@opencodedesktop" / "OpenCode.exe"
        if app.is_file():
            return str(app)
    return shutil.which("opencode")


def follow_log(path: Path, proc, from_start: bool = False) -> None:
    """Show the server's log on this console as it grows (prompt reading progress, answers, warnings) until the server process ends."""
    import threading

    def run() -> None:
        try:
            with open(path, "rb") as f:
                if not from_start:
                    f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        text = line.decode("utf-8", errors="replace").rstrip()
                        if text:
                            print(text, flush=True)
                    elif proc.poll() is not None:
                        return
                    else:
                        time.sleep(0.3)
        except OSError:
            return
    threading.Thread(target=run, daemon=True).start()


def server_cmd(cfg_file: Path, port: int) -> list:
    return [sys.executable, str(REPO / "runtimes" / "strata" / "serve" / "server.py"), "--engine", "strata", "--config", str(cfg_file),
            "--port", str(port), "--fit-max-tokens"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(REPO / "configs" / "strata-iq2_xs.json"))
    ap.add_argument("--profile", help="a profile from configs/profiles.json (quality, big-context, fastest): its model config and options")
    ap.add_argument("--max-window", type=int, help="default: the model's maximum context from configs/vram-model.json")
    ap.add_argument("--min-window", type=int, default=32768, help="refuse to start below this (default 32768)")
    ap.add_argument("--always-start", action="store_true", help="start without asking, as long as the minimum window fits")
    ap.add_argument("--fast", action="store_true", help="fast mode (the default since engine 0.1.44): --prefill-head-alias --short-read 0: about 1.5 to 2x faster prompts, "
                    "needs less VRAM; requires --kv-grow off, one GPU, --mtp")
    ap.add_argument("--no-fast", action="store_true", help="switch the fast mode off (the safe mode of engine 0.1.43: the KV cache is reserved up front, no head alias)")
    ap.add_argument("--allow-kv-grow", action="store_true", help="grow the KV cache on demand instead of reserving it: a bigger window fits, but the engine may exit on a long request "
                    "when the VRAM is tight (not with --fast)")
    ap.add_argument("--opencode", choices=("audit", "update"), help="once the model is up, audit or update the OpenCode config (tools/opencode_check.py: context, output, "
                    "compaction, model id); implies --verify (the server is started and watched by this script)")
    ap.add_argument("--thinking", choices=("default", "low", "off"), default="default",
                    help="with --opencode: default keeps the model's full thinking (for coding); low or off set a shorter or no thinking phase in the OpenCode config "
                    "(quicker chat replies, lower code quality). The next launch without it puts the default back.")
    ap.add_argument("--start-opencode", metavar="DIR", nargs="?", const=".", help="then start OpenCode in a new console, in DIR (default: the current folder)")
    ap.add_argument("--margin-mib", type=int, default=150, help="extra safety room")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--dry-run", action="store_true", help="only print the computed window")
    ap.add_argument("--verify", action="store_true", help="start, test with a short request, shrink on the engine's complaint, then keep serving")
    a, rest = ap.parse_known_args()
    if rest:
        ap.error(f"unrecognized arguments: {' '.join(rest)}")
    if a.profile:
        profiles = json.loads((REPO / "configs" / "profiles.json").read_text(encoding="utf-8"))
        prof = profiles.get(a.profile)
        if prof is None:
            raise SystemExit(f"no profile '{a.profile}' in configs/profiles.json (have: {', '.join(k for k in profiles if not k.startswith('_'))})")
        a.config = str(REPO / prof["config"])
        if prof.get("options"):
            a = ap.parse_args(list(prof["options"]) + sys.argv[1:])
            a.config = str(REPO / prof["config"])
        print(f"Profile '{a.profile}' (reviewed {prof.get('reviewed')}): {prof.get('why')}")
    if a.allow_kv_grow and a.fast:
        raise SystemExit("--allow-kv-grow cannot be combined with --fast: the head alias crashes the engine when --kv-grow is on")
    a.fast = not a.no_fast and not a.allow_kv_grow                 # on by default; --allow-kv-grow needs it off
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8-sig"))
    table = json.loads((REPO / "configs" / "vram-model.json").read_text(encoding="utf-8"))["models"]
    model = table.get(cfg.get("model_name"))
    if model is None:
        raise SystemExit(f"no cost model for '{cfg.get('model_name')}' in configs/vram-model.json")
    total, used = gpu_memory()
    if a.max_window is None:
        a.max_window = int(model.get("max_context", 262144))
    running = gpu_guard.port_listeners(a.port)
    if running:
        print(f"Note: a server is already listening on port {a.port} (PID {running[0]}); the GPU memory below includes it, so the window would be wrong.")
        if not a.dry_run:
            raise SystemExit(3)
    r = compute(cfg, model, total, used, a.margin_mib, a.max_window, a.min_window, a.fast, a.allow_kv_grow)
    print(f"Available (free) VRAM: {r['free_mib']} MiB of {total} MiB" + ("   [fast mode: --prefill-head-alias]" if a.fast else ""))
    need_min = needed_free_mib(cfg, model, a.min_window, a.margin_mib, a.fast)
    print("Available VRAM needed per context window (this model):")
    if a.allow_kv_grow:
        print(f"  (--allow-kv-grow) any window up to {int(model.get('verified_max_window', 131072))} tokens: {need_min:>6} MiB at the start; the KV cache grows on demand")
    for w in (a.min_window, 65536, 98304, 131072, 196608, a.max_window) if not a.allow_kv_grow else ():
        if w >= a.min_window and w <= a.max_window:
            n = needed_free_mib(cfg, model, w, a.margin_mib, a.fast)
            print(f"  {w:>7} tokens: {n:>6} MiB   {'<- fits now' if n <= r['free_mib'] else ''}")
    if r["window"] < a.min_window:
        print(f"Does not fit: the smallest window ({a.min_window} tokens) needs {need_min} MiB of available VRAM; {r['free_mib']} MiB are available "
              f"({need_min - r['free_mib']} MiB short).")
        return 2
    print(f"Largest window for the VRAM available now: {r['window']} tokens (limits: at least {a.min_window}, at most {a.max_window})")
    if a.allow_kv_grow:
        print("Warning: --allow-kv-grow. The KV cache grows on demand, so the VRAM needed at the start is that of the minimum window only; on a long request the engine "
              "may exit (HTTP 503, 'only N MiB VRAM free at request start'). Strata restarts it by itself, a retry goes through. Not tested above "
              f"{int(model.get('verified_max_window', 131072))} tokens.")
    if a.opencode or a.start_opencode:
        a.verify = True
    if a.dry_run:
        print("Dry run: nothing started." + ("" if a.always_start else " Without --always-start you would be asked to confirm."))
        return 0
    verified = int(model.get("verified_max_window", 131072))
    if r["window"] > verified:
        print(f"Note: the cost model was measured up to {verified} tokens; above that it is extrapolated and a test with a 217,088-token window "
              f"was 557 MiB short of what it predicted. The launcher will check with the engine and shrink the window if the engine says no (--verify).")
        a.verify = True
    chosen = confirm_window(r["window"], a.min_window, a.always_start)
    if chosen is None:
        print("Not started.")
        return 1
    r["window"] = chosen
    gpu_guard.require_free_port(a.port)
    window = r["window"]
    with gpu_guard.GpuLock("fit-launch"):
        for attempt in range(1, 6 if a.verify else 2):
            cfg_file = write_config(cfg, window, a.port, a.fast, a.allow_kv_grow)
            cmd = server_cmd(cfg_file, a.port)
            print(f"Starting Strata with --max-context {window} ...", flush=True)
            if not a.verify:
                return subprocess.call(cmd, cwd=str(REPO / "runtimes" / "strata"))
            import crash_probe
            import strata_bench
            log = cfg_file.with_name("server.log")
            proc = strata_bench.start_server(cfg_file, a.port, None, log)
            ok = strata_bench.wait_ready(f"http://127.0.0.1:{a.port}", "", proc, 900) and \
                crash_probe.post(f"http://127.0.0.1:{a.port}", "Say hello.", 16, 1800)[0] == 200
            if ok:
                print(f"Verified: the engine started with a window of {window} tokens. Serving on port {a.port} (Ctrl+C stops it).")
                if a.opencode:
                    import opencode_check
                    print()
                    opencode_check.run(opencode_check.default_config_path(), f"http://127.0.0.1:{a.port}/v1", window, None, a.opencode, thinking=a.thinking)
                    print()
                if a.start_opencode:
                    exe = find_opencode()
                    if exe:
                        subprocess.Popen([exe], cwd=str(Path(a.start_opencode).resolve()), creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if exe.lower().endswith("cli.exe") else 0)
                        print(f"Started OpenCode ({Path(exe).name}) in {Path(a.start_opencode).resolve().name}.")
                    else:
                        print("OpenCode was not found (set OPENCODE_EXE to its .exe, or start it yourself).")
                import opencode_check
                ident = opencode_check.probe_server(f"http://127.0.0.1:{a.port}/v1")["model_id"] or "the model"
                bar = "=" * 78
                print(bar)
                print("  The server is ready. You can now use the model in OpenCode.")
                print(f"  Model: {ident}   Window: {window} tokens   http://127.0.0.1:{a.port}/v1")
                print("  Keep this window open while you work (Ctrl+C stops the server).")
                print(bar, flush=True)
                print(f"Server log (also in {log}):", flush=True)
                follow_log(log, proc)
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    strata_bench.stop_server(proc)
                return 0
            strata_bench.stop_server(proc)
            text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
            m = re.findall(r"about (\d+) MiB more than this card has free", text)
            need = int(m[-1]) + a.margin_mib if m else 512
            window = max(0, (window - int(need / r["kv_per_token_mib"])) // STEP * STEP)
            print(f"The engine did not start (needs about {need} MiB more); trying a window of {window} tokens", flush=True)
            if window < a.min_window:
                print("Does not fit.")
                return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
