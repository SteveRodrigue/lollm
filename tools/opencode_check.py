#!/usr/bin/env python3
"""Print, audit or update the OpenCode configuration for the Strata model that is running.

    python tools/opencode_check.py --audit                 # compare opencode.json with the running server, change nothing
    python tools/opencode_check.py --update                # same, then write the fixes (a backup is made first)
    python tools/opencode_check.py --print                 # only print the snippet
    python tools/opencode_check.py --audit --window 98304 --model-id NAME   # when the server does not report them

Workflow this serves: launch the model (tools/strata_fit_launch.py --opencode update), the config is brought in line, then start OpenCode.

It follows the CURRENT OpenCode config schema (https://opencode.ai/config.json): the top-level "providers" block (package / settings / models /
limit / capabilities.reasoning). The older singular "provider" block (npm / options) is marked deprecated in that schema; it is left alone.
What it checks:
    - providers.strata: baseURL = the running server, the model id the server reports, reasoning supported
    - limit.context = the window the server really serves (not more: OpenCode would send prompts the engine refuses)
    - limit.output: these models spend a lot of the output budget on reasoning; below 16,384 many coding answers ended without a patch
    - compaction: auto on, and "reserved" (deprecated in the schema but still accepted; its replacement "buffer" has no description there)
      at least the output limit, so compaction starts before the window is full
    - model: "strata/<id>" selected
    - thinking (--thinking default|low|off): default sends nothing (full thinking, best for coding); low / off add body.reasoning_effort "low" / "none"
      to the model, which Strata maps to a shorter or no thinking phase (quicker replies, lower code quality)
The config is merged, not replaced: every other key stays (also your 'package' value). The apiKey is copied, never printed.
Needs the server to be running (or --window and --model-id).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

PROVIDER = "strata"
DEFAULT_PACKAGE = "@opencode/ai/providers/openai-compatible"      # the value docs/strata.md uses; an existing value in your file is kept
THINKING = {"default": None, "low": "low", "off": "none"}      # --thinking -> the reasoning_effort Strata understands (None: not sent, the model's own default)
MIN_OUTPUT = 16384
GOOD_OUTPUT = 32768


def default_config_path() -> Path:
    env = os.environ.get("OPENCODE_CONFIG")
    if env:
        return Path(env)
    return Path.home() / ".config" / "opencode" / "opencode.json"


def http_get(url: str, timeout: float = 5.0) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:                # noqa: S310 (local server)
            return r.read().decode("utf-8", errors="replace")
    except OSError:
        return None


def window_from_metrics(text: str) -> int | None:
    """The server's /metrics is JSON ({"engine": {"max_context": N}}); a Prometheus text form (engine_max_context N) is accepted too."""
    try:
        v = json.loads(text)["engine"]["max_context"]
        return int(v) if v else None
    except (ValueError, KeyError, TypeError):
        g = re.search(r"^\S*engine_max_context\S*\s+([0-9.]+)", text, re.M)
        return int(float(g.group(1))) if g else None


def probe_server(base: str) -> dict:
    """-> {'model_id', 'window'} of the running server (None when it does not say)."""
    out: dict = {"model_id": None, "window": None}
    root = base.rstrip("/")
    root = root[:-3] if root.endswith("/v1") else root
    t = http_get(root + "/v1/models")
    if t:
        try:
            out["model_id"] = json.loads(t)["data"][0]["id"]
        except (ValueError, KeyError, IndexError):
            pass
    m = http_get(root + "/metrics")
    if m:
        out["window"] = window_from_metrics(m)
    return out


def recommended_limits(window: int, output: int | None = None, reserved: int | None = None) -> tuple[int, int]:
    """Output limit and compaction buffer for a window. 32,768 output tokens when the window is big enough, else a third of it."""
    out = output or (GOOD_OUTPUT if window >= 98304 else max(4096, window // 3 // 1024 * 1024))
    res = reserved or min(out + 4096, window // 2)
    return out, res


def effective_output(current, target: int, window: int) -> int:
    """The output limit to want: the recommended one, or a bigger value the user chose as long as it leaves half the window for the prompt."""
    return current if isinstance(current, int) and target <= current <= window // 2 else target


def desired_block(model_id: str, window: int, base: str, output: int, api_key=None, name: str | None = None, package: str | None = None) -> dict:
    settings: dict = {"baseURL": base}
    if api_key:
        settings["apiKey"] = api_key
    return {"name": name or "Strata (local)", "package": package or DEFAULT_PACKAGE, "settings": settings,
            "models": {model_id: {"name": model_id, "capabilities": {"reasoning": {"supported": True}}, "limit": {"context": window, "output": output}}}}


def current_provider(cfg: dict) -> dict | None:
    p = cfg.get("providers")
    return p.get(PROVIDER) if isinstance(p, dict) else None


def deprecated_provider(cfg: dict) -> dict | None:
    p = cfg.get("provider")
    return p.get(PROVIDER) if isinstance(p, dict) else None


def audit(cfg: dict, model_id: str, window: int, base: str, output: int, reserved: int, thinking: str = "default") -> list[tuple[str, str]]:
    """-> [(status, text)]; status is OK, FIX (will be written by --update) or WARN (needs your decision)."""
    res: list[tuple[str, str]] = []
    if deprecated_provider(cfg) is not None:
        res.append(("WARN", "the file has a 'provider.strata' block in the older form (npm/options); the schema marks the singular 'provider' key as "
                            "deprecated. --update does not touch it, but both blocks define the same provider: remove one by hand."))
    prov = current_provider(cfg)
    if prov is None:
        res.append(("FIX", f"no 'providers.{PROVIDER}' block"))
        prov = {}
    else:
        got = (prov.get("settings") or {}).get("baseURL")
        res.append(("OK" if got == base else "FIX", f"settings.baseURL = {got!r} (server: {base!r})"))
        res.append(("OK" if prov.get("package") else "FIX", f"package = {prov.get('package')!r}"))
    models = prov.get("models") or {}
    stale = [m for m in models if m != model_id]
    if stale:
        res.append(("WARN", f"other model ids in the block: {', '.join(stale)} (the server serves {model_id}); --update replaces them"))
    m = models.get(model_id)
    if m is None:
        res.append(("FIX", f"model '{model_id}' is not defined"))
    else:
        lim = m.get("limit") or {}
        ctx = lim.get("context")
        if ctx == window:
            res.append(("OK", f"limit.context = {ctx} (the window served)"))
        elif isinstance(ctx, int) and ctx > window:
            res.append(("FIX", f"limit.context = {ctx} is MORE than the window served ({window}): OpenCode would send prompts the engine refuses"))
        else:
            res.append(("FIX", f"limit.context = {ctx} (the server serves {window}; a smaller value wastes the window)"))
        out = lim.get("output")
        output = effective_output(out, output, window)
        if out == output:
            res.append(("OK", f"limit.output = {out}" + (" (bigger than recommended, kept)" if out > recommended_limits(window)[0] else "")))
        else:
            why = "too small for a thinking model: reasoning eats the budget and answers end without a patch" if not isinstance(out, int) or out < MIN_OUTPUT                 else "below the recommended output for this window"
            res.append(("FIX", f"limit.output = {out} is {why} (want {output})"))
        have = (m.get("body") or {}).get("reasoning_effort")
        want = THINKING[thinking]
        if have == want:
            res.append(("OK", f"thinking: {'the model default (full thinking, for coding)' if want is None else 'reasoning_effort ' + want + ' (quicker replies, lower code quality)'}"))
        elif want is None and have not in THINKING.values():
            res.append(("WARN", f"model body.reasoning_effort = {have!r} (set by you); left as it is"))
        else:
            res.append(("FIX", f"model body.reasoning_effort = {have!r} (want {want!r} for --thinking {thinking})"))
        sup = ((m.get("capabilities") or {}).get("reasoning") or {}).get("supported")
        res.append(("OK" if sup is True else "FIX", f"capabilities.reasoning.supported = {sup} (the thinking stream is shown as thinking)"))
    comp = cfg.get("compaction") or {}
    res.append(("OK" if comp.get("auto", True) else "FIX", f"compaction.auto = {comp.get('auto', True)}"))
    r = comp.get("reserved")
    reserved = max(reserved, min(output + 4096, window // 2))
    if isinstance(r, int) and output <= r <= max(window // 2, reserved):
        res.append(("OK", f"compaction.reserved = {r} (at least the output limit, at most half the window)"))
    else:
        res.append(("FIX", f"compaction.reserved = {r} (want at least {output}; recommended {reserved}) so compaction starts before the window is full"))
    want_model = f"{PROVIDER}/{model_id}"
    res.append(("OK" if cfg.get("model") == want_model else "FIX", f"model = {cfg.get('model')!r} (want {want_model!r})"))
    return res


def apply_fixes(cfg: dict, model_id: str, window: int, base: str, output: int, reserved: int, thinking: str = "default") -> dict:
    cfg = json.loads(json.dumps(cfg))
    old = current_provider(cfg) or {}
    key = (old.get("settings") or {}).get("apiKey") or "local"
    prev = (old.get("models") or {}).get(model_id) or {}
    output = effective_output((prev.get("limit") or {}).get("output"), output, window)
    reserved = max(reserved, min(output + 4096, window // 2))
    block = desired_block(model_id, window, base, output, key, old.get("name"), old.get("package"))
    for k, v in (old.get("settings") or {}).items():          # the user's other provider settings (timeouts, ...) stay
        block["settings"].setdefault(k, v)
    for k, v in old.items():
        if k not in block:
            block[k] = v
    for k, v in prev.items():                                 # and other keys of the same model (cost, variants, ...)
        if k not in ("limit", "capabilities", "name", "body"):
            block["models"][model_id][k] = v
    if isinstance(prev.get("capabilities"), dict):
        reasoning = {**(prev["capabilities"].get("reasoning") or {}), "supported": True}
        block["models"][model_id]["capabilities"] = {**prev["capabilities"], "reasoning": reasoning}
    body = dict(prev.get("body") or {})
    have, want = body.get("reasoning_effort"), THINKING[thinking]
    if want is not None:
        body["reasoning_effort"] = want
    elif have in THINKING.values():                             # back to the default: remove only what this tool sets (low / none)
        body.pop("reasoning_effort", None)
    if body:
        block["models"][model_id]["body"] = body
    else:
        block["models"][model_id].pop("body", None)
    cfg.setdefault("providers", {})[PROVIDER] = block
    comp = cfg.setdefault("compaction", {})
    comp.setdefault("auto", True)
    cur = comp.get("reserved")
    comp["reserved"] = cur if isinstance(cur, int) and output <= cur <= max(window // 2, reserved) else reserved
    cfg["model"] = f"{PROVIDER}/{model_id}"
    return cfg


def backup(path: Path) -> Path:
    b = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, b)
    return b


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except ValueError as e:
        raise SystemExit(f"{path} is not plain JSON ({e}); comments (jsonc) are not supported, fix it by hand.")


def run(path: Path, base: str, window: int | None, model_id: str | None, mode: str, output: int | None = None,
        reserved: int | None = None, quiet: bool = False, thinking: str = "default") -> int:
    srv = probe_server(base)
    model_id = model_id or srv["model_id"]
    window = window or srv["window"]
    if not model_id or not window:
        print(f"Cannot read the model id / window from {base} (server not running?). Pass --model-id and --window.", file=sys.stderr)
        return 2
    out, res = recommended_limits(window, output, reserved)
    cfg = load(path)
    if mode == "print":
        snippet = {"providers": {PROVIDER: desired_block(model_id, window, base, out, "<apiKey kept from your file, else 'local'>")},
                   "compaction": {"auto": True, "reserved": res}, "model": f"{PROVIDER}/{model_id}"}
        print(json.dumps(snippet, indent=2))
        return 0
    findings = audit(cfg, model_id, window, base, out, res, thinking)
    if not quiet:
        print(f"OpenCode config: {path}   (server: {model_id}, window {window})")
    for st, text in findings:
        print(f"  [{st:4}] {text}")
    todo = [f for f in findings if f[0] == "FIX"]
    if mode == "audit":
        print("Everything fits." if not todo else f"{len(todo)} setting(s) to fix: run with --update.")
        return 0 if not todo else 1
    if not todo:
        print("Nothing to change.")
        return 0
    new = apply_fixes(cfg, model_id, window, base, out, res, thinking)
    if path.exists():
        print(f"Backup: {backup(path)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    lim = new["providers"][PROVIDER]["models"][model_id]["limit"]
    print(f"Updated {path}: providers.{PROVIDER} (context {lim['context']}, output {lim['output']}), compaction.reserved {new['compaction']['reserved']}, "
          f"model {new['model']}.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--audit", action="store_true", help="compare only (default)")
    g.add_argument("--update", action="store_true", help="write the fixes (backup first)")
    g.add_argument("--print", dest="show", action="store_true", help="print the snippet only")
    ap.add_argument("--config", help="path to opencode.json (default: $OPENCODE_CONFIG or ~/.config/opencode/opencode.json)")
    ap.add_argument("--base", default="http://127.0.0.1:8080/v1")
    ap.add_argument("--window", type=int)
    ap.add_argument("--model-id")
    ap.add_argument("--output", type=int, help="output token limit (default 32,768, a third of a small window)")
    ap.add_argument("--reserved", type=int, help="compaction buffer (default output + 4096)")
    ap.add_argument("--thinking", choices=tuple(THINKING), default="default",
                    help="default: the model's own full thinking (for coding; removes a low/off setting this tool made); low or off: quicker replies, lower code quality")
    a = ap.parse_args()
    mode = "update" if a.update else "print" if a.show else "audit"
    return run(Path(a.config) if a.config else default_config_path(), a.base, a.window, a.model_id, mode, a.output, a.reserved, thinking=a.thinking)


if __name__ == "__main__":
    sys.exit(main())
