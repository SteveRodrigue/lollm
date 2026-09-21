# Installation

This guide targets Windows 11 with an RTX 3060 Ti (8 GB VRAM), NVIDIA Studio drivers, 32 GB RAM, and an AMD 5800X3D. The project has only been tested on Windows 11; other operating systems are not currently validated. The immediate goal is a small-context POC; the end goal is to use the local model from a VS Code chat window. Model files and runtime data should live on a dedicated local data volume rather than the system volume.

The NVIDIA Studio driver branch is relevant because it is the installed GPU stack on this machine; it does not change the model's memory profile, but it matters for compatibility and for future backend changes (Vulkan vs. CUDA).

## 1. Choose the SN850X directory

Identify the drive letter assigned to the SN850X:

```powershell
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size
Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystem, SizeRemaining, Size
```

Use a local directory outside Git as the reusable model workspace:

```powershell
$DataRoot = Join-Path $env:LOCALAPPDATA "local-llm-data"
New-Item -ItemType Directory -Force `
  $DataRoot, `
  "$DataRoot\models", `
  "$DataRoot\runtimes", `
  "$DataRoot\cache", `
  "$DataRoot\logs" | Out-Null
$env:HF_HOME = "$DataRoot\cache\huggingface"
$env:HF_HUB_CACHE = "$DataRoot\cache\huggingface\hub"
[Environment]::SetEnvironmentVariable("HF_HOME", $env:HF_HOME, "User")
[Environment]::SetEnvironmentVariable("HF_HUB_CACHE", $env:HF_HUB_CACHE, "User")
```

Keep the model directory and Hugging Face cache outside the Git repository. The model is tens of gigabytes and the cache needs additional temporary space.

## 2. Install llama.cpp

Install the maintained Windows package with WinGet:

```powershell
winget install --id ggml.llamacpp --exact --source winget `
  --accept-source-agreements --accept-package-agreements
```

The WinGet package installs the Windows Vulkan runtime. Copy its complete package directory into `runtimes/llama-vulkan-b11026/` so the project uses a workspace-local runtime. A separate precompiled CUDA runtime is also available under `runtimes/llama-cuda-b11073/`; both are registered in `configs/models.yaml`. Vulkan and CUDA can be selected through runtime-specific profiles or the architecture benchmark. Verify the configured executables:

```powershell
$VulkanRuntime = "runtimes\llama-vulkan-b11026"
New-Item -ItemType Directory -Force $VulkanRuntime | Out-Null
Copy-Item -Path "<installed-vulkan-package>\*" -Destination $VulkanRuntime -Recurse -Force
```

```powershell
& "$VulkanRuntime\llama-cli.exe" --version
& "$VulkanRuntime\llama-server.exe" --version
```

A GPU-enabled build is required for practical offload. A CPU-only build will be much slower. Keep future runtime versions under `$DataRoot\runtimes` if you install them manually, so runtimes can be replaced or rolled back independently of the models.

For low-VRAM tuning background, consult the linked community guides before changing offload or context settings:

- <https://github.com/GenerelSchwerz/llama.cpp/wiki>
- <https://github.com/GenerelSchwerz/llama.cpp/wiki/Hardware-Setup-Guides>
- <https://github.com/GenerelSchwerz/llama.cpp/wiki/8GB-VRAM-Setup>

## 3. Download the model

The referenced `UD-IQ3_XXS` file is approximately 82 GB. It cannot fit entirely in 8 GB VRAM or 32 GB RAM, but GGUF memory mapping and partial GPU offload can leave most weights on the SN850X. Reserve extra free space for the download and cache.

Install the Hugging Face CLI in an isolated tool environment:

```powershell
winget install --id astral-sh.uv --exact --source winget `
  --accept-source-agreements --accept-package-agreements
uv tool install huggingface-hub
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$env:HF_HOME = "$DataRoot\cache\huggingface"
$env:HF_HUB_CACHE = "$DataRoot\cache\huggingface\hub"
[Environment]::SetEnvironmentVariable("HF_HOME", $env:HF_HOME, "User")
[Environment]::SetEnvironmentVariable("HF_HUB_CACHE", $env:HF_HUB_CACHE, "User")
hf --version
```

The current repository layout has three split files under `UD-IQ3_XXS/`. The API check used to verify that layout is:

```powershell
$modelInfo = Invoke-RestMethod `
  "https://huggingface.co/api/models/unsloth/Qwen3.8-Flash-Next-GGUF"
$modelInfo.siblings | Select-Object -ExpandProperty rfilename `
  | Where-Object { $_ -match "UD-IQ3_XXS" }
```

Download the `UD-IQ3_XXS` GGUF file or split files to the SN850X:

```powershell
$ModelDir = "$DataRoot\models\Qwen3.8-Flash-Next-GGUF"
hf download unsloth/Qwen3.8-Flash-Next-GGUF `
  --include "UD-IQ3_XXS/*.gguf" `
  --local-dir $ModelDir
```

The smaller `UD-IQ1_S` quantization is a fallback when the 82 GB download is impractical. It is still approximately 72.5 GB.

## 4. Run with memory mapping

For a single-file model, use the downloaded GGUF path:

```powershell
$Model = (Get-ChildItem $ModelDir -Recurse -Filter "*UD-IQ3_XXS-00001-of-00003.gguf" | Select-Object -First 1).FullName
llama-cli.exe -m $Model `
  --mmap `
  --mlock 0 `
  -ngl 20 `
  -c 1024 `
  -n 256 `
  -p "Explain how to verify that you are running locally."
```

The initial `-c 1024` context is intentionally small for the POC/MVP. Increase it to `2048` or `4096` only after a successful run and while system memory remains available. Start with a modest `-ngl` value and increase it gradually only while VRAM remains available. If the model is split across multiple GGUF files, keep all parts in the same directory and follow the exact split-file invocation supported by the llama.cpp release.

`--mmap` maps weights from the SN850X instead of eagerly loading the complete model into RAM. This does not make the model small: generation will be storage- and memory-bandwidth-limited, and success depends on the runtime build, context size, and temporary allocations.

### Verified small-model POC

Qwen2.5-Coder-7B-Instruct Q4_K_M successfully loaded on the RTX 3060 Ti and reached the interactive prompt with the following command:

```powershell
$Model = "models/Qwen2.5-Coder-7B-Instruct-GGUF\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
llama-cli.exe -m $Model -ngl 20 -c 1024 -n 32 `
  -p "Hello. Reply in one short sentence." --color off
```

When the process is waiting for input, type a prompt and press Enter. This is the currently validated local model and the recommended starting point for the VS Code integration.

For context sizing, treat `1024` as the initial smoke-test setting only. The practical context gate is separate: test progressively larger values such as `8192`, `16384`, `32768`, and `65536` with a realistic coding prompt that occupies the context and requests a complete answer. A model that allocates a large KV cache but cannot complete a coding task at that size has passed only the allocation check, not the usability gate. Record prompt length, time to first token, generation speed, output completeness, and independent test results in [evidences.md](evidences.md).

## 5. Prepare the VS Code chat endpoint

After the CLI smoke test works, run the same model as a local server. `llama-server` provides an OpenAI-compatible HTTP endpoint that a VS Code chat extension can consume:

```powershell
llama-server.exe -m $Model `
  --mmap `
  --mlock 0 `
  -ngl 20 `
  -c 1024 `
  --host 127.0.0.1 `
  --port 8080 `
  *> "$DataRoot\logs\qwen3.8-flash-next-server.log"
```

Leave this process running while VS Code connects to `http://127.0.0.1:8080/v1`. The exact VS Code extension and its configuration will be selected after the local server responds successfully; do not expose this endpoint beyond localhost unless authentication and network controls have been configured.

## Troubleshooting

- `CUDA out of memory`: lower `-ngl`, then lower `-c`.
- `Cannot load model`: confirm the GGUF filename and that every split file is present.
- Low disk space: keep at least the model size plus several GB of working space free on the SN850X.
- Very slow generation: confirm the CUDA build is active and that the model path is on the configured local data volume, not a synced folder.
- VS Code cannot connect: first verify that `http://127.0.0.1:8080/health` responds while `llama-server.exe` is running.

See [evidences.md](evidences.md) for the facts and assumptions behind this setup.

