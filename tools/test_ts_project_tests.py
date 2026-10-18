"""Pipeline test for tools/ts_project_tests.py on a tiny synthetic repository (no model, no TS project)."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import ts_project_tests as m

GOOD_BUG = """```diff
diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
```"""
GOOD_RULE = """diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,5 @@
 def add(a, b):
     return a + b
+
+def sub(a, b):
+    return a - b
"""


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True, capture_output=True, stdin=subprocess.DEVNULL)


def make_repo(root: Path) -> Path:
    root.mkdir()
    (root / "AGENTS.md").write_text("Rules: LF line endings only.\n", encoding="utf-8", newline="\n")
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8", newline="\n")
    (root / "settings.py").write_text("LIMIT = 42\n", encoding="utf-8", newline="\n")
    (root / "test_calc.py").write_text("import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
                                      "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n\nif __name__ == '__main__':\n    unittest.main()\n",
                                      encoding="utf-8", newline="\n")
    for i in range(30):
        (root / f"notes{i}.txt").write_text(("filler line %d\n" % i) * 40, encoding="utf-8", newline="\n")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "init")
    return root


def spec() -> dict:
    return {"sizes": [1500, 4000], "rules_files": ["AGENTS.md"], "test_command": [sys.executable, "-m", "unittest", "-q"],
            "bug_tasks": [{"id": "bug-1", "description": "A test fails.", "mutation": {"file": "calc.py", "find": "return a + b", "replace": "return a - b"},
                           "files_hint": ["calc.py"]}],
            "rule_tasks": [{"id": "rule-1", "instruction": "Add sub(a, b).", "files_hint": ["calc.py"],
                            "checks": [{"type": "no_crlf", "files": "*"}, {"type": "require_regex", "file": "calc.py", "pattern": "def sub"},
                                       {"type": "max_changed_files", "n": 1}]}],
            "recall_questions": [{"id": "q1", "question": "What is LIMIT?", "answer_from": {"type": "regex_capture", "file": "settings.py", "pattern": r"LIMIT = (\d+)"}}]}


def test_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "SNAP_ROOT", tmp_path / "snaps")
    monkeypatch.setattr(m, "RUN_ROOT", tmp_path / "runs")
    repo = make_repo(tmp_path / "repo")
    assert m.main(["snapshot", "--repo", str(repo), "--name", "s"]) == 0
    # the live repo changes afterwards: the snapshot must not care
    (repo / "calc.py").write_text("def add(a, b):\n    return 0\n", encoding="utf-8")
    sp = tmp_path / "spec.json"
    sp.write_text(json.dumps(spec()), encoding="utf-8")
    run = tmp_path / "run"
    assert m.main(["build", "--snapshot", "s", "--spec", str(sp), "--out", str(run)]) == 0
    key = json.loads((run / "key.json").read_text(encoding="utf-8"))
    assert set(key["items"]) == {"bug-1@1500", "bug-1@4000", "rule-1@1500", "rule-1@4000", "recall@1500", "recall@4000"}
    big = (run / "prompts" / "bug-1-4000.txt").read_text(encoding="utf-8")
    assert "return a - b" in big and "FAIL" in big          # the injected bug and the failing output are in the prompt
    (run / "responses").mkdir()
    replies = {"bug-1": GOOD_BUG, "rule-1": GOOD_RULE, "recall": '{"q1": "42"}'}
    for item in key["items"]:
        data = {"choices": [{"message": {"content": replies[item.split("@")[0]]}}], "usage": {"prompt_tokens": 1}, "_wall_s": 1.0}
        (run / "responses" / f"{item.replace('@', '-')}-r1.json").write_text(json.dumps(data), encoding="utf-8")
    bad = {"choices": [{"message": {"content": "I cannot do that"}}]}
    (run / "responses" / "bug-1-1500-r2.json").write_text(json.dumps(bad), encoding="utf-8")
    assert m.main(["check", "--run", str(run)]) == 0
    res = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (run / "results").glob("*.json")}
    assert res["bug-1-1500-r1"]["score"] == res["bug-1-1500-r1"]["max"] == 4
    assert res["rule-1-4000-r1"]["score"] == res["rule-1-4000-r1"]["max"]
    assert res["recall-1500-r1"]["score"] == 1
    assert res["bug-1-1500-r2"]["score"] == 0
    assert m.main(["report", "--run", str(run)]) == 0
    assert "bug-1@1500" in (run / "report.md").read_text(encoding="utf-8")


def test_auto_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "SNAP_ROOT", tmp_path / "snaps")
    monkeypatch.setattr(m, "RUN_ROOT", tmp_path / "runs")
    repo = make_repo(tmp_path / "repo")
    assert m.main(["snapshot", "--repo", str(repo), "--name", "s"]) == 0
    out = tmp_path / "auto.json"
    cmd = f'"{sys.executable}" -m unittest -q'
    assert m.main(["auto", "--snapshot", "s", "--out", str(out), "--test-command", cmd.replace("\\", "/"), "--bugs", "1", "--sizes", "1500"]) == 0
    spec = json.loads(out.read_text(encoding="utf-8"))
    assert len(spec["bug_tasks"]) == 1 and spec["bug_tasks"][0]["mutation"]["file"] == "calc.py"
    assert spec["recall_questions"][0]["answer_from"]["pattern"].endswith(r"\s*=\s*(\d+)")
    run = tmp_path / "run"
    assert m.main(["build", "--snapshot", "s", "--spec", str(out), "--out", str(run)]) == 0
    assert set(json.loads((run / "key.json").read_text(encoding="utf-8"))["items"]) == {"bug-1@1500", "recall@1500"}
