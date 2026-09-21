# Model Test Protocol

This protocol defines how to test a new GGUF model on this machine and record comparable results. It targets Windows 11, one NVIDIA GeForce RTX 3060 Ti with 8 GB VRAM at GPU index 0, and 32 GB system memory. The project has only been tested on Windows 11; other operating systems are not currently validated. Current protocol runs do not split models across multiple GPUs or support non-NVIDIA devices.

The declarative test registry is [configs/tests.yaml](../configs/tests.yaml). Runtime and model profiles are in [configs/models.yaml](../configs/models.yaml). Add new prompts and parameterized tests there instead of embedding new test definitions in the runner.

For the step-by-step process for creating a prompt, registry entry, independent checker, and pytest validation, see [creating-tests.md](creating-tests.md).

Python tests declare `extraction_function` in `configs/tests.yaml`. The shared extractor uses that function name to locate the model's Python candidate, so tests such as `pi-1000-digits` can extract `generate_pi` without normalize-events-specific logic.

## Configuration-driven runner

Use `tools/run_tests.py` to execute configured tests. The runner reads both YAML files, saves artifacts and ledger rows under `logs/<model-id>-runner`, and refreshes the evidence and summary reports after each checkpoint. Install the Python dependency in an isolated environment first:

This configuration-driven Python runner is the current execution path. The longer PowerShell command examples later in this document are legacy/manual protocol references; when they conflict with the runner or YAML registry, the code and registry are authoritative.

Profiles may set `runtime: vulkan` or `runtime: cuda`. When omitted, the runner uses `default_runtime` from `configs/models.yaml`. The selected runtime supplies the executable, backend, device selection, and version recorded in the ledger.

Rerunning the same model, test, profile, context, and output-budget combination replaces its generation and validation ledger rows and artifacts. Different parameters remain separate experiments.

```powershell
python -m venv .venv
python -m pip install -r requirements.txt
```

Preview a run without starting llama.cpp:

```powershell
python tools/run_tests.py `
  --model qwen35-q2k `
  --test hello-readiness `
  --dry-run
```

Run a selected model and test:

```powershell
python tools/run_tests.py `
  --model qwen35-q3km `
  --test normalize-events-with-tests
```

Override contexts or output budgets for a focused run:

```powershell
python tools/run_tests.py `
  --model qwen35-q3km `
  --test normalize-events-with-tests `
  --context 4096 --context 16384 `
  --output-budget 8192 --output-budget 16384
```

After changing a model or test configuration, rerun only cases whose latest recorded quality result failed:

```powershell
python tools/run_tests.py --retry-failed
```

Use `--model` and `--test` with `--retry-failed` to narrow the retry set. The runner never enables CPU-only execution; it requires positive GPU offload from the model configuration.

The protocol has four separate gates:

1. **Load gate:** the model loads, generates a short response, and exits cleanly.
2. **Allocation gate:** the requested context can be allocated. This is a memory check only.
3. **Practical-context gate:** the model completes a meaningful coding prompt at the selected context.
4. **Code-quality gate:** the generated Python source compiles, passes its own tests, and passes an independent checker.

Do not call a model usable based only on a successful allocation check.

## Durable recording rule

Treat every individual command as a checkpoint. Before starting a batch, create its log directory. After each process exits, save the complete stdout/stderr log and immediately record that result in [evidences.md](evidences.md) before starting the next context or model. Never wait until the full batch completes to update the evidence.

Use an append-only run ledger as the durable machine-readable record. Define the ledger after `$LogDirectory` is set in section 1. A ledger row must be written even when a test fails, times out, or is interrupted after the process exits:

```powershell
$Ledger = Join-Path $LogDirectory "results.jsonl"
function Add-TestResult {
  param(
    [string]$Stage,
    [int]$Context,
    [string]$Status,
    [string]$Outcome,
    [int]$ExitCode,
    [double]$DurationSeconds,
    [string]$Log,
    [string]$RawOutput = "",
    [string]$PromptFile = "",
    [string]$PromptName = "",
    [string]$PromptSha256 = "",
    [int]$OutputBudget = 8192,
    [int]$ReasoningBudget = 4096,
    [string]$ReasoningMode = "auto",
    [double]$Temperature = 0.2,
    [double]$TopP = 0.95,
    [int]$Seed = 42
  )
  [pscustomobject]@{
    date = (Get-Date).ToString("o")
    run_id = $RunId
    model = $Model
    runtime = $RuntimeVersion
    backend = "Vulkan"
    gpu_layers = $GpuLayers
    stage = $Stage
    context = $Context
    status = $Status
    outcome = $Outcome
    exit_code = $ExitCode
    duration_seconds = [math]::Round($DurationSeconds, 3)
    log = $Log
    raw_output = $RawOutput
    prompt_file = $PromptFile
    prompt_name = $PromptName
    prompt_sha256 = $PromptSha256
    output_budget = $OutputBudget
    reasoning_budget = $ReasoningBudget
    reasoning_mode = $ReasoningMode
    temperature = $Temperature
    top_p = $TopP
    seed = $Seed
  } | ConvertTo-Json -Compress | Add-Content -Path $Ledger
}
```

The JSONL ledger and raw logs are the recovery record. If power is lost, inspect the last complete ledger row and resume with the next unrecorded test. Do not rerun completed tests unless the log or ledger row is missing or marked `inconclusive`.

## 1. Record the test configuration

Before testing, record:

- Test date and machine/runtime version.
- Model repository, exact quantization, file size, and local path.
- Whether the model is single-file or split across GGUF files.
- Backend, GPU offload setting (`-ngl`), context size, output limit, and prompt file.
- Any existing work in `docs/evidences.md`; do not overwrite earlier results.

Use the first GGUF shard for a split model. Keep all shards in the same directory. Confirm the expected files before running:

```powershell
Get-ChildItem $ModelDirectory -Recurse -Filter *.gguf |
  Select-Object FullName, Length
```

Set the runtime and model variables for the current test:

```powershell
$LlamaCli = $env:LLAMA_VULKAN_EXECUTABLE
$Model = "models/<model-directory>\<model-file-or-first-shard>.gguf"
$ModelDirectory = Split-Path $Model
$LogDirectory = "logs/<short-model-name>"
$GpuLayers = 10
$AllowCpuOnly = $false
$RunId = "$(Get-Date -Format yyyyMMdd-HHmmss)-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$RuntimeVersion = (& $LlamaCli --version | Out-String).Trim()
$QualityPromptFile = "<repo-root>\test-prompts\normalize-events.txt"
$QualityPromptHash = (Get-FileHash $QualityPromptFile -Algorithm SHA256).Hash
function Get-PromptHash {
  param([string]$Text)
  $Hasher = [security.cryptography.sha256]::Create()
  try {
    return [bitconverter]::ToString(
      $Hasher.ComputeHash([text.encoding]::UTF8.GetBytes($Text))
    ).Replace("-", "")
  } finally {
    $Hasher.Dispose()
  }
}
New-Item -ItemType Directory -Force $LogDirectory | Out-Null
Set-Content (Join-Path $LogDirectory "run-manifest.txt") @(
  "run_id=$RunId"
  "model=$Model"
  "runtime=$RuntimeVersion"
  "backend=Vulkan"
  "gpu_layers=$GpuLayers"
  "quality_prompt_file=$QualityPromptFile"
  "quality_prompt_sha256=$QualityPromptHash"
)

if (-not $AllowCpuOnly -and $GpuLayers -le 0) {
  throw "CPU-only testing is disabled. Set AllowCpuOnly to true only when explicitly requested."
}
```

Use the same runtime and backend for every model in a comparison. If the runtime changes, start a new comparison set.

For slower, higher-effort coding runs, use one of the profiles in `configs/models.yaml`:

| Profile | Total output | Reasoning budget |
| --- | ---: | ---: |
| `high-reasoning-8k` | 16K | 8K |
| `high-reasoning-16k` | 32K | 16K |
| `high-reasoning-32k` | 32K | 24K |

These profiles are intended for models that support the reasoning template correctly. Do not use them for Qwen3.5 Q2_K, which is marked incompatible/inconsistent for coding. More reasoning budget can help planning, but it also increases runtime and leaves less room for the final answer unless the total output budget is increased.

The runner classifies failed generation attempts as `out-of-memory`, `context-overflow`, `invalid-arguments`, `zero-generation`, or `process-error` in the ledger. A process that exits zero but reports `Generation: 0.0 t/s` is recorded as `zero-generation`, not a successful completion.

## 2. Run the minimum load test

For the current runner, use the selected profile's single `parameters.gpu_layers` value and runtime entry. Keep that profile fixed across models when making a comparison. If a model fails at the profile setting, record the failure; do not silently substitute another profile. The manual command below is a legacy protocol example; the runner is authoritative.

```powershell
$Log = Join-Path $LogDirectory "load-c1024.log"
$LoadPrompt = "Reply with exactly READY."
$LoadPromptHash = Get-PromptHash $LoadPrompt
$Start = Get-Date
& $LlamaCli -m $Model -ngl $GpuLayers -c 1024 -n 16 `
  -p $LoadPrompt --single-turn --simple-io --color off `
  *> $Log
$ExitCode = $LASTEXITCODE
$Duration = ((Get-Date) - $Start).TotalSeconds
$Outcome = if ($ExitCode -eq 0) { "model loaded and generated" } else { "model load or generation failed" }
Add-TestResult -Stage "load" -Context 1024 `
  -Status $(if ($ExitCode -eq 0) { "pass" } else { "fail" }) `
  -Outcome $Outcome -ExitCode $ExitCode -DurationSeconds $Duration -Log $Log `
  -PromptName "load-ready" -PromptSha256 $LoadPromptHash
Write-Host "Checkpoint written to $Ledger; update evidences.md now."
Write-Host "Exit code: $ExitCode"
Get-Content $Log -Tail 30
& python "<repo-root>\tools\reconcile_evidence.py" --evidence "<repo-root>\docs\evidences.md" --logs "<repo-root>\logs"
```

Record:

- `pass` only if the model loads, produces output, and exits with code `0`.
- `fail` if model loading or memory allocation fails, the process crashes, or the process exits nonzero.
- The prompt rate and generation rate reported by llama.cpp.
- Whether the response followed the exact `READY` instruction. Instruction-following is separate from the load result.
- The complete log path.

Do not silently retry a failed comparable run at a different GPU layer count. If an exploratory lower-positive-`-ngl` run is explicitly requested, give it a distinct run ID and exclude it from the comparison set. Do not use `-ngl 0` as part of the normal protocol. CPU-only testing is permitted only when the user explicitly requests it by setting `$AllowCpuOnly = $true`; label those results `cpu-only` and exclude them from GPU model comparisons.

## 3. Run the allocation sweep

Run the following contexts in order:

`1024`, `2048`, `4096`, `8192`, `16384`, `32768`, `65536`, `98304`, `131072`, `196608`, and `262144`.

Use a short response so the test focuses on model and KV-cache allocation:

```powershell
$Contexts = 1024, 2048, 4096, 8192, 16384, 32768, 65536, 98304, 131072, 196608, 262144
$AllocationPrompt = "Reply with exactly READY."
$AllocationPromptHash = Get-PromptHash $AllocationPrompt
foreach ($Context in $Contexts) {
  $Log = Join-Path $LogDirectory "allocation-c$Context.log"
  $Start = Get-Date
  & $LlamaCli -m $Model -ngl $GpuLayers -c $Context -n 16 `
    -p $AllocationPrompt --single-turn --simple-io --color off `
    *> $Log
  $ExitCode = $LASTEXITCODE
  $Duration = ((Get-Date) - $Start).TotalSeconds
  if ($ExitCode -eq 0 -and (Select-String -Path $Log -Pattern "Generation:|generated" -Quiet)) {
    $Status = "allocation-pass"
  } elseif ($ExitCode -eq 0) {
    $Status = "inconclusive"
  } else {
    $Status = "allocation-fail"
  }
  Add-TestResult -Stage "allocation" -Context $Context -Status $Status `
    -Outcome "allocation check only" -ExitCode $ExitCode -DurationSeconds $Duration -Log $Log `
    -PromptName "allocation-ready" -PromptSha256 $AllocationPromptHash
  Write-Host "Context ${Context}: $Status; exit code $ExitCode; log $Log"
  Write-Host "Checkpoint written to $Ledger; update evidences.md now."
  & python "<repo-root>\tools\reconcile_evidence.py" --evidence "<repo-root>\docs\evidences.md" --logs "<repo-root>\logs"
  if ($Status -eq "allocation-fail") {
    Write-Host "Stopping allocation sweep after confirmed failure."
    break
  }
}
```

For each context, record one of:

- `allocation-pass`: exit code `0`, generated output, and no load/allocation error.
- `allocation-fail`: model or KV-cache allocation failed, or the process exited nonzero.
- `inconclusive`: exit code `0` but no measurable generated output, a timeout, or another result that requires a rerun.
- `not-tested`: stop the sweep after a confirmed failure unless there is a reason to test a larger value.

A larger context must not be marked successful merely because the process loaded. If no tokens were generated, use `inconclusive` and record the reason.

The highest allocation-pass context is not automatically the usable context. It only establishes a candidate for the practical-context test.

## Next-round controlled quality parameters

The existing quality results are preliminary because they used `-n 1024`. Do not compare those results directly with the next round. The next round must use one new run ID and the following fixed parameters for every model and context:

| Parameter | Required value | Reason |
| --- | --- | --- |
| Runtime | Profile-selected entry from `runtimes` | Record the exact runtime and build |
| Backend | Profile-selected runtime backend | Keep the backend and sampler implementation fixed |
| GPU offload | Profile `parameters.gpu_layers` | Keep the named profile reproducible |
| Memory mapping | `--mmap` | Keep model loading behavior consistent |
| CPU locking | `--mlock 0` | Avoid forcing the full model into RAM |
| Sampling temperature | `--temp 0.2` | Reduce random variation in code output |
| Top-p | `--top-p 0.95` | Keep the normal sampling distribution fixed |
| Seed | `--seed 42` | Make repeated runs reproducible where supported |
| Reasoning mode | `--reasoning auto` | Preserve each model's supported thinking template |
| Reasoning budget | `--reasoning-budget 4096` | Prevent thinking from consuming the entire answer budget |
| Total output budget | `-n 8192` and `-n 16384` | Run both controlled budgets; never mix their results |
| Prompt | Exact `test-prompts/normalize-events.txt` contents | Keep the coding task identical |
| Extraction | `tools/extract_model_python.py` | Keep raw output immutable and parsing consistent |
| Validation | Compile, model tests, and six-check independent checker | Keep final scoring consistent |

Use this quality command shape for each value of `$OutputBudget`:

```powershell
& $LlamaCli -m $Model `
  -ngl $GpuLayers `
  --mmap `
  --mlock 0 `
  -c $Context `
  -n $OutputBudget `
  --temp 0.2 `
  --top-p 0.95 `
  --seed 42 `
  --reasoning auto `
  --reasoning-budget 4096 `
  --single-turn --simple-io --color off `
  -p $Prompt
```

Test these context sizes first:

`4096`, `16384`, `32768`, `65536`, `98304`, `131072`, `196608`, and `262144`.

Run the complete context sequence twice for each model:

```powershell
foreach ($OutputBudget in 8192, 16384) {
  foreach ($Context in 4096, 16384, 32768, 65536, 98304, 131072, 196608, 262144) {
    # Run the quality command and validation for this exact budget/context pair.
  }
}
```

The result set therefore contains two independent matrices per model comparison:

- `-n 8192`: normal controlled output budget.
- `-n 16384`: extended reasoning/output budget.

Do not combine scores from the two budgets. Include `output_budget` in every run manifest, ledger row, artifact filename, and report table. A test at the same context but a different `-n` value is a different experiment.

Record the effort parameters in `run-manifest.txt` and every ledger row. A run is comparable only when the model, context, prompt hash, runtime, `-ngl`, sampling settings, reasoning settings, and `-n` value match this table. If a model does not support a reasoning flag, record the unsupported flag and start a separate comparison set rather than silently changing the command.

## 4. Run the practical-context test

Choose one or more allocation-pass contexts. For a new model, test at least the highest reliable allocation-pass context and one lower context with useful memory headroom. Use the same prompt and output limit for every model being compared.

For the first quality test, use the committed prompt file:

```powershell
$PromptFile = $QualityPromptFile
$Prompt = Get-Content $PromptFile -Raw
$PromptHash = $QualityPromptHash
$Context = 4096
$Log = Join-Path $LogDirectory "quality-normalize-events-c$Context.log"
$Output = Join-Path $LogDirectory "quality-normalize-events-c$Context.transcript.txt"
$RawOutput = Join-Path $LogDirectory "quality-normalize-events-c$Context.raw-output.txt"
$Start = Get-Date
& $LlamaCli -m $Model -ngl $GpuLayers -c $Context -n 8192 `
  --mmap --mlock 0 --temp 0.2 --top-p 0.95 --seed 42 `
  --reasoning auto --reasoning-budget 4096 `
  -p $Prompt --single-turn --simple-io --color off `
  *> $Log
$ExitCode = $LASTEXITCODE
$Duration = ((Get-Date) - $Start).TotalSeconds
Get-Content $Log -Raw | Set-Content $Output -Encoding utf8
Get-Content $Log -Raw | Set-Content $RawOutput -Encoding utf8
Add-TestResult -Stage "quality-normalize-events" -Context $Context `
  -Status $(if ($ExitCode -eq 0) { "generation-pass" } else { "generation-fail" }) `
  -Outcome "pending independent validation" -ExitCode $ExitCode -DurationSeconds $Duration `
  -Log $Log -RawOutput $RawOutput -PromptFile $PromptFile `
  -PromptName "normalize-events" -PromptSha256 $PromptHash
& python "<repo-root>\tools\reconcile_evidence.py" --evidence "<repo-root>\docs\evidences.md" --logs "<repo-root>\logs"
Write-Host "Checkpoint written to $Ledger; update evidences.md now."
Write-Host "Exit code: $ExitCode; duration: $Duration seconds; transcript: $Output; raw output: $RawOutput"
```

The transcript and raw-output artifacts must be saved before judging the result. The raw-output artifact is an immutable copy of the complete process output; it is not yet a Python source file. Extract the model response into a separate generated `.py` candidate, preserving both originals unchanged. The practical-context result is `practical-pass` only when the model loads, generates a complete answer, exits successfully, and the independent code checks pass. Record:

- Context setting and actual prompt token count from the log.
- Total wall-clock duration from process start to exit.
- Time to first token and generation speed when reported.
- Whether the response is complete and contains the requested function and tests.
- Whether output was truncated, dominated by reasoning, wrapped in Markdown fences, or otherwise needs cleanup.
- The raw log path, raw-output path, and extracted response path.

A one-token response at a large context is an allocation result, not a practical-context pass.

## 5. Validate the generated code independently

Extract the model response from the immutable `.raw-output.txt` artifact into `normalize-events.py` with the repository extractor. Preserve the transcript and raw output permanently. Do not repair the implementation before scoring it. If Markdown fences or explanatory text are present, the extractor may isolate the Python candidate for execution, but record the formatting as an instruction-following failure. Extraction is not a code-quality pass.

Run the model's own tests:

```powershell
$Generated = "logs/<short-model-name>\normalize-events.py"
$RawOutput = "logs/<short-model-name>\quality-normalize-events-c4096.raw-output.txt"
$ExtractionMetadata = "logs/<short-model-name>\normalize-events-extraction.json"
$CompileLog = "logs/<short-model-name>\normalize-events-compile.txt"
$UnitTestLog = "logs/<short-model-name>\normalize-events-unittest.txt"
& python "<repo-root>\tools\extract_model_python.py" $RawOutput $Generated `
  --metadata $ExtractionMetadata *> $ExtractionMetadata
$ExtractionCode = $LASTEXITCODE
if ($ExtractionCode -ne 0) {
  Write-Host "Extraction failed; record practical-fail and do not run Python tests."
  exit $ExtractionCode
}
& python -m py_compile $Generated *> $CompileLog
$CompileCode = $LASTEXITCODE
& python -m unittest $Generated -v *> $UnitTestLog
$TestCode = $LASTEXITCODE
& python "<repo-root>\tools\check_normalize_events.py" $Generated `
  --json-out "logs/<short-model-name>\normalize-events-independent.json" `
  *> "logs/<short-model-name>\normalize-events-independent.txt"
$IndependentCode = $LASTEXITCODE
Write-Host "Compile: $CompileCode; unittest: $TestCode; independent: $IndependentCode"
```

PowerShell 5.1 commonly writes redirected native-process output as UTF-16LE. When inspecting a unittest or checker log from Python, read it with `encoding="utf-16le"` when the file contains `\x00` characters, or use the encoding-aware parser in `reconcile_evidence.py`. Reading these logs as UTF-8 produces misleading visible null bytes but does not indicate corrupted test results.

After the independent checker, append a second ledger row for the final outcome. Use `practical-pass` only when compilation, the model's tests, the independent checker, and the dependency constraint all pass. Otherwise use `practical-fail` and record the specific failed checks in `outcome`:

```powershell
$ValidationStatus = if ($ExtractionCode -eq 0 -and $CompileCode -eq 0 -and $TestCode -eq 0 -and $IndependentCode -eq 0) {
  "practical-pass"
} else {
  "practical-fail"
}
$ValidationOutcome = "extraction=$ExtractionCode; compile=$CompileCode; unittest=$TestCode; independent=$IndependentCode; dependency-constraint=manual-review"
$IndependentOutput = "logs/<short-model-name>\normalize-events-independent.json"
Add-TestResult -Stage "quality-validation" -Context $Context `
  -Status $ValidationStatus -Outcome $ValidationOutcome -ExitCode $IndependentCode `
  -DurationSeconds 0 -Log $IndependentOutput -RawOutput $IndependentOutput `
  -PromptFile $PromptFile -PromptName "normalize-events" -PromptSha256 $PromptHash
& python "<repo-root>\tools\reconcile_evidence.py" --evidence "<repo-root>\docs\evidences.md" --logs "<repo-root>\logs"
```

Then update the hand-written model matrix with the quality score and dependency-constraint review. The generated ledger summary is the immediate durable checkpoint; the matrix is the human comparison view.

Then run an independent checker containing at least these cases:

- Empty input.
- One valid event.
- Sorting by timestamp, then `id` for equal timestamps.
- Duplicate ids keep the newest timestamp.
- Payload and optional metadata are preserved.
- Missing `id` raises `ValueError` with a useful message.
- Missing `timestamp` raises `ValueError` with a useful message.
- The input list and event dictionaries are unchanged after the call.
- Repeated equivalent calls produce deterministic output.

The code-quality result is `pass` only when all of these are true:

- The source compiles.
- The model's own tests pass.
- The independent checker passes.
- The required public function is present and complete.
- Only the Python standard library is used.
- There are no package-install commands, dependency changes, third-party imports, or package-manager instructions.

Score the response separately for completeness, correctness, edge-case coverage, instruction following, and maintainability. A generation can be fast and successful while still failing the code-quality gate.

## 6. Update the evidence records

Add the new model to the test-results matrix in [evidences.md](evidences.md). Use the exact quantization name and these status terms:

- `pass` or `fail` for the load gate.
- `allocation-pass`, `allocation-fail`, `inconclusive`, or `not-tested` for each context.
- `practical-pass` or `practical-fail` for a completed coding prompt.
- `pending` until the code-quality checks are complete.

Add a context-test log row for every tested context that matters to the decision. Include the command or log path, exit result, speed, and next action. Keep raw logs under `<repo-root>\logs` and do not mark planned tests as completed before they run.

At minimum, record this per model:

| Field | Value |
| --- | --- |
| Model and quantization | Exact repository and quant name |
| File size and layout | Size; single or split GGUF |
| Runtime/backend | llama.cpp version and Vulkan/CUDA backend |
| Offload/context | `-ngl` and `-c` values |
| Load result | pass/fail, exit code, log path |
| Allocation results | Status for every tested context |
| Practical result | Context, completeness, log path |
| Code result | Compile, own tests, independent checker, dependency constraint |
| Performance | Duration, prompt tokens, time to first token, generation speed |
| Notes | Errors, reasoning behavior, truncation, next action |

Every quality run must leave these artifacts before the next model starts: `run-manifest.txt`, `results.jsonl`, the complete transcript, the immutable raw output, extraction metadata, the extracted generated test file, compile output, unittest output, independent-checker output, and the final evidence row. A missing artifact means the run is incomplete and must not be scored as a pass.

Record each completed test immediately in the context-test log and results matrix. Include the raw log and raw response artifact paths so a later reviewer can reproduce the score without rerunning the model. For long batches, update `evidences.md` after every context result, not only after the final context.

## 7. Select a model

Choose the model with the best code-quality result at a practical GPU-offloaded context. Use generation speed, GPU memory headroom, context reliability, and disk size as tie-breakers. Treat any `-ngl 0` result as CPU-only and exclude it from the normal comparison unless CPU-only testing was explicitly requested.

Do not change the prompt, context, output limit, runtime, or extraction rules between models in the same comparison unless the change is recorded and a new comparison set is started.

