# Gemma 4 E4B-it (Q4_K_M) Runtime Guide

## 1. Overview & Model Artifacts

* **Model:** `Gemma-4-E4B-it-Q4_K_M`
* **Architecture:** `dense_ple` (Per-Layer Embeddings / PLE, 8B total parameters / 4B active)
* **Target Hardware:** 8GB VRAM GPU (NVIDIA RTX 3060 Ti / 4060 Ti)

### Model Locations in Project

1. **Monolithic GGUF (for `llama-cli` & `llama-server`):**
   * Path: `models/gemma-4-E4B-it-Q4_K_M/gemma-4-E4B-it-Q4_K_M.gguf`
   * Size: ~4.97 GB
   * Source: `unsloth/gemma-4-E4B-it-GGUF`
2. **Layer-Sharded Package (for distributed Mesh-LLM execution):**
   * Path: `models/gemma-4-E4B-it-Q4_K_M-layers/`
   * Contents: 42 layer shards (`layers/layer-00000.gguf` to `layer-00041.gguf`) + shared components (`embeddings.gguf`, `metadata.gguf`, `common.gguf`, `output.gguf`)
   * Source: `meshllm/gemma-4-E4B-it-Q4_K_M-layers`

---

## 2. Recommended Runtime Parameters

| Parameter | Recommended Value | Rationale |
| :--- | :--- | :--- |
| **GPU Layers (`-ngl`)** | `42` | Fits entirely in VRAM (~4.2 GB allocated), leaving ~3.8 GB headroom on 8GB cards for KV cache. |
| **Reasoning Mode (`--reasoning`)** | `off` | **Mandatory for coding/agent tasks.** Default thinking mode burns generation budget on rumination. |
| **Reasoning Budget (`--reasoning-budget`)** | `0` | Disables internal thinking tokens to maintain fast deterministic output. |
| **Context Window (`-c`)** | `32768` | Standard 32K context fits comfortably in remaining VRAM. |
| **Max Output Tokens (`-n`)** | `8192` | Ample headroom for complete multi-file implementations. |
| **Temperature (`--temp`)** | `0.2` (or `0.0`) | Low temperature ensures disciplined tool calling and syntactically correct code. |
| **Top-P (`--top-p`)** | `0.95` | Standard high-fidelity nucleus sampling. |
| **Seed (`--seed`)** | `42` | Deterministic reproducibility across test runs. |

---

## 3. Direct Execution Commands

### Quick Sanity Test (CUDA Runtime)

```powershell
runtimes/llama-cuda-b11093/llama-cli.exe `
  -m models/gemma-4-E4B-it-Q4_K_M/gemma-4-E4B-it-Q4_K_M.gguf `
  -ngl 42 `
  -c 4096 `
  -n 128 `
  --reasoning off `
  --reasoning-budget 0 `
  --single-turn `
  --simple-io `
  -p "Hello, are you ready? Reply with exactly READY."
```

### Quick Sanity Test (Vulkan Runtime)

```powershell
runtimes/llama-vulkan-b11093/llama-cli.exe `
  -m models/gemma-4-E4B-it-Q4_K_M/gemma-4-E4B-it-Q4_K_M.gguf `
  -ngl 42 `
  -c 4096 `
  -n 128 `
  --reasoning off `
  --reasoning-budget 0 `
  --single-turn `
  --simple-io `
  -p "Hello, are you ready? Reply with exactly READY."
```

---

## 4. Serving for Agent Loops (OpenAI-Compatible Server)

### Tested / Working Command

The exact command below was verified live (`tested/working`) with `http://127.0.0.1:8080/v1/chat/completions` (HTTP 200, prompt response logged):

```powershell
runtimes/llama-cuda-b11093/llama-server.exe `
  -m models/gemma-4-E4B-it-Q4_K_M/gemma-4-E4B-it-Q4_K_M.gguf `
  -ngl 42 `
  -c 32768 `
  -n 512 `
  --reasoning off `
  --port 8080 `
  --host 127.0.0.1
```

* **Tested & Verified:** Responded to `"Are you ready to help?"` with clean non-ruminating output in 3.63s (`logs/gemma-server-reply.json`).
* **Flag Breakdown:**
  * `-m models/gemma-4-E4B-it-Q4_K_M/gemma-4-E4B-it-Q4_K_M.gguf`: Model weights path.
  * `-ngl 42`: Offloads all 42 model layers into GPU VRAM (~4.2 GB used).
  * `-c 8192`: 8K server context window (expandable up to 32K via `-c 32768`).
  * `-n 512`: Max generation tokens per completion.
  * `--reasoning off`: Completely disables thinking tokens so the model immediately generates replies.
  * `--port 8080 --host 127.0.0.1`: Binds local OpenAI-compatible endpoint.

### Extended Configuration for Agent Tool Loops (32K Context + Jinja)

To serve the model with full 32K context and native tool calling enabled for agent frameworks (such as Pi or Hermes Agent):

```powershell
runtimes/llama-cuda-b11093/llama-server.exe `
  -m models/gemma-4-E4B-it-Q4_K_M/gemma-4-E4B-it-Q4_K_M.gguf `
  -ngl 42 `
  -c 32768 `
  -n 8192 `
  --reasoning off `
  --jinja `
  --port 8080 `
  --host 127.0.0.1
```

### Verifying the Server with `tools/test_server.py`

Once the server is running, you can test it directly with:

```powershell
.venv/bin/python.exe tools/test_server.py
```

Optional arguments:
```powershell
.venv/bin/python.exe tools/test_server.py `
  --url "http://127.0.0.1:8080/v1/chat/completions" `
  --prompt "Are you ready to help?" `
  --temperature 0.2 `
  --max-tokens 256 `
  --log-file logs/gemma-server-reply.json
```

---

## 5. Running Configured Project Tests

The model has been registered in `configs/models.yaml` under the ID `gemma4-e4b-it-q4km`.

### Dry-Run Verification

```powershell
.venv/bin/python.exe tools/run_tests.py `
  --model gemma4-e4b-it-q4km `
  --test hello-readiness `
  --dry-run
```

### Single Test Execution (Readiness Check)

```powershell
.venv/bin/python.exe tools/run_tests.py `
  --model gemma4-e4b-it-q4km `
  --profile gemma4-e4b-controlled-8k `
  --test hello-readiness `
  --context 32768 `
  --output-budget 8192
```

### Coding Benchmark Run (`normalize-events-no-unit-tests`)

```powershell
.venv/bin/python.exe tools/run_tests.py `
  --model gemma4-e4b-it-q4km `
  --profile gemma4-e4b-controlled-8k `
  --test normalize-events-no-unit-tests `
  --context 32768 `
  --output-budget 8192
```
