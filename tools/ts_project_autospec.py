"""Write an TS project test spec automatically, so the user supplies nothing but a snapshot.

Bugs: mutation testing. Small operator changes (== to !=, < to <=, + to -, && to ||, true to false) are applied one at
a time to non-test source files of the snapshot; a mutation is kept as a bug task only when the project's own tests then
fail (and not because of a syntax error). Files that the tests mention by name are tried first.
Recall questions: numeric constants (NAME = 123) that are declared exactly once in the snapshot.
Commands: the test script from package.json (npm), or pytest, or --test-command.
Rule tasks are optional and are not generated.
"""
from __future__ import annotations

import json
import random
import re
import shlex
import sys
import time
from pathlib import Path

import ts_project_tests as m

BUG_OPS = [
    (r"(?<![=!<>])===(?!=)", "!=="), (r"!==", "==="), (r"(?<![=!<>])==(?!=)", "!="), (r"(?<![=!<>])!=(?!=)", "=="),
    (r" <= ", " < "), (r" >= ", " > "), (r" < ", " <= "), (r" > ", " >= "), (r" && ", " || "), (r" \|\| ", " && "),
    (r" \+ ", " - "), (r" - ", " + "), (r"\btrue\b", "false"), (r"\bfalse\b", "true"), (r" and ", " or "), (r" or ", " and "),
]
CODE_EXT = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".sh")
SKIP_LINE = ("//", "*", "#", "/*", "import ", "from ", "require")
CONST_RE = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)?\s*([A-Z][A-Z0-9_]{2,})\s*=\s*(\d+)\s*;?\s*(?://.*|#.*)?$", re.M)
CRASH_RE = re.compile(r"SyntaxError|ParseError|Unexpected token|Cannot find module|IndentationError")


def is_test_file(rel: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|__tests__|spec)/|[._-](test|spec)\.|(^|/)test_", rel.lower()))


def detect_commands(snap: m.Snap, test_command: str | None, setup_command: str | None):
    names = set(snap.manifest["files"])
    setup = shlex.split(setup_command) if setup_command else None
    if test_command:
        return shlex.split(test_command), setup
    if "package.json" in names:
        pkg = json.loads(snap.read("package.json"))
        if "test" not in (pkg.get("scripts") or {}):
            raise SystemExit("package.json has no test script: pass --test-command")
        return ["npm", "test", "--silent"], setup or (["npm", "ci", "--ignore-scripts"] if "package-lock.json" in names
                                                       else ["npm", "install", "--ignore-scripts"])
    if any(n.endswith(("pytest.ini", "pyproject.toml")) for n in names):
        return [sys.executable, "-m", "pytest", "-q"], setup
    raise SystemExit("could not detect the test command: pass --test-command")


def related_template(snap: m.Snap):
    """vitest and jest can run just the tests that import a changed file: far faster than the whole suite."""
    if "package.json" not in snap.manifest["files"]:
        return None
    pkg = json.loads(snap.read("package.json"))
    deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    if "vitest" in deps:
        return ["npx", "vitest", "related", "--run", "{file}"]
    if "jest" in deps:
        return ["npx", "jest", "--findRelatedTests", "{file}"]
    return None


def mutation_candidates(snap: m.Snap, exclude: list[str], seed: str, max_file_tokens: int = 8000) -> list[dict]:
    texts = {r: snap.read(r) for r in snap.text_files(exclude) if r.endswith(CODE_EXT)}
    tests_blob = "\n".join(t for r, t in texts.items() if is_test_file(r))
    rng = random.Random(seed)
    out = []
    for rel, text in texts.items():
        if is_test_file(rel) or m.est_tokens(text) > max_file_tokens:      # the file must fit in the smallest prompt
            continue
        covered = bool(re.search(r"\b" + re.escape(Path(rel).stem) + r"\b", tests_blob))
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if not line.strip() or line.lstrip().startswith(SKIP_LINE):
                continue
            for pat, rep in BUG_OPS:
                hit = re.search(pat, line)
                if not hit:
                    continue
                new = line[:hit.start()] + re.sub(pat, rep, line[hit.start():hit.end()]) + line[hit.end():]
                find, replace = line, new
                if text.count(find) != 1 and i > 0:                 # not unique: add the previous line as context
                    find, replace = lines[i - 1] + "\n" + line, lines[i - 1] + "\n" + new
                if text.count(find) == 1:
                    out.append({"file": rel, "find": find, "replace": replace, "covered": covered, "r": rng.random()})
    out.sort(key=lambda c: (not c["covered"], c["r"]))
    return out


def run(a) -> int:
    snap = m.Snap(a.snapshot)
    snap.verify()
    test_cmd, setup_cmd = detect_commands(snap, a.test_command, a.setup_command)
    exclude = m.DEFAULT_EXCLUDE + ["docs/*", "*.png", "*.svg"]
    rules = [r for r in snap.text_files([]) if m.matches(r, ["AGENTS.md", "CLAUDE.md", ".agents/rules/*.md"])]
    spec = {"sizes": [int(x) for x in a.sizes.split(",")], "rules_files": ["AGENTS.md", "CLAUDE.md", ".agents/rules/*.md"],
            "padding_exclude": ["docs/*", "*.png", "*.svg"], "padding_include": ["src/*", "tests/*", "test/*", "scripts/*", "tools/*", "lib/*"],
            "setup_command": setup_cmd, "test_command": test_cmd, "target_test_template": related_template(snap),
            "failure_chars": 4000, "node_modules_from": a.node_modules_from, "bug_tasks": [], "rule_tasks": [], "recall_questions": [], "_generated_from": snap.name}
    work = m.prepare_work(snap, {"id": "_probe"}, spec, m.RUN_ROOT / f"_probe-{snap.name}")
    rc, out = m.sh(test_cmd, cwd=work, timeout=1800)
    if rc:
        raise SystemExit(f"the snapshot's tests do not pass here, so bugs cannot be probed:\n{out[-1500:]}")
    t0, tried = time.time(), 0
    for c in mutation_candidates(snap, exclude, snap.name, a.max_file_tokens):
        if len(spec["bug_tasks"]) >= a.bugs or tried >= a.max_tries or time.time() - t0 > a.budget_min * 60:
            break
        tried += 1
        target = work / c["file"]
        original = target.read_text(encoding="utf-8")
        target.write_text(original.replace(c["find"], c["replace"], 1), encoding="utf-8", newline="")
        probe = [x.replace("{file}", c["file"]) for x in spec["target_test_template"]] if spec["target_test_template"] else test_cmd
        rc, out = m.sh(probe, cwd=work, timeout=1800)
        m.reset_work(work)
        kept = rc != 0 and not CRASH_RE.search(out)
        print(f"  try {tried}: {c['file']}: {'tests fail, kept' if kept else 'tests pass or crash, dropped'}", flush=True)
        if kept:
            spec["bug_tasks"].append({
                "id": f"bug-{len(spec['bug_tasks']) + 1}",
                "description": "One or more tests are failing. Find the cause in the code above and fix it with a minimal change.",
                "mutation": {k: c[k] for k in ("file", "find", "replace")}, "files_hint": [c["file"]]})
    consts = [(rel, mm.group(1)) for rel in snap.text_files(exclude) if rel.endswith(CODE_EXT)
              and not is_test_file(rel) and m.est_tokens(snap.read(rel)) <= a.max_file_tokens
              for mm in CONST_RE.finditer(snap.read(rel))]
    names = [n for _, n in consts]
    uniq = sorted((r, n) for r, n in consts if names.count(n) == 1)
    random.Random(snap.name).shuffle(uniq)
    for k, (rel, name) in enumerate(uniq[:a.questions], 1):
        spec["recall_questions"].append({
            "id": f"q{k}", "question": f"In {rel}, what number is the constant {name} set to?",
            "answer_from": {"type": "regex_capture", "file": rel, "pattern": rf"\b{name}\s*=\s*(\d+)"}})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(spec, indent=1), encoding="utf-8")
    print(f"Spec written to {a.out}: {len(spec['bug_tasks'])} bug task(s) after {tried} tries, {len(spec['recall_questions'])} recall "
          f"question(s); {len(rules)} rules file(s) will head each prompt. Rule tasks are optional and not generated.")
    return 0 if spec["bug_tasks"] else 1
