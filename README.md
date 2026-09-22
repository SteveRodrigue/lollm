# lollm

Local GGUF model testing on Windows 11 with llama.cpp and Vulkan. The project has only been tested on Windows 11; other operating systems are not currently validated.

The project records reproducible model experiments for one NVIDIA GeForce RTX 3060 Ti with 8 GB VRAM, using GPU index 0. Current testing and architecture optimization are single-GPU only: models are not split across multiple GPUs. Large local assets are intentionally excluded from Git: model files, Hugging Face cache, runtime files, logs, and virtual environments stay on the machine.

## Repository Layout

- `configs/` - YAML model and test registries
- `docs/` - installation notes, protocol, evidence, and generated result summaries
- `test-prompts/` - versioned prompts used by the test runner
- `tools/` - extraction, validation, reconciliation, and batch-runner scripts
- `logs/` - raw per-run outputs and validation artifacts
- `reports/` - generated aggregate and per-test summaries
- `requirements.txt` - Python tooling dependencies

## Setup

Use an isolated Python environment:

```powershell
python -m venv .venv
python -m pip install -r requirements.txt
```

The Vulkan and CUDA runtime paths in `configs/models.yaml` are repository-relative. Copy the local Vulkan package into `runtimes/llama-vulkan-b11026/` before running tests; runtime binaries are intentionally ignored by Git.

Quality profiles can select a runtime explicitly with `runtime: vulkan` or `runtime: cuda`; profiles without that field use `default_runtime`.

## Run Tests

Preview a configured run without starting inference:

```powershell
python tools/run_tests.py `
  --model qwen35-q3km `
  --test normalize-events-explicit-contract `
  --context 4096 `
  --output-budget 8192 `
  --dry-run
```

Run a configured test:

```powershell
python tools/run_tests.py `
  --model qwen35-q3km `
  --test normalize-events-explicit-contract `
  --context 4096 `
  --output-budget 8192
```

Run the pi precision test, which does not require model-authored tests:

```powershell
python tools/run_tests.py `
  --model qwen35-q3km `
  --test pi-1000-digits `
  --context 4096 `
  --output-budget 8192
```

Retry only previously failed experiment keys:

```powershell
python tools/run_tests.py --retry-failed
```

Resume an interrupted matrix by skipping cases that already have validation results:

```powershell
python tools/run_tests.py `
  --model qwen25-coder7b `
  --test pi-1000-digits `
  --missing-only
```

`--skip-completed` is an equivalent spelling. A case is considered complete only after its validation ledger row is written, so an interrupted case remains eligible.

Each run stores raw output, extracted candidates, validation logs, and ledger rows under `logs/`. Reports are regenerated after each checkpoint under `reports/latest/`:

- `reports/latest/test-results.md` - aggregate readable results digest
- `reports/latest/test-summary.md` - concise readable summary
- `reports/latest/test-summary.yaml` - machine-readable summary
- `reports/latest/test-summary-<test-id>.md` - per-test readable summary
- `reports/latest/test-summary-<test-id>.yaml` - per-test machine-readable summary

## Current Model Notes

Qwen3.5 Q2_K is marked `incompatible-inconsistent` for coding under the installed runtime. Its limited hello profiles remain documented for conversational experiments. Qwen2.5-Coder-7B, Qwen3.5 Q3_K_M, and Qwen3.5 IQ4_XS are the current coding comparison candidates.

## Protocol

Read [docs/test-protocol.md](docs/test-protocol.md) before adding or comparing tests. See [docs/creating-tests.md](docs/creating-tests.md) when adding a new prompt, checker, or pytest snippet. Existing 1K-output coding results are marked preliminary. Controlled quality runs use separate 8K and 16K output budgets, fixed sampling, explicit reasoning settings, durable ledgers, and per-test summaries.

