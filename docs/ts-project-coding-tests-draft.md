# TS project-Style Long-Context Coding Tests (Draft)

**Status**: The tooling is written and passes its pipeline test on a synthetic repository (`tools/test_ts_project_tests.py`). It has **not** been run against TS project or a model: that needs the spec values listed under "Still needed".
**Purpose**: Compare local coding models (Strata Flash-Next, Qwen3.6-35B-A3B, Tiel Coder 35B-A3B) on the kind of work the TS project project needs, with a context of about 128K tokens. The existing tests in `configs/tests.yaml` are small single-function Python tasks. They do not exercise a large prompt, multi-file edits, or repository rules.

## Why these tests

Public suites (HumanEval+, LiveCodeBench, Aider polyglot) cover short tasks. The open question for TS project is different: does the model stay accurate when the prompt holds the agent rules plus a large part of the codebase, and does it still produce a usable patch?

## What I know about TS project, and what I do not

From the notes in this repository (the TS project's issue tracker, not kept here): TS project is a Node 20 app with CI on `ubuntu-latest`, an `AGENTS.md`, agent rules in `.agents/rules/`, `.claude/hooks/*.mjs` hooks, POSIX `sh` git hooks, and LF line endings. I have **not seen its source**, so every path, commit and test command below is a placeholder to fill in from the real repository.

## Self-sufficient by design (TS project is a live repository)

TS project changes, so nothing may depend on its live state after the start:

- **Frozen snapshot.** `python tools/ts_project_tests.py snapshot --repo <TS project> --commit <sha>` exports the files at one commit into `logs/ts-project-snapshots/<name>/` (gitignored) with a SHA-256 manifest. Line endings are forced to LF. Every later step reads only the snapshot and refuses to run if a file changed.
- **The bug is injected, not borrowed.** Test A applies a fixed one-line text replacement to the snapshot, so the bug cannot be "already fixed" by a later commit. The builder first checks that the untouched snapshot passes its own tests and that the injected bug makes them fail, and puts that failing output in the prompt.
- **Answers are computed from the snapshot** (regex capture, count, or literal), never typed by hand.
- **Rules come from the snapshot,** so they are the ones in force at the commit, not today's.
- **Tests run in a throwaway git working copy** of the snapshot with dependencies installed once and the tree reset after each check.
- **Nothing TS project-specific is committed.** The real spec lives in `configs/ts-project-tests.local.json` (gitignored); `configs/ts-project-tests.example.json` is the template.

## Commands

```text
python tools/ts_project_tests.py snapshot --repo <path to TS project> --commit <sha>
python tools/ts_project_tests.py build    --snapshot ts-project-<sha8>               # writes logs/ts-project-tests/<stamp>-<snapshot>/
python tools/ts_project_tests.py run      --run <that folder> --url http://127.0.0.1:8080 --repeats 3
python tools/ts_project_tests.py check    --run <that folder>
python tools/ts_project_tests.py report   --run <that folder>                 # report.md
```

`run` talks to any OpenAI-compatible server (Strata, llama-server, PolyStrata) and records the server's own prompt tokens and, when given, its prompt and decode speed. It is a separate script from `tools/run_tests.py`, so the existing runner is untouched.

## What you need to provide

Only the TS project checkout and a commit (default: the current one). The rest is generated:

```text
python tools/ts_project_tests.py snapshot --repo <path to TS project>
python tools/ts_project_tests.py auto     --snapshot ts-project-<sha8>      # writes configs/ts-project-tests.local.json
```

`auto` finds the bugs itself by **mutation testing**: it changes one operator at a time in the snapshot's source files (`==` to `!=`, `<` to `<=`, `+` to `-`, `&&` to `||`, `true` to `false`), runs the TS project's own tests, and keeps the changes that make them fail (not syntax errors or crashes). Files the tests mention are tried first. It also builds the recall questions from numeric constants declared once in the code. The test command comes from `package.json` (npm) or pytest; `--test-command` overrides it. Rule-following tests (B) are optional and are not generated, since they need someone's judgment about which rules matter.

## Shared design

- **Source material stays out of this repository** (see above).
- **Size ladder.** Each task is built at about 16K, 64K and 120K prompt tokens by adding unrelated files as padding, so the same task shows how accuracy changes with context. Padding is chosen deterministically (sorted paths, fixed seed).
- **Fixed settings** as in `docs/test-protocol.md`: fixed sampling, explicit reasoning setting, 16K output budget, three repeats because one run proves little.
- **Recorded per run:** pass or fail per check, prompt tokens, decode and prompt tok/s, time to first token, peak RAM.

## Test A: Fix a failing test across files

**Measures:** locating the right code in a large prompt and producing a correct, minimal patch.

- **Pick:** a subtle one-line bug in a source file that a real test covers; the bug is injected into the snapshot by text replacement. Avoid code that needs the app running.
- **Prompt contains:** `AGENTS.md` and the agent rules, the failing test output from the parent commit, and the relevant files plus padding up to the size target.
- **Asks for:** a unified diff only.
- **Checker:** check out the parent commit in a temporary copy, apply the diff with `git apply --check`, then run the project's test command. Pass requires the target test to pass and the rest of the suite to stay green. Partial credit: the patch applies (1), touches the right files (2), target test passes (3), nothing else breaks (4).
- **Needs from you:** the mutations and the test command.

## Test B: Follow the repository rules

**Measures:** whether the model respects `AGENTS.md` and the rules while making a small change, a common failure with long prompts.

- **Pick:** a task whose correct result obeys concrete, checkable rules from the repository, such as LF line endings, POSIX `sh` in git hooks, no PowerShell-only commands in rules that must work on Linux, or never deleting generated reports. Issue #307 (rewriting the shell rules to cover both bash and PowerShell) is a natural candidate.
- **Asks for:** a diff that implements the change.
- **Checker (automated):** line endings are LF only; no forbidden commands added; the rule file still contains the required sections; hooks still pass `sh -n`. Rubric items that cannot be automated are listed in the report, not scored.
- **Needs from you:** the 4–6 hard rules that matter most, in your own words.

## Test C: Recall inside the repository

**Measures:** retrieval accuracy at 32K, 64K and 120K, independent of code quality.

- **Pick:** 8 questions per size with exact answers computed from the checkout by script, for example "what does `<function>` return when `<condition>`", "which file defines `<constant>` and what is its value", "which hook blocks `<pattern>`".
- **Asks for:** a one-line answer per question as JSON.
- **Checker:** exact match after normalisation. Scripted, so no model judging.
- **Complements** Strata's `tools/needle_bench.py`, which uses synthetic needles.

## Open questions

- How large is TS project? If the whole repository is under 120K tokens, padding is unnecessary and test A can use the real repository.
- Does the TS project's test command run offline and finish in a few minutes? A slow suite makes three repeats per size impractical.
- Is it acceptable to run the TS project's tests on this machine while the model is loaded? Memory is tight at 128K.
