# Evidence

This records the facts and checks behind the installation plan. Rerun the machine checks because drive letters, releases, and model files can change.

## Test recording policy

Follow [test-protocol.md](test-protocol.md) when adding a model or extending a test sweep. Each completed process must be recorded immediately before the next test starts. Preserve the complete stdout/stderr log, the immutable raw process output, and the append-only `results.jsonl` ledger under `logs/<short-model-name>`. These artifacts are the recovery record if a batch is interrupted.

Update the relevant matrix or context-test row after every completed run. Use `allocation-pass` only for a successful allocation check, and use `practical-pass` only after a realistic coding prompt completes. Keep allocation results separate from code-quality results so models can be compared at the same context size or at explicitly different context sizes.

The normal protocol requires positive GPU offload. CPU-only results (`-ngl 0`) are allowed only when explicitly requested and must be labeled `cpu-only` and excluded from the normal GPU comparison.

For a detailed readable overview, see [test-results.md](../reports/latest/test-results.md). For the aggregate concise summary, see [test-summary.md](../reports/latest/test-summary.md). Per-test summaries are generated under [reports/latest](../reports/latest/) as `test-summary-<test-id>.md` and matching `.yaml` files. All are regenerated from the durable ledgers after each completed test.

The coding-quality results currently recorded are **preliminary** because the quality runs used `-n 1024`. This can truncate reasoning, source code, or tests. The next controlled quality round must use the parameters documented in [test-protocol.md](test-protocol.md).

The next round will run every selected context at both `-n 8192` and `-n 16384`. These are separate result sets and must remain separate in the report.

<!-- BEGIN AUTO TEST LEDGER -->
## Durable Test Ledger Summary

This section is generated from per-model `results.jsonl` files. It is updated after each completed test.

| Date | Model | Stage | Context | GPU layers | Status | Outcome | Log |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| 2026-09-21T13:50:40.674487Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 4096 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c4096.log |
| 2026-09-21T13:50:40.674487Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 4096 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c4096-independent.txt |
| 2026-09-21T13:52:01.934077Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 16384 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c16384.log |
| 2026-09-21T13:52:01.934077Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 16384 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c16384-independent.txt |
| 2026-09-21T13:53:23.172268Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c32768.log |
| 2026-09-21T13:53:23.172268Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c32768-independent.txt |
| 2026-09-21T13:54:44.656132Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c65536.log |
| 2026-09-21T13:54:44.656132Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c65536-independent.txt |
| 2026-09-21T13:56:06.080403Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c98304.log |
| 2026-09-21T13:56:06.080403Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c98304-independent.txt |
| 2026-09-21T13:57:28.663581Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c131072.log |
| 2026-09-21T13:57:28.663581Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c131072-independent.txt |
| 2026-09-21T13:58:52.213055Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c196608.log |
| 2026-09-21T13:58:52.213055Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c196608-independent.txt |
| 2026-09-21T14:00:17.279223Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c262144.log |
| 2026-09-21T14:00:17.279223Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c262144-independent.txt |
| 2026-09-21T14:01:51.161111Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 4096 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c4096.log |
| 2026-09-21T14:01:51.161111Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 4096 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c4096-independent.txt |
| 2026-09-21T14:03:12.688140Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 16384 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c16384.log |
| 2026-09-21T14:03:12.688140Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 16384 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c16384-independent.txt |
| 2026-09-21T14:04:34.511433Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c32768.log |
| 2026-09-21T14:04:34.511433Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c32768-independent.txt |
| 2026-09-21T14:05:58.295467Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c65536.log |
| 2026-09-21T14:05:58.295467Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c65536-independent.txt |
| 2026-09-21T14:07:21.370353Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c98304.log |
| 2026-09-21T14:07:21.370353Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c98304-independent.txt |
| 2026-09-21T14:08:44.864431Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c131072.log |
| 2026-09-21T14:08:44.864431Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c131072-independent.txt |
| 2026-09-21T14:10:08.436662Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c196608.log |
| 2026-09-21T14:10:08.436662Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c196608-independent.txt |
| 2026-09-21T14:11:33.789360Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c262144.log |
| 2026-09-21T14:11:33.789360Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-controlled-quality-16k-n16384-c262144-independent.txt |
| 2026-09-21T14:13:08.322316Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 4096 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c4096.log |
| 2026-09-21T14:13:08.322316Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 4096 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c4096-independent.txt |
| 2026-09-21T14:14:31.050093Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 16384 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c16384.log |
| 2026-09-21T14:14:31.050093Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 16384 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c16384-independent.txt |
| 2026-09-21T14:15:53.908524Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c32768.log |
| 2026-09-21T14:15:53.908524Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c32768-independent.txt |
| 2026-09-21T14:17:16.124730Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c65536.log |
| 2026-09-21T14:17:16.124730Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c65536-independent.txt |
| 2026-09-21T14:18:37.578007Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c98304.log |
| 2026-09-21T14:18:37.578007Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c98304-independent.txt |
| 2026-09-21T14:19:58.173723Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c131072.log |
| 2026-09-21T14:19:58.173723Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c131072-independent.txt |
| 2026-09-21T14:21:19.270383Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c196608.log |
| 2026-09-21T14:21:19.270383Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c196608-independent.txt |
| 2026-09-21T14:22:43.936154Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c262144.log |
| 2026-09-21T14:22:43.936154Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-8k-n16384-c262144-independent.txt |
| 2026-09-21T14:24:12.942589Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 4096 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c4096.log |
| 2026-09-21T14:24:12.942589Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 4096 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c4096-independent.txt |
| 2026-09-21T14:25:32.076141Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 16384 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c16384.log |
| 2026-09-21T14:25:32.076141Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 16384 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c16384-independent.txt |
| 2026-09-21T14:26:50.109811Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c32768.log |
| 2026-09-21T14:26:50.109811Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c32768-independent.txt |
| 2026-09-21T14:28:10.345765Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c65536.log |
| 2026-09-21T14:28:10.345765Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c65536-independent.txt |
| 2026-09-21T14:29:30.626515Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c98304.log |
| 2026-09-21T14:29:30.626515Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c98304-independent.txt |
| 2026-09-21T14:30:51.989364Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c131072.log |
| 2026-09-21T14:30:51.989364Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c131072-independent.txt |
| 2026-09-21T14:32:13.157396Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c196608.log |
| 2026-09-21T14:32:13.157396Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c196608-independent.txt |
| 2026-09-21T14:33:35.526200Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c262144.log |
| 2026-09-21T14:33:35.526200Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-16k-n32768-c262144-independent.txt |
| 2026-09-21T14:35:00.243854Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 4096 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c4096.log |
| 2026-09-21T14:35:00.243854Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 4096 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c4096-independent.txt |
| 2026-09-21T14:36:19.472586Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 16384 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c16384.log |
| 2026-09-21T14:36:19.472586Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 16384 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c16384-independent.txt |
| 2026-09-21T14:37:39.573494Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c32768.log |
| 2026-09-21T14:37:39.573494Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c32768-independent.txt |
| 2026-09-21T14:38:59.730426Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c65536.log |
| 2026-09-21T14:38:59.730426Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c65536-independent.txt |
| 2026-09-21T14:40:19.896708Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c98304.log |
| 2026-09-21T14:40:19.896708Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c98304-independent.txt |
| 2026-09-21T14:41:41.373462Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c131072.log |
| 2026-09-21T14:41:41.373462Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c131072-independent.txt |
| 2026-09-21T14:43:06.349176Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c196608.log |
| 2026-09-21T14:43:06.349176Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c196608-independent.txt |
| 2026-09-21T14:44:32.940958Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c262144.log |
| 2026-09-21T14:44:32.940958Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=1 | logs/qwen25-coder7b-runner/normalize-events-explicit-contract-high-reasoning-32k-n32768-c262144-independent.txt |
| 2026-09-21T20:06:45.277818Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c32768.log |
| 2026-09-21T20:06:45.277818Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c32768-independent.txt |
| 2026-09-21T20:07:05.061812Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c65536.log |
| 2026-09-21T20:07:05.061812Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c65536-independent.txt |
| 2026-09-21T20:07:26.524293Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c98304.log |
| 2026-09-21T20:07:26.524293Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c98304-independent.txt |
| 2026-09-21T20:07:47.763355Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c131072.log |
| 2026-09-21T20:07:47.763355Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c131072-independent.txt |
| 2026-09-21T20:08:09.602262Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c196608.log |
| 2026-09-21T20:08:09.602262Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c196608-independent.txt |
| 2026-09-21T20:08:32.641584Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c262144.log |
| 2026-09-21T20:08:32.641584Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-8k-n8192-c262144-independent.txt |
| 2026-09-21T20:08:59.862820Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c32768.log |
| 2026-09-21T20:08:59.862820Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c32768-independent.txt |
| 2026-09-21T20:09:19.634781Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c65536.log |
| 2026-09-21T20:09:19.634781Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c65536-independent.txt |
| 2026-09-21T20:09:39.476667Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c98304.log |
| 2026-09-21T20:09:39.476667Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c98304-independent.txt |
| 2026-09-21T20:09:59.417800Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c131072.log |
| 2026-09-21T20:09:59.417800Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c131072-independent.txt |
| 2026-09-21T20:10:21.241717Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c196608.log |
| 2026-09-21T20:10:21.241717Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c196608-independent.txt |
| 2026-09-21T20:10:44.224358Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c262144.log |
| 2026-09-21T20:10:44.224358Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-controlled-quality-16k-n16384-c262144-independent.txt |
| 2026-09-21T20:11:10.323594Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c32768.log |
| 2026-09-21T20:11:10.323594Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c32768-independent.txt |
| 2026-09-21T20:11:30.089979Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c65536.log |
| 2026-09-21T20:11:30.089979Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c65536-independent.txt |
| 2026-09-21T20:11:49.961079Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c98304.log |
| 2026-09-21T20:11:49.961079Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c98304-independent.txt |
| 2026-09-21T20:12:09.972186Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c131072.log |
| 2026-09-21T20:12:09.972186Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c131072-independent.txt |
| 2026-09-21T20:12:30.846457Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c196608.log |
| 2026-09-21T20:12:30.846457Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c196608-independent.txt |
| 2026-09-21T20:12:52.886134Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c262144.log |
| 2026-09-21T20:12:52.886134Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-8k-n16384-c262144-independent.txt |
| 2026-09-21T20:13:17.982995Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c32768.log |
| 2026-09-21T20:13:17.982995Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c32768-independent.txt |
| 2026-09-21T20:13:37.796070Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c65536.log |
| 2026-09-21T20:13:37.796070Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c65536-independent.txt |
| 2026-09-21T20:13:57.587868Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c98304.log |
| 2026-09-21T20:13:57.587868Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c98304-independent.txt |
| 2026-09-21T20:14:17.547967Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c131072.log |
| 2026-09-21T20:14:17.547967Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c131072-independent.txt |
| 2026-09-21T20:14:39.515004Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c196608.log |
| 2026-09-21T20:14:39.515004Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c196608-independent.txt |
| 2026-09-21T20:15:01.543837Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c262144.log |
| 2026-09-21T20:15:01.543837Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-16k-n32768-c262144-independent.txt |
| 2026-09-21T20:15:26.665928Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c32768.log |
| 2026-09-21T20:15:26.665928Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c32768-independent.txt |
| 2026-09-21T20:15:46.475946Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c65536.log |
| 2026-09-21T20:15:46.475946Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c65536-independent.txt |
| 2026-09-21T20:16:06.321683Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c98304.log |
| 2026-09-21T20:16:06.321683Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c98304-independent.txt |
| 2026-09-21T20:16:27.408448Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c131072.log |
| 2026-09-21T20:16:27.408448Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c131072-independent.txt |
| 2026-09-21T20:16:48.345777Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c196608.log |
| 2026-09-21T20:16:48.345777Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c196608-independent.txt |
| 2026-09-21T20:17:10.350340Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c262144.log |
| 2026-09-21T20:17:10.350340Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-high-reasoning-32k-n32768-c262144-independent.txt |
| 2026-09-21T20:17:36.543512Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 30 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-cuda-qwen25-coder7b-context-n8192-c262144.log |
| 2026-09-21T20:17:36.543512Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 30 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-cuda-qwen25-coder7b-context-n8192-c262144-independent.txt |
| 2026-09-21T20:17:51.912295Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 30 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-cuda-qwen25-coder7b-throughput-n8192-c32768.log |
| 2026-09-21T20:17:51.912295Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 30 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-cuda-qwen25-coder7b-throughput-n8192-c32768-independent.txt |
| 2026-09-21T20:17:58.869692Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-vulkan-qwen25-coder7b-context-n8192-c262144.log |
| 2026-09-21T20:17:58.869692Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-vulkan-qwen25-coder7b-context-n8192-c262144-independent.txt |
| 2026-09-21T20:18:24.140994Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-normalize-events | 32768 | 30 | generation-pass | failure_class=none; pending validation | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-vulkan-qwen25-coder7b-throughput-n8192-c32768.log |
| 2026-09-21T20:18:24.140994Z | models/Qwen2.5-Coder-7B-Instruct-GGUF/qwen2.5-coder-7b-instruct-q4_k_m.gguf | quality-validation | 32768 | 30 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen25-coder7b-runner/pi-1000-digits-architecture-vulkan-qwen25-coder7b-throughput-n8192-c32768-independent.txt |
| 2026-09-21T14:46:02.364697Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 4096 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c4096.log |
| 2026-09-21T14:46:02.364697Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 4096 | 10 | practical-fail | extraction=1; compile=1; unittest=1; independent=1 | logs/qwen35-q3km-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c4096-independent.txt |
| 2026-09-21T14:52:54.449724Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 16384 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c16384.log |
| 2026-09-21T14:52:54.449724Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 16384 | 10 | practical-fail | extraction=0; compile=0; unittest=1; independent=0 | logs/qwen35-q3km-runner/normalize-events-explicit-contract-controlled-quality-8k-n8192-c16384-independent.txt |
| 2026-09-21T20:18:32.243891Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c32768.log |
| 2026-09-21T20:18:32.243891Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c32768-independent.txt |
| 2026-09-21T20:34:02.828066Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c65536.log |
| 2026-09-21T20:34:02.828066Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c65536-independent.txt |
| 2026-09-21T20:49:33.258688Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c98304.log |
| 2026-09-21T20:49:33.258688Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c98304-independent.txt |
| 2026-09-21T21:05:27.812669Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 131072 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c131072.log |
| 2026-09-21T21:05:27.812669Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 131072 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c131072-independent.txt |
| 2026-09-21T21:21:39.675861Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 196608 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c196608.log |
| 2026-09-21T21:21:39.675861Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 196608 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c196608-independent.txt |
| 2026-09-21T21:37:33.657273Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 262144 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c262144.log |
| 2026-09-21T21:37:33.657273Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 262144 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-8k-n8192-c262144-independent.txt |
| 2026-09-21T21:53:20.296163Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 32768 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-16k-n16384-c32768.log |
| 2026-09-21T21:53:20.296163Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 32768 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-16k-n16384-c32768-independent.txt |
| 2026-09-21T23:48:56.692084Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 65536 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-16k-n16384-c65536.log |
| 2026-09-21T23:48:56.692084Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 65536 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-16k-n16384-c65536-independent.txt |
| 2026-09-22T00:27:53.467783Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-normalize-events | 98304 | 10 | generation-pass | failure_class=none; pending validation | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-16k-n16384-c98304.log |
| 2026-09-22T00:27:53.467783Z | models/Qwen3.5-9B-Coder-Q3_K_M/Qwen3.5-9B-Coder.Q3_K_M.gguf | quality-validation | 98304 | 10 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen35-q3km-runner/pi-1000-digits-controlled-quality-16k-n16384-c98304-independent.txt |
| 2026-09-22T02:09:24.696929Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-stable-vulkan-n1024-c4096.log |
| 2026-09-22T02:09:24.696929Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-stable-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:14:04.861564Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-stable-cuda-n1024-c4096.log |
| 2026-09-22T02:14:04.861564Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-stable-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:18:59.889874Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-nightly-vulkan-n1024-c4096.log |
| 2026-09-22T02:18:59.889874Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-nightly-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:23:53.305825Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-nightly-cuda-n1024-c4096.log |
| 2026-09-22T02:23:53.305825Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-with-tests-qwen38-iq2xs-nightly-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:28:35.181550Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-stable-vulkan-n1024-c4096.log |
| 2026-09-22T02:28:35.181550Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-stable-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:30:25.036546Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-stable-cuda-n1024-c4096.log |
| 2026-09-22T02:30:25.036546Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-stable-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:32:07.271528Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-nightly-vulkan-n1024-c4096.log |
| 2026-09-22T02:32:07.271528Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-nightly-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:34:11.535313Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-nightly-cuda-n1024-c4096.log |
| 2026-09-22T02:34:11.535313Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-no-unit-tests-qwen38-iq2xs-nightly-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:35:52.790305Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-stable-vulkan-n1024-c4096.log |
| 2026-09-22T02:35:52.790305Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-stable-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:41:27.615647Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-stable-cuda-n1024-c4096.log |
| 2026-09-22T02:41:27.615647Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-stable-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:46:21.928732Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-nightly-vulkan-n1024-c4096.log |
| 2026-09-22T02:46:21.928732Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-nightly-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:52:02.855565Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-nightly-cuda-n1024-c4096.log |
| 2026-09-22T02:52:02.855565Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/normalize-events-explicit-contract-qwen38-iq2xs-nightly-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:56:59.322329Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-stable-vulkan-n1024-c4096.log |
| 2026-09-22T02:56:59.322329Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-stable-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:57:18.348974Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-stable-cuda-n1024-c4096.log |
| 2026-09-22T02:57:18.348974Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-stable-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:57:31.906877Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-nightly-vulkan-n1024-c4096.log |
| 2026-09-22T02:57:31.906877Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-nightly-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T02:57:53.209875Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-nightly-cuda-n1024-c4096.log |
| 2026-09-22T02:57:53.209875Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/hello-readiness-qwen38-iq2xs-nightly-cuda-n1024-c4096-independent.txt |
| 2026-09-22T02:58:13.412249Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-stable-vulkan-n1024-c4096.log |
| 2026-09-22T02:58:13.412249Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-stable-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T03:02:02.191466Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-stable-cuda-n1024-c4096.log |
| 2026-09-22T03:02:02.191466Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-stable-cuda-n1024-c4096-independent.txt |
| 2026-09-22T03:06:56.587171Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-nightly-vulkan-n1024-c4096.log |
| 2026-09-22T03:06:56.587171Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-nightly-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T03:10:40.160581Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-nightly-cuda-n1024-c4096.log |
| 2026-09-22T03:10:40.160581Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/pi-1000-digits-qwen38-iq2xs-nightly-cuda-n1024-c4096-independent.txt |
| 2026-09-22T03:15:37.770033Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-stable-vulkan-n1024-c4096.log |
| 2026-09-22T03:15:37.770033Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-stable-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T03:17:17.765656Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-stable-cuda-n1024-c4096.log |
| 2026-09-22T03:17:17.765656Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-stable-cuda-n1024-c4096-independent.txt |
| 2026-09-22T03:18:50.084817Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-nightly-vulkan-n1024-c4096.log |
| 2026-09-22T03:18:50.084817Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-pass | extraction=0; compile=0; unittest=0; independent=0 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-nightly-vulkan-n1024-c4096-independent.txt |
| 2026-09-22T03:20:30.293023Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-normalize-events | 4096 | 1 | generation-pass | failure_class=none; pending validation | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-nightly-cuda-n1024-c4096.log |
| 2026-09-22T03:20:30.293023Z | models/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS/Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf | quality-validation | 4096 | 1 | practical-fail | extraction=0; compile=0; unittest=0; independent=1 | logs/qwen38-flash-next-gsq-rco-iq2xs-runner/parse-and-average-qwen38-iq2xs-nightly-cuda-n1024-c4096-independent.txt |
<!-- END AUTO TEST LEDGER -->
## Local hardware

The project reference records:

- GPU: GeForce RTX 3060 Ti with 8 GB VRAM.
- Driver branch: NVIDIA Studio drivers.
- System memory: 32 GB RAM.
- CPU: AMD Ryzen 7 5800X3D with 8 physical cores.
- Fast storage: Fastest available disk on the system (e.g. high-speed NVMe SSD).

Source: [references.md](references.md).

For local inference, the NVIDIA Studio driver branch matters mainly because it is the installed GPU driver stack; it does not change the model requirements themselves. It is relevant for Vulkan or CUDA compatibility checks, but the model-size and memory assumptions remain the same.

Verify the storage model and drive letter with:

```powershell
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size
Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystem, SizeRemaining, Size
```

### Verified on 2026-09-20

The workspace path is intentionally omitted from this public evidence record. Windows reports that the selected local volume is hosted by:

- Disk: `3`
- Device: Fastest available NVMe SSD
- Bus: `NVMe`
- Capacity: approximately 1 TB

Therefore, the current project folder is already on the selected local volume. The model and cache paths in [installation.md](installation.md) should also use a local data volume outside synced folders.

### Installation progress verified on 2026-09-20

- `<repo-root>` exists on the fastest available disk.
- The reusable directories `models`, `runtimes`, `cache`, `configs`, and `logs` exist under `<repo-root>`.
- WinGet installed `llama.cpp` package `ggml.llamacpp`, build `b11026`.
- The installed package is a Windows Vulkan build; `llama-cli` and `llama-server` both report version `0.4.1-dev`.
- `uv` installed `huggingface-hub` version `1.32.0` and provided the `hf` command.
- The model repository currently stores `UD-IQ3_XXS` as three split GGUF files under the `UD-IQ3_XXS/` directory.

## Low-VRAM references

The reference file links these community llama.cpp guides for Windows and low-VRAM tuning:

- General llama.cpp guidance: <https://github.com/GenerelSchwerz/llama.cpp/wiki>
- Hardware setup guides: <https://github.com/GenerelSchwerz/llama.cpp/wiki/Hardware-Setup-Guides>
- 8 GB VRAM setup: <https://github.com/GenerelSchwerz/llama.cpp/wiki/8GB-VRAM-Setup>

These links are supporting documentation, not local test results. The local runtime currently installed is the WinGet Windows Vulkan build, so any CUDA-specific advice must be translated to Vulkan options and verified locally.

## Model and quantization

Source model page: <https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF>

The project reference identifies `unsloth/Qwen3.8-Flash-Next-GGUF` and the intended example quantization `UD-IQ3_XXS` at approximately 82 GB. The smallest quantization noted during investigation was `UD-IQ1_S` at approximately 72.5 GB.

These sizes show that the complete model cannot be resident in 8 GB VRAM or 32 GB RAM. The planned approach is memory-mapped GGUF loading with partial GPU offload, currently through the installed Vulkan backend, not a claim that the model fits wholly in memory.

## Model test matrix

| Model | Format / quant | Approx. size | VRAM target | Test run | Result |
| --- | --- | ---: | ---: | --- | --- |
| Qwen3.8-Flash-Next-UD-IQ3_XXS | 3-part GGUF | ~82 GB | 8 GB VRAM class | `llama-cli -m ... -ngl 20 -c 1024 -n 32` | Failed: Vulkan out-of-device-memory during model load |
| Qwen3.6-35B-A3B-Q4_K_M | Single GGUF | ~20.4 GB | 8 GB VRAM class | `llama-cli -m ... -ngl 20 -c 1024 -n 32` | Failed: Vulkan out-of-device-memory during model load |
| Qwen2.5-Coder-7B-Instruct-Q4_K_M | Single GGUF | ~4.7 GB | 8 GB VRAM class | Protocol run: `-ngl 10`; load `-c 1024`; quality `-c 4096` | Load passed; allocation passed through 262144; quality practical-fail: compile passed, model tests had 3 failures, independent checker failed timestamp-message check |
| Qwen3.5-9B-Coder-Q2_K | Single GGUF | ~3.65 GB | 8 GB VRAM class | Protocol run: `-ngl 10`; load `-c 1024`; quality `-c 4096` | Load passed; allocation passed through 262144; quality practical-fail: generated output was not valid Python (syntax error) |
| Qwen3.5-9B-Coder-Q3_K_M | Single GGUF | ~4.41 GB | 8 GB VRAM class | Protocol run: `-ngl 10`; load `-c 1024`; quality `-c 4096` | Load passed; allocation passed through 262144; quality practical-fail: generated output was not valid Python (syntax error) |
| Qwen3.5-9B-Coder-IQ4_XS | Single GGUF | ~4.99 GB | 8 GB VRAM class | Protocol run: `-ngl 10`; load `-c 1024`; quality `-c 4096` | Load passed; allocation passed through 262144; quality practical-fail: generated output was not valid Python (syntax error) |

This table records the tests that were actually attempted or downloaded on this machine. The 7B Q4_K_M model is the first tested candidate that loads successfully with the current Vulkan runtime and small-context settings. The Qwen3.5-9B-Coder rows are community GGUF quantizations from <https://huggingface.co/mradermacher/Qwen3.5-9B-Coder-GGUF>.

## Full test commands

The WinGet runtime was invoked by its installed path during validation:

```powershell
$env:LLAMA_VULKAN_EXECUTABLE
```

### Previously tested models

Qwen3.8-Flash-Next `UD-IQ3_XXS`:

```powershell
& $LlamaCli -m $Model -ngl 20 -c 1024 -n 32 -p "Hello. Reply in one short sentence."
```

Qwen3.6-35B-A3B `Q4_K_M`:

```powershell
& $LlamaCli -m $Model -ngl 20 -c 1024 -n 32 -p "Hello. Reply in one short sentence."
```

Qwen2.5-Coder-7B-Instruct `Q4_K_M` successful smoke test:

```powershell
$Model = "models/Qwen2.5-Coder-7B-Instruct-GGUF\qwen2.5-coder-7b-instruct-q4_k_m.gguf"
& $LlamaCli -m $Model -ngl 20 -c 1024 -n 32 `
	-p "Hello. Reply in one short sentence." --color off
```

### Planned Qwen3.5-9B-Coder tests

Use the same load-test shape for each downloaded quantization:

```powershell
$Model = "models/Qwen3.5-9B-Coder-Q2_K\Qwen3.5-9B-Coder.Q2_K.gguf"
& $LlamaCli -m $Model -ngl 10 -c 1024 -n 32 `
	-p "Hello. Reply in one short sentence." --color off
```

Change `$Model` to one of these paths for the other candidates:

```powershell
"models/Qwen3.5-9B-Coder-Q3_K_M\Qwen3.5-9B-Coder.Q3_K_M.gguf"
"models/Qwen3.5-9B-Coder-IQ4_XS\Qwen3.5-9B-Coder.IQ4_XS.gguf"
```

For each model that loads, first repeat the allocation check with progressively larger context sizes:

```powershell
foreach ($Context in 1024, 2048, 4096, 8192, 16384, 32768, 65536) {
	& $LlamaCli -m $Model -ngl 10 -c $Context -n 16 `
		-p "Reply with exactly READY." --single-turn --simple-io --color off
}
```

The allocation check only proves that the runtime can reserve the KV cache. After the largest successful allocation check, run a practical coding-context test with a long source-like prompt and enough output tokens to exercise the context:

```powershell
$CodingContext = @"
You are reviewing a small Python project. The following source contains several functions,
tests, and comments. Identify the bug, explain the root cause briefly, then provide a minimal
patch and tests. Preserve the public API and handle empty input, duplicate values, invalid
values, and deterministic output. Do not invent dependencies.

SOURCE AND TEST MATERIAL:
$LongSourceAndTests
"@
& $LlamaCli -m $Model -ngl 10 -c $Context -n 256 `
	-p $CodingContext --single-turn --simple-io --color off
```

Use the same `$LongSourceAndTests` content for every model. Record the actual prompt token count, total wall-clock duration from process start to exit, context setting, time to first token, generation speed, output completeness, and independent test result. A context setting is considered **practical** only when the model both loads and completes this coding task; a one-token response at a large context is only an allocation checkpoint.

Coding-quality and speed test:

```powershell
& $LlamaCli -m $Model -ngl 10 -c 4096 -n 256 `
	-p "Write a Python function merge_intervals(intervals) that merges overlapping inclusive integer intervals. Return intervals sorted by start. Handle an empty input and single-item input. Then provide three concise tests covering overlap, disjoint intervals, and touching intervals. Output only the function and tests." --color off
```

The exact output, load result, context size, generation speed, and independent test result should be recorded beside each model row after execution.

## Planned comparison protocol

The three Qwen3.5 candidates will be compared against the working Qwen2.5 baseline using the same settings where possible:

1. **Load test:** start with `-c 1024`, conservative `-ngl`, `-n 16`, `--single-turn`, and `--simple-io`. Record whether the model loads, generates, and exits cleanly or fails with an allocation error.
2. **Allocation context test:** increase context through `1024`, `2048`, `4096`, `8192`, `16384`, `32768`, and `65536`, stopping at the first failure. This measures memory reservation only and is not the model's advertised maximum context.
3. **Practical context test:** at each selected successful size, use the same long coding prompt and meaningful output budget. Record prompt size, total wall-clock duration, time to first token, generation speed, completeness, and independent test result.
4. **Coding quality test:** give every model the same implementation task. Execute the generated tests independently and compare correctness, edge-case handling, instruction following, unnecessary reasoning, and compile/test success.
5. **Selection gate:** prefer the model with the best coding result at a practical context, then use generation speed, memory headroom, and disk size as tie-breakers.

The coding prompt should be kept identical across models. A practical first task is a small function with explicit edge cases and a short test suite, so correctness can be checked independently rather than judged only by prose.

## Coding-quality and code-test rubric

The shared task is `normalize_events(events)`, recorded in [test-prompts/normalize-events.txt](../test-prompts/normalize-events.txt). Every model must produce a complete Python implementation and `unittest` tests.

### Required behavior

- Return a new list and never mutate the input list or its event dictionaries.
- Preserve valid event fields, including `payload` and optional metadata.
- Reject an event missing `id` or `timestamp` with `ValueError` and a useful message.
- Deduplicate by `id`, keeping the record with the newest timestamp.
- Sort the final result deterministically by timestamp and then `id`.
- Handle empty input and a single valid event.
- Use only the Python standard library and keep the requested public function name.
- Do not install packages, modify dependency files, add third-party imports, invoke `pip` or another package manager, or instruct the user to install anything.

### Quality scoring

Score each raw response using the same rubric:

| Criterion | Pass condition |
| --- | --- |
| Completeness | Includes the requested function and executable tests, without unfinished placeholders |
| Correctness | Implements validation, newest-record deduplication, deterministic sorting, and field preservation |
| Edge cases | Tests empty input, sorting, duplicate ids, invalid records, immutability, and deterministic output |
| Instruction following | Output is valid Python source without Markdown fences, package-install commands, dependency changes, third-party imports, or unrelated explanation |
| Maintainability | Clear names, focused logic, useful error messages, and no unnecessary API changes |

### Independent code-test procedure

1. Save the model response from its raw log to a temporary `.py` file, removing only accidental terminal decoration if present.
2. Compile it with `python -m py_compile <file>`.
3. Run it with `python -m unittest <file> -v`.
4. Inspect the tests to confirm that they genuinely cover the required cases rather than merely asserting constants.
5. Check the response for package-install commands, dependency-file changes, third-party imports, and package-manager instructions. Any of these fails the dependency constraint.
6. Run an external checker containing additional cases: newest duplicate wins, equal timestamps sort by id, input remains unchanged after the call, missing `id`, missing `timestamp`, empty input, and payload/metadata preservation.
7. Record total wall-clock duration in seconds, compile result, test result, external-check result, dependency-constraint result, missing requirements, and a concise quality score beside the model in the matrix.

The code-quality result is **pass** only when the response compiles, its own tests pass, and the external checker passes. A model may have a successful generation and speed measurement while still failing this coding gate.

## Test-results matrix

Fill this matrix as each test is performed. A context result is marked **allocation-pass** only when the process exits successfully; it becomes **practical-pass** only after a realistic coding prompt completes and the generated code passes independent tests.

| Model | Quant | Load | 1K | 2K | 4K | 8K | 16K | 32K | 64K | 96K | 128K | 192K | 256K | Coding quality | Code tests | Duration | Speed | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| Qwen2.5-Coder-7B-Instruct | Q4_K_M | pass | pending | pending | pending | pending | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-fail | allocation-fail | allocation-fail | pending | pending | pending | 22.1 t/s @ 96K | Failed allocation at 128K and above; practical coding pending |
| Qwen3.5-9B-Coder | Q2_K | pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | inconclusive | allocation-pass | inconclusive | pending | pending | pending | 14.3 t/s @ 96K | 128K and 256K measured 0.0 t/s; 192K generated at ~14.2 t/s |
| Qwen3.5-9B-Coder | Q3_K_M | pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | pending | pending | pending | 10.7 t/s @ 96K | 192K ~9.7 t/s; 256K ~10.4 t/s; practical coding pending |
| Qwen3.5-9B-Coder | IQ4_XS | pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | allocation-pass | pending | pending | pending | 9.6 t/s @ 96K | 192K ~9.3 t/s; 256K ~10.0 t/s; practical coding pending |

### Context-test log

| Date | Model | Context | Test type | Command/log | Result | Speed | Next action |
| --- | --- | ---: | --- | --- | --- | ---: | --- |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 1024, 2048, 4096, 8192 | Allocation check | `logs/qwen35-Q2_K-c*.log` | Passed all four | See smoke table | Test 16384 allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 1024, 2048, 4096, 8192 | Allocation check | `logs/qwen35-Q3_K_M-c*.log` | Passed all four | See smoke table | Test 16384 allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 1024, 2048, 4096, 8192 | Allocation check | `logs/qwen35-IQ4_XS-c*.log` | Passed all four | See smoke table | Test 16384 allocation |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 16384 | Allocation check | `logs/qwen25-coder7b-c16384.log` | Passed; exit code 0; no allocation error | ~21.0 t/s | Test practical 16K coding prompt |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 16384 | Allocation check | `logs/qwen35-Q2_K-c16384.log` | Passed; exit code 0; no allocation error | ~11.1 t/s | Test practical 16K coding prompt |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 16384 | Allocation check | `logs/qwen35-Q3_K_M-c16384.log` | Passed; exit code 0; no allocation error | ~9.0 t/s | Test practical 16K coding prompt |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 16384 | Allocation check | `logs/qwen35-IQ4_XS-c16384.log` | Passed; exit code 0; no allocation error | ~9.1 t/s | Test practical 16K coding prompt |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 98304 | Allocation check | `logs/qwen25-coder7b-c98304.log` | Passed; exit code 0; no allocation error | ~22.1 t/s | Test 128K allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 98304 | Allocation check | `logs/qwen35-Q2_K-c98304.log` | Passed; exit code 0; no allocation error | ~14.3 t/s | Test 128K allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 98304 | Allocation check | `logs/qwen35-Q3_K_M-c98304.log` | Passed; exit code 0; no allocation error | ~10.7 t/s | Test 128K allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 98304 | Allocation check | `logs/qwen35-IQ4_XS-c98304.log` | Passed; exit code 0; no allocation error | ~9.6 t/s | Test 128K allocation |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 131072 | Allocation check | `logs/qwen25-coder7b-c131072.log` | Failed: Vulkan out-of-device-memory; exit code 1 | N/A | Practical maximum is below 128K |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 131072 | Allocation check | `logs/qwen35-Q2_K-c131072.log` | Loaded; no measurable generated tokens; exit code 0 | 0.0 t/s | Rerun 128K before classifying |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 131072 | Allocation check | `logs/qwen35-Q3_K_M-c131072.log` | Passed; exit code 0; generated response | ~11.8 t/s | Run practical 128K coding prompt if feasible |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 131072 | Allocation check | `logs/qwen35-IQ4_XS-c131072.log` | Passed; exit code 0; generated response | ~9.6 t/s | Run practical 128K coding prompt if feasible |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 196608 | Allocation check | `logs/qwen25-coder7b-c196608.log` | Failed: Vulkan out-of-device-memory; exit code 1 | N/A | Stop allocation sweep for this model |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 196608 | Allocation check | `logs/qwen35-Q2_K-c196608.log` | Passed; exit code 0; generated response | ~14.2 t/s | Test 256K allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 196608 | Allocation check | `logs/qwen35-Q3_K_M-c196608.log` | Passed; exit code 0; generated response | ~9.7 t/s | Test 256K allocation |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 196608 | Allocation check | `logs/qwen35-IQ4_XS-c196608.log` | Passed; exit code 0; generated response | ~9.3 t/s | Test 256K allocation |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 262144 | Allocation check | `logs/qwen25-coder7b-c262144.log` | Failed: Vulkan out-of-device-memory; exit code 1 | N/A | Stop allocation sweep for this model |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 262144 | Allocation check | `logs/qwen35-Q2_K-c262144.log` | Loaded; no measurable generated tokens; exit code 0 | 0.0 t/s | Rerun 256K before classifying |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 262144 | Allocation check | `logs/qwen35-Q3_K_M-c262144.log` | Passed; exit code 0; generated response | ~10.4 t/s | Run practical 256K coding prompt if feasible |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 262144 | Allocation check | `logs/qwen35-IQ4_XS-c262144.log` | Passed; exit code 0; generated response | ~10.0 t/s | Run practical 256K coding prompt if feasible |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 65536 | Allocation check | `logs/qwen25-coder7b-c65536.log` | Passed; exit code 0; no allocation error | ~21.0 t/s | Run practical long-prompt coding test |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 65536 | Allocation check | `logs/qwen35-Q2_K-c65536.log` | Passed; exit code 0; no allocation error | ~11.5 t/s | Run practical long-prompt coding test |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 65536 | Allocation check | `logs/qwen35-Q3_K_M-c65536.log` | Passed; exit code 0; no allocation error | ~9.3 t/s | Run practical long-prompt coding test |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 65536 | Allocation check | `logs/qwen35-IQ4_XS-c65536.log` | Passed; exit code 0; no allocation error | ~9.1 t/s | Run practical long-prompt coding test |
| 2026-09-20 | Qwen2.5-Coder-7B-Instruct-Q4_K_M | 32768 | Allocation check | `logs/qwen25-coder7b-c32768.log` | Passed; exit code 0; no allocation error | ~20.1 t/s | Test practical 32K coding prompt |
| 2026-09-20 | Qwen3.5-9B-Coder-Q2_K | 32768 | Allocation check | `logs/qwen35-Q2_K-c32768.log` | Passed; exit code 0; no allocation error | ~13.8 t/s | Test practical 32K coding prompt |
| 2026-09-20 | Qwen3.5-9B-Coder-Q3_K_M | 32768 | Allocation check | `logs/qwen35-Q3_K_M-c32768.log` | Passed; exit code 0; no allocation error | ~10.5 t/s | Test practical 32K coding prompt |
| 2026-09-20 | Qwen3.5-9B-Coder-IQ4_XS | 32768 | Allocation check | `logs/qwen35-IQ4_XS-c32768.log` | Passed; exit code 0; no allocation error | ~8.7 t/s | Test practical 32K coding prompt |

Rows are updated after each test rather than marking a planned test as successful in advance.

## Results logged during testing

### Qwen3.5-9B-Coder smoke tests

All three downloaded models were tested sequentially on 2026-09-20 with `-ngl 10`, `-c 1024`, `-n 16`, `--single-turn`, and `--simple-io`. Each process exited with code `0` after producing a response.

| Model | Context tested | Result | Generation speed |
| --- | ---: | --- | ---: |
| Qwen2.5-Coder-7B-Instruct-Q4_K_M | 1024 | Passed; returned `READY` | ~21.1 t/s |
| Qwen3.5-9B-Coder-Q2_K | 1024 | Passed | ~13.1 t/s |
| Qwen3.5-9B-Coder-Q3_K_M | 1024 | Passed; visible reasoning before response | ~10.9 t/s |
| Qwen3.5-9B-Coder-IQ4_XS | 1024 | Passed; visible reasoning before response | ~6.6 t/s |

### Context checks

Each model was tested at `1024`, `2048`, `4096`, and `8192` context with a one-token response, using `-ngl 10`, `--single-turn`, and `--simple-io`. All twelve checks exited with code `0` and no detected allocation error. Therefore, `8192` is the highest context validated so far for allocation, not the practical coding limit. The next gate is a larger allocation sweep followed by realistic long-prompt coding tests.

## Context-size choice

The project reference requests a small context window for the initial POC/MVP. The installation guide therefore starts llama.cpp with `-c 1024`, which reduces KV-cache memory requirements. The context can be increased incrementally after the first successful local generation.

## VS Code end goal

The project reference states that the end goal is to run the model from VS Code in a chat window. A persistent local server is therefore required after the CLI POC. The installation guide uses `llama-server` and its localhost OpenAI-compatible endpoint as the integration boundary; a VS Code extension can be selected and configured once that endpoint is verified.

## Runtime assumptions

llama.cpp supports GGUF models, CUDA GPU offload, and memory mapping via `--mmap`. Confirm the current Windows archive and executable name here:

<https://github.com/ggml-org/llama.cpp/releases/latest>

This is an attemptable configuration, not a guarantee of acceptable speed or successful generation. Disk space, CUDA compatibility, context size, temporary allocations, and the exact model split layout can affect the result.

