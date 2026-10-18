#!/usr/bin/env python3
"""Self-contained long-context coding tests built from a frozen snapshot of the TS project repository.

TS project is a live repository: bugs get fixed and files change. These tests therefore never read the live repo
after the snapshot is taken. Everything (prompt text, injected bug, expected answers, test run) comes from the
snapshot, so a result stays comparable months later.

    python tools/ts_project_tests.py snapshot --repo PATH_TO_TS_PROJECT [--commit SHA] [--name NAME]
    python tools/ts_project_tests.py auto     --snapshot NAME            (writes configs/ts-project-tests.local.json by itself)
    python tools/ts_project_tests.py build    --snapshot NAME [--spec configs/ts-project-tests.local.json]
    python tools/ts_project_tests.py run      --run RUN_DIR --url http://127.0.0.1:8080 [--repeats 3] [--only bug-1]
    python tools/ts_project_tests.py check    --run RUN_DIR
    python tools/ts_project_tests.py report   --run RUN_DIR

Tests (see docs/ts-project-coding-tests-draft.md):
  bug     a bug injected into the snapshot by a fixed text replacement (so it can never be "already fixed");
          the model gets the rules, the failing test output and the code, and returns a unified diff.
  rule    a change that must follow repository rules; scripted checks decide.
  recall  questions whose exact answers are computed from the snapshot files.
Each runs at the context sizes of the spec (about 16K / 64K / 120K tokens) by adding padding files.
Snapshots and runs live in logs/ (gitignored): TS project source is never committed to this repository.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
import random
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAP_ROOT = REPO / "logs" / "ts-project-snapshots"
RUN_ROOT = REPO / "logs" / "ts-project-tests"
CHARS_PER_TOKEN = 3.2            # measured on Strata's own tokenizer for mixed code: 3.2-3.3; the report shows the real prompt token count
DEFAULT_EXCLUDE = ["node_modules/*", "*.lock", "package-lock.json", "*.min.js", "*.map", ".git/*", "dist/*", "build/*", "coverage/*"]


# ------------------------------------------------------------------------------------------------ helpers
def sh(cmd, cwd=None, timeout=600, shell=False):
    if isinstance(cmd, list) and cmd and not shell:
        cmd = [shutil.which(cmd[0]) or cmd[0], *cmd[1:]]     # npm is npm.cmd on Windows
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace", shell=shell, stdin=subprocess.DEVNULL)
        return r.returncode, (r.stdout + r.stderr)
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def est_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def matches(rel: str, patterns) -> bool:
    return any(fnmatch.fnmatch(rel, p) for p in patterns)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def block(rel: str, text: str) -> str:
    return f"=== FILE: {rel} ===\n{text.rstrip(chr(10))}\n=== END FILE ===\n"


# ----------------------------------------------------------------------------------------------- snapshot
def cmd_snapshot(a) -> int:
    commit = a.commit or "HEAD"
    rc, full = sh(["git", "-C", a.repo, "rev-parse", commit])
    if rc:
        print(full, file=sys.stderr)
        return 1
    full = full.strip()
    name = a.name or f"ts-project-{full[:8]}"
    dest = SNAP_ROOT / name
    part = SNAP_ROOT / (name + ".partial")
    if part.exists():
        shutil.rmtree(part)                       # an interrupted earlier attempt
    if dest.exists():
        print(f"Snapshot {name} exists; snapshots are never overwritten.", file=sys.stderr)
        return 1
    files = part / "files"
    files.mkdir(parents=True)
    p = subprocess.Popen(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "-C", a.repo, "archive", "--format=tar", full], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    with tarfile.open(fileobj=p.stdout, mode="r|") as tf:
        tf.extractall(files, filter="data")
    p.stdout.read()                                   # drain the tar trailer, or git archive blocks on a full pipe
    p.wait()
    entries = {}
    for f in sorted(files.rglob("*")):
        if f.is_file():
            data = f.read_bytes()
            try:
                data.decode("utf-8")
                text = True
            except UnicodeDecodeError:
                text = False
            entries[f.relative_to(files).as_posix()] = {"sha256": sha256(data), "bytes": len(data), "text": text}
    manifest = {"commit": full, "created": datetime.date.today().isoformat(), "files": entries}
    (part / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    part.rename(dest)                             # a snapshot exists only once it is complete
    tot = sum(e["bytes"] for e in entries.values() if e["text"])
    print(f"Snapshot {name}: {len(entries)} files, about {int(tot / CHARS_PER_TOKEN):,} tokens of text, commit {full[:12]}")
    return 0


class Snap:
    def __init__(self, name: str):
        self.dir = SNAP_ROOT / name
        self.files = self.dir / "files"
        self.manifest = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
        self.name = name

    def verify(self) -> None:
        for rel, e in self.manifest["files"].items():
            if sha256((self.files / rel).read_bytes()) != e["sha256"]:
                raise SystemExit(f"Snapshot {self.name} was modified: {rel}")

    def text_files(self, exclude) -> list[str]:
        return [r for r, e in sorted(self.manifest["files"].items()) if e["text"] and not matches(r, exclude)]

    def read(self, rel: str) -> str:
        return (self.files / rel).read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------ prompt building
def assemble(snap: Snap, spec: dict, must: dict[str, str], size: int, seed: str) -> tuple[str, list[str]]:
    """Rules first, then the must-have files and padding files in a seeded order, up to `size` tokens."""
    exclude = DEFAULT_EXCLUDE + spec.get("padding_exclude", [])
    rules = [r for r in snap.text_files([]) if matches(r, spec.get("rules_files", []))]
    head = "".join(block(r, snap.read(r)) for r in rules)
    used = est_tokens(head) + sum(est_tokens(t) for t in must.values())
    if used > size:
        raise SystemExit(f"{seed}: rules and required files need about {used:,} tokens, more than the size {size:,}")
    rng = random.Random(seed)
    pool = [r for r in snap.text_files(exclude) if r not in rules and r not in must
            and (not spec.get("padding_include") or matches(r, spec["padding_include"]))]
    rng.shuffle(pool)
    chosen = dict(must)
    for r in pool:
        t = snap.read(r)
        if used + est_tokens(t) > size:
            continue
        chosen[r] = t
        used += est_tokens(t)
    order = sorted(chosen, key=lambda r: (rng.random(), r))
    return head + "".join(block(r, chosen[r]) for r in order), [*rules, *order]


def apply_mutation(snap: Snap, m: dict) -> tuple[str, str]:
    orig = snap.read(m["file"])
    if orig.count(m["find"]) != 1:
        raise SystemExit(f"mutation in {m['file']}: the text to replace must occur exactly once (found {orig.count(m['find'])})")
    return orig, orig.replace(m["find"], m["replace"])


def prepare_work(snap: Snap, task: dict, spec: dict, run: Path) -> Path:
    """A git working copy of the snapshot (with the bug injected for bug tasks), dependencies installed once."""
    work = run / "work" / task["id"]
    if work.exists():
        return work
    shutil.copytree(snap.files, work)
    if task.get("mutation"):
        _, mutated = apply_mutation(snap, task["mutation"])
        (work / task["mutation"]["file"]).write_text(mutated, encoding="utf-8", newline="")
    (work / ".gitignore").write_text("node_modules/\n.venv/\n__pycache__/\n", encoding="utf-8")
    for c in (["git", "init", "-q"], ["git", "config", "core.autocrlf", "false"], ["git", "config", "core.eol", "lf"], ["git", "add", "-A"], ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"]):
        sh(c, cwd=work)
    if spec.get("node_modules_from"):                # reuse an existing install (no download): a junction/symlink to it
        link, target = work / "node_modules", Path(spec["node_modules_from"])
        if sys.platform == "win32":
            sh(["cmd", "/c", "mklink", "/J", str(link), str(target)])
        else:
            link.symlink_to(target, target_is_directory=True)
    elif spec.get("setup_command"):
        rc, out = sh(spec["setup_command"], cwd=work, timeout=1800)
        if rc:
            raise SystemExit(f"setup_command failed:\n{out[-1500:]}")
    return work


def reset_work(work: Path) -> None:
    sh(["git", "reset", "-q", "--hard"], cwd=work)
    sh(["git", "clean", "-fdq"], cwd=work)


def resolve_answer(snap: Snap, a: dict) -> str:
    t = a["type"]
    if t == "literal":
        return str(a["value"])
    if t == "regex_capture":
        m = re.search(a["pattern"], snap.read(a["file"]), re.M)
        if not m:
            raise SystemExit(f"answer pattern {a['pattern']!r} not found in {a['file']}")
        return m.group(1)
    if t == "count_matches":
        n = sum(len(re.findall(a["pattern"], snap.read(r), re.M)) for r in snap.text_files([]) if fnmatch.fnmatch(r, a["files"]))
        return str(n)
    raise SystemExit(f"unknown answer type {t}")


PREAMBLE = ("You are a careful software engineer. Below is a snapshot of a repository: its agent rules first, then source files, "
            "each between '=== FILE: path ===' and '=== END FILE ===' markers. Follow the rules in the snapshot.\n\n")


def cmd_build(a) -> int:
    snap = Snap(a.snapshot)
    snap.verify()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    run = Path(a.out) if a.out else RUN_ROOT / f"{datetime.datetime.now():%Y%m%d-%H%M}-{snap.name}"
    (run / "prompts").mkdir(parents=True, exist_ok=True)
    key: dict = {"snapshot": snap.name, "commit": snap.manifest["commit"], "spec": spec, "items": {}}
    for task in spec.get("bug_tasks", []):
        if not a.no_verify and "clean_ok" not in key:
            rc_clean, out_clean = sh(spec["test_command"], cwd=prepare_work(snap, {"id": "_clean"}, spec, run), timeout=1800)
            if rc_clean:
                raise SystemExit(f"the untouched snapshot fails its own tests, so no bug task is meaningful:\n{out_clean[-1500:]}")
            key["clean_ok"] = True
        work = prepare_work(snap, task, spec, run)
        target_cmd = [x.replace("{file}", task["mutation"]["file"]) for x in spec["target_test_template"]] if spec.get("target_test_template") else None
        rc0, fail_out = sh(target_cmd or spec["test_command"], cwd=work, timeout=1800)
        if rc0 == 0 and not a.no_verify:
            raise SystemExit(f"{task['id']}: the injected bug does not make the tests fail; fix the mutation")
        fail_text = fail_out[-spec.get("failure_chars", 4000):]
        for size in spec["sizes"]:
            must = {r: (apply_mutation(snap, task["mutation"])[1] if r == task["mutation"]["file"] else snap.read(r))
                    for r in set(task.get("files_hint", [])) | {task["mutation"]["file"]}}
            ctx, order = assemble(snap, spec, must, size, f"{task['id']}-{size}")
            prompt = (PREAMBLE + ctx + "\n## Failing test output\n```\n" + fail_text + "\n```\n\n## Task\n" + task["description"] +
                      "\nReply with a unified diff (git format, paths relative to the repository root) that fixes the bug and nothing else. "
                      "Output only the diff.\n")
            _write_item(run, key, f"{task['id']}@{size}", "bug", prompt, {"task": task["id"], "files_hint": task.get("files_hint", [task["mutation"]["file"]]), "target_cmd": target_cmd})
    for task in spec.get("rule_tasks", []):
        prepare_work(snap, task, spec, run)
        for size in spec["sizes"]:
            ctx, _ = assemble(snap, spec, {r: snap.read(r) for r in task.get("files_hint", [])}, size, f"{task['id']}-{size}")
            prompt = (PREAMBLE + ctx + "\n## Task\n" + task["instruction"] +
                      "\nReply with a unified diff (git format, paths relative to the repository root). Output only the diff.\n")
            _write_item(run, key, f"{task['id']}@{size}", "rule", prompt, {"task": task["id"], "checks": task["checks"]})
    qs = spec.get("recall_questions", [])
    if qs:
        answers = {q["id"]: resolve_answer(snap, q["answer_from"]) for q in qs}
        for size in spec["sizes"]:
            ctx, _ = assemble(snap, spec, {q["answer_from"]["file"]: snap.read(q["answer_from"]["file"]) for q in qs if "file" in q["answer_from"]},
                              size, f"recall-{size}")
            listing = "\n".join(f"{q['id']}: {q['question']}" for q in qs)
            prompt = (PREAMBLE + ctx + "\n## Questions\n" + listing + "\n\nAnswer from the files above. Reply with one JSON object mapping each question id "
                      "to a short exact answer (a value, a name or a number) and nothing else.\n")
            _write_item(run, key, f"recall@{size}", "recall", prompt, {"answers": answers})
    (run / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"Built {len(key['items'])} prompts in {run}")
    return 0


def _write_item(run: Path, key: dict, item_id: str, kind: str, prompt: str, extra: dict) -> None:
    (run / "prompts" / (item_id.replace("@", "-") + ".txt")).write_text(prompt, encoding="utf-8")
    key["items"][item_id] = {"kind": kind, "est_prompt_tokens": est_tokens(prompt), **extra}


# --------------------------------------------------------------------------------------------------- run
def post(url: str, model: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    data["_wall_s"] = round(time.time() - t0, 2)
    return data


def cmd_run(a) -> int:
    run = Path(a.run)
    key = json.loads((run / "key.json").read_text(encoding="utf-8"))
    (run / "responses").mkdir(exist_ok=True)
    for item_id in key["items"]:
        if a.only and not any(o in item_id for o in a.only.split(",")):
            continue
        for rep in range(1, a.repeats + 1):
            out = run / "responses" / f"{item_id.replace('@', '-')}-r{rep}.json"
            if out.exists():
                continue
            prompt = (run / "prompts" / (item_id.replace("@", "-") + ".txt")).read_text(encoding="utf-8")
            print(f"{item_id} run {rep} ...", flush=True)
            data = {}
            for attempt in range(3):                   # a 503 means the engine exited; Strata restarts it, so wait and ask again
                try:
                    data = post(a.url, a.model, prompt, a.max_tokens, a.timeout)
                    break
                except Exception as e:                 # noqa: BLE001  record the failure, keep going
                    data = {"error": str(e), "attempts": attempt + 1}
                    if "503" not in str(e) or attempt == 2:
                        break
                    print(f"    HTTP 503 (engine restart): waiting 240 s, attempt {attempt + 2} of 3", flush=True)
                    time.sleep(240)
            if attempt and "error" not in data:
                data["retried_after_engine_restart"] = attempt
            out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return 0


# ------------------------------------------------------------------------------------------------- check
def reply_text(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def extract_diff(text: str) -> str:
    m = re.search(r"```(?:diff|patch)?\n(.*?)```", text, re.S)
    body = m.group(1) if m and ("--- " in m.group(1) or "diff --git" in m.group(1)) else text
    i = min([x for x in (body.find("diff --git"), body.find("--- a/"), body.find("--- ")) if x >= 0], default=-1)
    return (body[i:] if i >= 0 else "").rstrip() + "\n" if i >= 0 else ""


def diff_files(diff: str) -> list[str]:
    return sorted({m.group(1) for m in re.finditer(r"^\+\+\+ b/(\S+)", diff, re.M)})


def run_checks(work: Path, checks: list[dict], changed: list[str]) -> dict[str, bool | None]:
    res: dict[str, bool | None] = {}
    for i, c in enumerate(checks):
        t, name = c["type"], f"{i + 1}:{c['type']}"
        files = [f for f in work.rglob("*") if f.is_file() and ".git" not in f.parts and "node_modules" not in f.parts]
        rel = lambda f: f.relative_to(work).as_posix()          # noqa: E731
        sel = [f for f in files if fnmatch.fnmatch(rel(f), c.get("files", "*"))]
        if t == "no_crlf":
            res[name] = not any(b"\r\n" in f.read_bytes() for f in sel if rel(f) in changed or c.get("all"))
        elif t == "forbid_regex":
            res[name] = not any(re.search(c["pattern"], f.read_text(encoding="utf-8", errors="replace"), re.M) for f in sel)
        elif t == "require_regex":
            f = work / c["file"]
            res[name] = f.exists() and bool(re.search(c["pattern"], f.read_text(encoding="utf-8", errors="replace"), re.M))
        elif t == "max_changed_files":
            res[name] = len(changed) <= c["n"]
        elif t == "sh_syntax":
            if not shutil.which("sh"):
                res[name] = None
            else:
                res[name] = all(sh(["sh", "-n", str(f)])[0] == 0 for f in sel)
        else:
            res[name] = None
    return res


def _norm_ws(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def edit_match_apply(diff: str, work: Path) -> bool:
    """Last resort when the context lines of a diff do not match: apply only its changed lines. Each run of removed lines is looked up in the
    file (compared without whitespace differences) and has to occur exactly once; it is replaced by the added lines, keeping the file's
    indentation. A pure addition cannot be located and fails. Returns True if every change was applied."""
    cur, files, applied = None, {}, True
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            parts = raw.split()
            cur = parts[-1][2:] if parts[-1].startswith("b/") else parts[-1]
            files.setdefault(cur, [])
        elif raw.startswith("+++ "):
            cur = raw[4:].strip()
            cur = cur[2:] if cur.startswith("b/") else cur
            files.setdefault(cur, [])
        elif cur and raw[:1] in "-+ " and not raw.startswith(("--- ", "+++ ")):
            files[cur].append(raw)
        elif cur and raw.startswith("@@"):
            files[cur].append("@@")
    if not files:
        return False
    for rel, lines in files.items():
        f = work / rel
        if not f.is_file():
            return False
        text = f.read_text(encoding="utf-8")
        eol = "\r\n" if "\r\n" in text else "\n"
        src = text.split(eol)
        runs, i = [], 0
        while i < len(lines):
            if lines[i][:1] == "-" or lines[i][:1] == "+":
                before = []
                k = i - 1
                while k >= 0 and lines[k][:1] == " " and len(before) < 3:
                    before.insert(0, lines[k][1:]); k -= 1
                rem, add = [], []
                while i < len(lines) and lines[i][:1] == "-":
                    rem.append(lines[i][1:]); i += 1
                while i < len(lines) and lines[i][:1] == "+":
                    add.append(lines[i][1:]); i += 1
                runs.append((rem, add, before))
            else:
                i += 1
        if not runs:
            return False
        for rem, add, before in runs:
            if not rem:                                     # a pure addition: put it after the context lines in front of it
                for n in range(len(before), 0, -1):
                    nb = [_norm_ws(x) for x in before[-n:]]
                    hits = [k for k in range(len(src) - n + 1) if [_norm_ws(x) for x in src[k:k + n]] == nb]
                    if len(hits) == 1:
                        k = hits[0] + n
                        ind = len(src[k - 1]) - len(src[k - 1].lstrip())
                        d_ind = len(before[-1]) - len(before[-1].lstrip())
                        src[k:k] = [" " * max(0, len(x) - len(x.lstrip()) - d_ind + ind) + x.lstrip() if x.strip() else "" for x in add]
                        break
                else:
                    applied = False
                continue
            norm_rem = [_norm_ws(x) for x in rem]
            hits = [k for k in range(len(src) - len(rem) + 1) if [_norm_ws(x) for x in src[k:k + len(rem)]] == norm_rem]
            if len(hits) != 1:
                applied = False
                continue
            k = hits[0]
            file_indent = len(src[k]) - len(src[k].lstrip())
            diff_indent = len(rem[0]) - len(rem[0].lstrip())
            new = []
            for x in add:
                ind = max(0, len(x) - len(x.lstrip()) - diff_indent + file_indent) if x.strip() else 0
                new.append(" " * ind + x.lstrip())
            src[k:k + len(rem)] = new
        f.write_text(eol.join(src), encoding="utf-8", newline="")
    return applied


def apply_diff(p: Path, diff: str, work: Path) -> tuple[str | None, str]:
    """Try a strict git apply, then one that ignores whitespace differences, then the changed lines alone. -> (mode or None, error text)."""
    rc, out = sh(["git", "apply", "--recount", "--whitespace=nowarn", str(p)], cwd=work)
    if rc == 0:
        return "strict", ""
    rc2, _ = sh(["git", "apply", "--recount", "--ignore-whitespace", "--whitespace=nowarn", str(p)], cwd=work)
    if rc2 == 0:
        return "ignore-whitespace", out[-500:]
    reset_work(work)
    if edit_match_apply(diff, work):
        return "edit-match", out[-500:]
    reset_work(work)
    return None, out[-500:]


def check_diff_item(item: dict, key: dict, work: Path, reply: str) -> dict:
    spec = key["spec"]
    diff = extract_diff(reply)
    reset_work(work)
    r: dict = {"diff_found": bool(diff)}
    if not diff:
        r.update(score=0, max=4 if item["kind"] == "bug" else len(item["checks"]) + 1)
        return r
    (work.parent / "model.patch").write_text(diff, encoding="utf-8", newline="")
    p = work.parent / "model.patch"
    mode, out = apply_diff(p, diff, work)
    r["applies"] = mode is not None
    r["apply_mode"] = mode
    changed = diff_files(diff)
    r["changed_files"] = changed
    if mode is None:
        r["apply_error"] = out
        r.update(score=0, max=4 if item["kind"] == "bug" else len(item["checks"]) + 1)
        reset_work(work)
        return r
    if item["kind"] == "bug":
        r["touches_expected_files"] = bool(set(changed) & set(item["files_hint"]))
        tgt = item.get("target_cmd") or spec.get("target_test_command") or spec["test_command"]
        r["target_test_passes"] = sh(tgt, cwd=work, timeout=1800)[0] == 0
        r["full_suite_passes"] = sh(spec["test_command"], cwd=work, timeout=1800)[0] == 0
        # a different fix that makes the whole suite pass (which includes the failing test) counts as fully solved, wherever it is
        r["works"] = bool(r["full_suite_passes"])
        r["score"] = 4 if r["works"] else 1 + sum(bool(r[k]) for k in ("touches_expected_files", "target_test_passes", "full_suite_passes"))
        r["max"] = 4
    else:
        r["checks"] = run_checks(work, item["checks"], changed)
        r["score"] = 1 + sum(v is True for v in r["checks"].values())
        r["max"] = 1 + len(item["checks"])
    reset_work(work)
    return r


def norm(s) -> str:
    return re.sub(r"[\s`'\"]+", "", str(s)).lower()


def check_recall(item: dict, reply: str) -> dict:
    m = re.search(r"\{.*\}", reply, re.S)
    try:
        got = json.loads(m.group(0)) if m else {}
    except ValueError:
        got = {}
    per = {q: norm(got.get(q, "")) == norm(a) for q, a in item["answers"].items()}
    return {"answers": per, "score": sum(per.values()), "max": len(per)}


def cmd_check(a) -> int:
    run = Path(a.run)
    key = json.loads((run / "key.json").read_text(encoding="utf-8"))
    snap = Snap(key["snapshot"])
    (run / "results").mkdir(exist_ok=True)
    for f in sorted((run / "responses").glob("*.json")):
        item_id = next((i for i in key["items"] if f.name.startswith(i.replace("@", "-") + "-r")), None)
        out = run / "results" / f.name
        if not item_id or out.exists():
            continue
        item, data = key["items"][item_id], json.loads(f.read_text(encoding="utf-8"))
        reply = reply_text(data)
        if item["kind"] == "recall":
            res = check_recall(item, reply)
        else:
            task = next(t for t in key["spec"]["bug_tasks" if item["kind"] == "bug" else "rule_tasks"] if t["id"] == item["task"])
            res = check_diff_item(item, key, prepare_work(snap, task, key["spec"], run), reply)
        usage, tim = data.get("usage") or {}, data.get("timings") or {}
        res.update(prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"), wall_s=data.get("_wall_s"),
                   prompt_tps=tim.get("prompt_per_second"), decode_tps=tim.get("predicted_per_second"), error=data.get("error"))
        out.write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(f"{f.name}: {res['score']}/{res['max']}")
    return 0


def cmd_regrade(a) -> int:
    """Grade again, with the tolerant apply and the 'a fix that works counts' rule, every answer that scored below the maximum.
    The earlier result is kept in results-strict/ (a strict `git apply`, 4 only if the fix touched the expected file)."""
    run = Path(a.run)
    key = json.loads((run / "key.json").read_text(encoding="utf-8"))
    snap = Snap(key["snapshot"])
    old_dir = run / "results-strict"
    old_dir.mkdir(exist_ok=True)
    for f in sorted((run / "responses").glob("*.json")):
        item_id = next((i for i in key["items"] if f.name.startswith(i.replace("@", "-") + "-r")), None)
        out = run / "results" / f.name
        if not item_id or not out.exists() or key["items"][item_id]["kind"] != "bug":
            continue
        old = json.loads(out.read_text(encoding="utf-8"))
        if old["score"] >= old["max"] or old.get("apply_mode") or (old.get("applies") and old.get("touches_expected_files")):
            continue
        item, data = key["items"][item_id], json.loads(f.read_text(encoding="utf-8"))
        task = next(t for t in key["spec"]["bug_tasks"] if t["id"] == item["task"])
        res = check_diff_item(item, key, prepare_work(snap, task, key["spec"], run), reply_text(data))
        for k in ("prompt_tokens", "completion_tokens", "wall_s", "prompt_tps", "decode_tps", "error"):
            res[k] = old.get(k)
        res["strict_score"] = old["score"]
        (old_dir / f.name).write_text(json.dumps(old, indent=1), encoding="utf-8")
        out.write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(f"{run.name}/{f.name}: {old['score']} -> {res['score']}/{res['max']} ({res.get('apply_mode')})", flush=True)
    return 0


# ------------------------------------------------------------------------------------------------ report
def cmd_report(a) -> int:
    run = Path(a.run)
    key = json.loads((run / "key.json").read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = {}
    for f in sorted((run / "results").glob("*.json")):
        item_id = next((i for i in key["items"] if f.name.startswith(i.replace("@", "-") + "-r")), None)
        if item_id:
            rows.setdefault(item_id, []).append(json.loads(f.read_text(encoding="utf-8")))

    def med(vals):
        v = [x for x in vals if isinstance(x, (int, float))]
        return f"{statistics.median(v):.1f}" if v else "n/a"
    L = [f"# TS project long-context tests: snapshot {key['snapshot']} (commit `{key['commit'][:12]}`)", "",
         "| Test | Prompt tokens (server) | Runs | Score (mean of max) | Prompt tok/s | Decode tok/s | Wall s |", "| --- | ---: | ---: | --- | ---: | ---: | ---: |"]
    for item_id, rs in rows.items():
        mx = rs[0]["max"]
        L.append(f"| {item_id} | {med([r['prompt_tokens'] for r in rs])} | {len(rs)} | {statistics.mean(r['score'] for r in rs):.2f} / {mx} | "
                 f"{med([r['prompt_tps'] for r in rs])} | {med([r['decode_tps'] for r in rs])} | {med([r['wall_s'] for r in rs])} |")
    (run / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--repo", required=True)
    s.add_argument("--commit")
    s.add_argument("--name")
    u = sub.add_parser("auto", help="write the spec by itself: bugs by mutation testing, questions from constants")
    u.add_argument("--snapshot", required=True)
    u.add_argument("--out", default=str(REPO / "configs" / "ts-project-tests.local.json"))
    u.add_argument("--bugs", type=int, default=3)
    u.add_argument("--questions", type=int, default=8)
    u.add_argument("--sizes", default="16000,64000,120000")
    u.add_argument("--max-tries", type=int, default=40)
    u.add_argument("--max-file-tokens", type=int, default=8000, help="skip bug candidates in files larger than this (they must fit the smallest prompt)")
    u.add_argument("--budget-min", type=int, default=45, help="stop probing for bugs after this many minutes")
    u.add_argument("--test-command", help="override the detected test command, e.g. \"npm test --silent\"")
    u.add_argument("--setup-command", help="override the install command")
    u.add_argument("--node-modules-from", help="reuse this existing node_modules folder instead of installing (no download)")
    b = sub.add_parser("build")
    b.add_argument("--snapshot", required=True)
    b.add_argument("--spec", default=str(REPO / "configs" / "ts-project-tests.local.json"))
    b.add_argument("--out")
    b.add_argument("--no-verify", action="store_true", help="do not require the injected bug to fail the tests")
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--url", default="http://127.0.0.1:8080")
    r.add_argument("--model", default="local")
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--only", help="comma-separated substrings of test ids (e.g. bug-1@16000)")
    r.add_argument("--max-tokens", type=int, default=16384)
    r.add_argument("--timeout", type=int, default=7200)
    for n in ("check", "report", "regrade"):
        c = sub.add_parser(n)
        c.add_argument("--run", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "auto":
        import ts_project_autospec
        return ts_project_autospec.run(a)
    return {"snapshot": cmd_snapshot, "build": cmd_build, "run": cmd_run, "check": cmd_check, "regrade": cmd_regrade, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
