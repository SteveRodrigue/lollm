# Creating Tests

This guide explains how to add a test to the project without changing the runner. The test definition belongs in `configs/tests.yaml`; implementation-specific validation belongs in a checker under `tools/`.

## Test Parts

A Python test normally has these parts:

1. A prompt under `test-prompts/`.
2. A registry entry under `configs/tests.yaml`.
3. An extraction function name, if the generated source must contain a particular function.
4. An independent checker under `tools/`.
5. Optional model-authored tests, if the prompt asks for them and the runner should execute them.

The runner stores raw output, extracted source, compiler output, checker output, and ledger rows under `logs/`. Reports are regenerated under `reports/latest/`.

## 1. Write the Prompt

Keep the prompt explicit about the public function, inputs, outputs, edge cases, dependencies, and output format. For a Python test, ask for valid Python source so the shared extractor can parse it.

Example:

```text
Output only valid Python source code.
Implement parse_and_average(values: list[str]) -> float.
Ignore empty and invalid values, return 0.0 when no values are valid, and round the average to two decimals.
Include a short docstring and type hints.
After the implementation, include two pytest functions named test_normal_values and test_mixed_values.
```

If the task asks for a pytest snippet, say so directly. The generated file can contain the implementation and pytest functions together.

## 2. Register the Test

Add an entry to `configs/tests.yaml`:

```yaml
- id: parse-and-average
  description: Parse numeric strings and calculate a rounded average.
  prompt_file_location: test-prompts/parse-and-average.txt
  language: python
  extraction_function: parse_and_average
  tests: null
  model_tests:
    required: false
    score: N/A
  our_test:
    checker: tools/check_parse_and_average.py
    score_denominator: 6
```

Use `extraction_function` to tell `tools/extract_model_python.py` which function must exist. Do not rely on the historical `normalize_events` default for a new test.

Use `model_tests.required: true` only when the generated file contains unittest tests that the runner should execute with `unittest`. A requested pytest snippet is normally validated by the independent checker instead.

## 3. Build the Independent Checker

A checker receives the extracted Python file and an optional JSON output path:

```text
python tools/check_parse_and_average.py generated.py --json-out result.json
```

The checker should:

- Load the generated module.
- Verify the public function exists.
- Run focused behavior checks for normal, edge, invalid, and empty inputs.
- Check type hints and documentation when they are part of the contract.
- Return exit code `0` only when every check passes.
- Write structured JSON with `status`, `passed`, and `failed` entries.

Keep checker logic independent from model-authored code. It is the project's source of truth for correctness.

## 4. Validate Generated Pytest Snippets

For tests that request pytest code, the checker should validate the snippet explicitly. The recommended flow is:

1. Parse the generated file with `ast`.
2. Require at least the requested number of `test_*` functions.
3. Compile/import the generated file.
4. Run the generated file with the project interpreter:

```powershell
python -m pytest generated.py -q --disable-warnings
```

5. Record pytest output and failure details in the checker JSON.

The implementation itself may be restricted to the standard library while the checker may use pytest as a validation dependency. `pytest` is listed in `requirements.txt` for this purpose.

Do not count the pytest snippet as a passing result merely because it parses. It must execute successfully.

## 5. Run a Dry Check

Before inference, validate the registry and command shape:

```powershell
python tools/run_tests.py `
  --model qwen25-coder7b `
  --test parse-and-average `
  --profile controlled-quality-8k `
  --context 4096 `
  --output-budget 8192 `
  --dry-run
```

The runner prints the planned count and the exact command. Dry-run does not start inference or write test artifacts.

## 6. Run One Canary

Run one known model/profile/context first:

```powershell
python tools/run_tests.py `
  --model qwen25-coder7b `
  --test parse-and-average `
  --profile controlled-quality-8k `
  --context 4096 `
  --output-budget 8192
```

Inspect the extracted source, compile log, checker JSON, and checker text log under the modelâ€™s `logs/<model>-runner/` directory. Confirm the report appears under `reports/latest/`.

## 7. Expand the Test

After the canary works:

- Run additional contexts and output budgets.
- Run the selected runtime-specific profiles.
- Use `--all-profiles` only when all compatible profiles are intended.
- Keep the test's prompt hash and configuration stable for comparable results.
- Regenerate reports with `tools/reconcile_evidence.py` if artifacts were interrupted or manually restored.

## Completion Checklist

- [ ] Prompt file added and asks for the exact public function.
- [ ] Registry entry added with `extraction_function`.
- [ ] Independent checker added and returns structured JSON.
- [ ] Pytest snippets are discovered and executed when requested.
- [ ] Standard-library and dependency rules are enforced.
- [ ] Dry run passes.
- [ ] One canary passes extraction, compilation, and independent validation.
- [ ] Reports and raw artifacts are present.

