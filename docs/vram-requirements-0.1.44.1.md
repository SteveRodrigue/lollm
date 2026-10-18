# How much available VRAM does Strata need?

**Available VRAM** is the GPU memory that is free when Strata starts (what `nvidia-smi` shows as free; here the card has 8192 MiB in total). It is the only figure that matters: what is using the rest, a browser, the desktop or another program, makes no difference.

Measured 2026-10-16 on an RTX 3060 Ti 8 GB with Strata engine 0.1.44.1, `--kv q4_0`, KV cache reserved up front (no `--kv-grow`), `--vram-reserve-mib 1024`, `--spec 4 --mtp`. A ballast held part of the VRAM so that the available amount took chosen values; every cell starts a fresh server, a short request, then one 24K-token prompt. Grid step about 200 MiB, so read the limits as +-100 MiB.

## Measured (what worked)

| Model | Context window | Works with at least this much available VRAM | Failed to start with this much or less |
| --- | ---: | ---: | ---: |
| Coder IQ1_M | 131072 | never (it failed even with 7128 MiB available) | 7128 MiB |
| Coder IQ1_M | 65536 | never (it failed even with 7499 MiB available) | 7499 MiB |
| Coder IQ1_M | 32768 | 7493 MiB | 7281 MiB |
| IQ3_XXS | 131072 | never (it failed even with 7496 MiB available) | 7496 MiB |
| IQ3_XXS | 65536 | 7371 MiB | 7172 MiB |
| IQ3_XXS | 32768 | 6937 MiB | 6609 MiB |
| IQ2_XS | 131072 | 7655 MiB | 7290 MiB |
| IQ2_XS | 65536 | 6682 MiB | - |
| IQ2_XS | 32768 | 6757 MiB | - |

No engine exit on the long prompt happened in any cell that started: with the KV cache reserved up front, a setup that starts also answers.

## Fitted requirement used by `tools/strata_fit_launch.py`

Available VRAM needed = weights + draft head + VRAM reserve + minimum expert cache + KV cache of the window (+ a 150 MiB safety margin).

| Context window | Coder IQ1_M | IQ3_XXS | IQ2_XS |
| ---: | ---: | ---: | ---: |
| 32768 | 7424 MiB | 7069 MiB | 6729 MiB |
| 65536 | 7697 MiB | 7342 MiB | 7002 MiB |
| 98304 | 7969 MiB | 7614 MiB | 7274 MiB |
| 131072 | 8242 MiB (more than this card has) | 7887 MiB | 7547 MiB |
| 196608 | 8787 MiB (more than this card has) | 8432 MiB (more than this card has) | 8092 MiB |
| 262144 | 9333 MiB (more than this card has) | 8978 MiB (more than this card has) | 8638 MiB (more than this card has) |

A card with more VRAM needs the same amounts: with about 9.5 GB of VRAM available every model reaches the model's maximum window (262,144 tokens).
