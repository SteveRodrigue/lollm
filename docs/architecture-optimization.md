# Architecture Optimization Tests

This track is intentionally separate from the normal model-quality comparison. It measures runtime and offload behavior only on Windows 11 and the configured NVIDIA GPU set. The project has only been tested on Windows 11; other operating systems are not currently validated. The current configuration selects GPU index 0 with no model splitting, while the runtime registry supports future multi-GPU configurations. It must not change existing profiles, overwrite normal ledgers, or replace fixed profile-specific layer settings.

## Isolation Rules

- Keep `configs/models.yaml`, `configs/tests.yaml`, and normal profiles unchanged while collecting architecture data.
- Store all artifacts below `logs/architecture-optimization/<run-id>/`.
- Do not use `tools/run_tests.py` for this matrix. Its experiment key does not include `gpu_layers` or backend.
- Keep model, prompt, context, sampling, and output budget fixed within a comparison.
- Use the same runtime version and driver state for repeated runs.
- Record failures such as out-of-memory and zero-generation; never silently remove a failed `-ngl` value.
- After each completed repeat, append its row to `results.csv`, refresh `matrix.md`, print the result, and only then start the next repeat.
- If interrupted, completed rows and logs remain valid; an inference interrupted before completion has no result row.
- Each result also records process RSS/private-memory peaks and system RAM total, available-at-start/end, and peak used memory.
- Runtime constraints and executable paths live in the `runtimes` registry in `configs/models.yaml`: vendor, backend, executable, GPU indices, device identifiers, and split mode.
- The default is one NVIDIA GPU at index `0`, using `Vulkan0` or `CUDA0` with `split_mode: none`.
- Multi-GPU configuration is supported by the runtime registry but is not part of the current comparison results.
- Non-NVIDIA vendors are outside the current project scope and are rejected until a vendor-specific runtime and telemetry provider are configured.

## 1. Context x GPU-Layer Matrix

The first single-context sweep is useful for orientation, but it is not enough to select a production setting. Context size consumes KV-cache memory, so the usable `-ngl` ceiling and speed must be measured together. The benchmark runs every context against every layer value and writes both raw rows and a human-readable `matrix.md`.

The benchmark reads eligible models from `configs/models.yaml` and contexts from `common_parameters.context.values` when those options are omitted. The current registry selects Qwen2.5-Coder 7B, Qwen3.5 Q3_K_M, and Qwen3.5 IQ4_XS; it skips the explicitly incompatible Q2_K model.

Architecture defaults are stored separately in `architecture_defaults`: both backends, the layer table `[1, 5, 10, 15, 20, 30, 99]`, 256 output tokens, and two repeats. Normal profiles set their own single `parameters.gpu_layers` value.

Run the complete configured matrix on both registered runtimes:

```powershell
python tools/run_architecture_benchmark.py
```

Defaults are read from `configs/models.yaml`.

Validate the complete configuration and see the exact test count without creating a run directory, changing files, or starting inference:

```powershell
python tools/run_architecture_benchmark.py --dry-run
```

The dry run validates selected model paths, runtime paths, NVIDIA GPU availability, and architecture dimensions before printing `Tests planned`.

Analyze completed architecture results and generate profile proposals without editing configuration:

```powershell
python tools/analyze_architecture_benchmark.py
```

The analyzer reads the newest run for each backend/model, ignores incomplete or failed cells, and writes two proposals per backend/model:

- **Context window:** the highest stable context, selecting the fastest layer count at that context.
- **Max token/sec:** the fastest stable cell at or above the default 32K context floor.

Use `--minimum-context` to change the throughput floor, `--target-context` to change the preferred maximum, and `--output` to save the Markdown report. The generated YAML snippets are proposals only and must be validated with the real coding test before being added to `configs/models.yaml`.

`99` means "try all available layers"; it is expected to fail for some model/context combinations. Read `matrix.md` by context: the best setting can change as context grows.

The resulting `matrix.md` contains one table per backend and model. `results.csv` remains the authoritative per-repeat record and is updated during the run. Keep Qwen3.5 Q2_K out of coding-performance conclusions because its current profile is already marked incompatible/inconsistent.

### Acceptance

- A context/layer pair is **usable** when all repeats load and generate nonzero output with VRAM headroom.
- Prefer the highest stable tokens/sec at each context, not the highest GPU utilization.
- Reject values with out-of-memory, zero-generation, crashes, or materially worse repeat variance.
- After selecting a candidate, validate it with the existing coding test in a new, explicitly named future profile. Do not modify the current profiles yet.

## 2. CUDA versus Vulkan

This is a second architecture experiment, not part of the layer sweep. It uses the CUDA-capable `llama.cpp` executable in `runtimes/llama-cuda-b11073/` and the Vulkan executable from `configs/models.yaml`. Both runtime paths and versions are recorded in the isolated manifest.

### Preparation

1. Verify both executables independently with `llama-cli --version`.
2. Run a CUDA hello/load check before the full matrix.
3. Confirm that both runtimes accept the same command-line flags: `-ngl`, `--load-mode mmap`, context, reasoning, and sampling options.
4. If either runtime rejects a flag, create a separate comparison set; do not silently normalize the commands.

### Comparison design

Use the same model, prompt, context, output budget, seed, and layer values for both backends. First compare the Vulkan-selected layer value and one lower value. Then compare the full layer matrix only if CUDA loads successfully.

```powershell
python tools/run_architecture_benchmark.py `
  --backend Both `
  --gpu-layers 10 20 30 99 `
  --context 4096 `
  --output-tokens 256 `
  --repeats 3
```

Compare generation tokens/sec, prompt-processing tokens/sec, duration, peak VRAM, load failures, and output validity. A backend wins only when it is faster at a stable configuration and does not regress output validity or memory headroom.

### CUDA validation gates

- Runtime loads and reports the intended backend.
- Model loads with positive GPU offload.
- Generation is nonzero and repeatable.
- The same generated output passes the existing compile and independent-checker gates at the selected candidate setting.
- The result is documented as a new architecture comparison, separate from the normal model-quality summaries.

## Profile Promotion

Do not immediately change existing quality profiles. First select a stable `context`/`-ngl` pair per model and context tier from the matrix, then validate those pairs with the real coding test. Only after validation should new runtime-specific architecture profiles be added to `configs/models.yaml`, for example `architecture-vulkan-qwen25-coder7b-throughput`. Existing profiles and defaults remain unchanged.
