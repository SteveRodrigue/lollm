# Strata on an 8 GB GPU: setting-by-setting benchmark

Measured 2026-10-13 on a consumer desktop with an **NVIDIA GeForce RTX 3060 Ti** (8 GiB VRAM) and 31.9 GiB RAM. Strata project 0.1.43.1, commit `a0116b27`, engine 0.1.43.1. Model: qwen3.8-flash-next-coder-iq1_m (IQ1_M), 131072-token context. Each variant changes one thing from the baseline config; 3 run(s) per test, medians with ranges. Speed only: no output-quality check was run.

## Hardware

| Component | Details |
| --- | --- |
| CPU | AMD Ryzen 7 5800X3D 8-Core Processor (8 cores / 16 threads, base 3401 MHz, L3 96.0 MiB) |
| RAM | 31.9 GiB total: 4 module(s): 8 GiB DDR4-3600, 8 GiB DDR4-3600, 8 GiB DDR4-3600, 8 GiB DDR4-3600; rated 3600 MT/s, running 3600 MT/s |
| RAM bandwidth (measured) | read 32.9 GB/s, copy 37.8 GB/s (read+write traffic), 8 threads; theoretical 57.6 GB/s (3600 MT/s x 8 B x 2 channels (assumed)) |
| GPU | NVIDIA GeForce RTX 3060 Ti: 8192 MiB VRAM, 38 SMs, L2 3.0 MiB, 256-bit bus, memory clock up to 7001 MHz, SM clock up to 2100 MHz |
| VRAM bandwidth (measured) | 401.3 GB/s device-to-device copy (read+write traffic) |
| GPU power limit | 240.00 W (default 240.00 W, max 325.00 W) |
| PCIe link | max Gen3 x16; idle Gen3 x16; under load Gen3 x16 |
| PCIe bandwidth (measured) | host to GPU 13.04 GB/s pinned, 9.24 GB/s pageable; GPU to host 13.17 GB/s pinned, 7.87 GB/s pageable |
| Resizable BAR | BAR1 8192 MiB (enabled (BAR >= VRAM)) |
| GPU driver | 616.92 |
| Model drive | WD_BLACK SN850X 1000GB (NVMe SSD, 932 GiB); sequential read 3.37 GB/s (unbuffered, 2 GiB) |
| OS | Windows 11 (10.0.26300); power plan: Utilisation normale |

Bandwidths are measured with `tools/strata_hwinfo.py` (RAM: 8 threads numpy read/copy; VRAM: `cudaMemcpy` device-to-device, counting read+write traffic; PCIe: 256 MiB `cudaMemcpy`, link read from `nvidia-smi` while copying; disk: unbuffered sequential read from the middle of the model file). Background load was not controlled.

## Results

Decode = tokens generated per second; prompt = prompt tokens ingested per second on a fresh (uncached) prompt; TTFT = time to first token. Peak RAM = highest system memory in use (total minus available, file cache excluded) while the variant ran. Percentages are relative to the first baseline run.

| Variant | Chat decode tok/s | Chat TTFT s | 4K prompt tok/s | 16K prompt tok/s | 16K TTFT s | Agent decode tok/s | Agent TTFT s | Agent cache hit % | Peak RAM in use GiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 17.4 (11.8-22.4) | 1.66 (1.21-2.57) | 363 (266-376) | 370 (368-373) | 43.4 (43.1-43.7) | 15.3 (10.1-21.5) | 19.73 (8.34-22.77) | 68.7 | 31.8 |

## What each variant changes

- **baseline**: the config as it is now (`--spec 4 --mtp`, `--kv q4_0`, `--kv-grow`, reserve 1024 MiB, 131072 context)

## Launch line and settings of the baseline

```text
strata.exe --pack coder-iq1_m --native Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf --expert-profile expert-profile-coder.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 131072 --vram-reserve-mib 1024 --kv q4_0 --kv-grow --mmap-experts
```

Server settings: `model_name=qwen3.8-flash-next-coder-iq1_m`, `port=8080`, `gpu=0`, `gpus_asked=True`, `open_browser=False`

## Failures and skipped tests

None.

## Method and limits

- Tool: Strata's `tools/strata_bench.py` (suite described in its docs/COMMUNITY_BENCHMARKS.md), driven by `tools/strata_bench_matrix.py`, which restarts the server for every variant with a modified copy of the config.
- Thinking is off, temperature 0. The agent session reuses the model's own replies, so token counts vary slightly per run.
- Strata's route-tail skip (on by default since 0.1.42) changes answers slightly; no correctness check was run here.
- One machine, one model pack, one OS session per variant; ranges show run-to-run spread, not a statistical test.
- Hostname, user name, absolute paths and IP addresses are not recorded.

## Reproduce

```text
python tools/strata_bench_matrix.py --only baseline,kv-k8v4,no-mtp
```
