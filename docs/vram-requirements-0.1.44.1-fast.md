# How much available VRAM does Strata need? Fast mode (`--prefill-head-alias --short-read 0`)

**Available VRAM** is the GPU memory that is free when Strata starts (what `nvidia-smi` shows as free; here the card has 8192 MiB in total). It is the only figure that matters: what is using the rest, a browser, the desktop or another program, makes no difference.

Measured 2026-10-16 on an RTX 3060 Ti 8 GB with Strata engine 0.1.44.1, `--kv q4_0`, KV cache reserved up front (no `--kv-grow`), `--vram-reserve-mib 1024`, `--spec 4 --mtp`, `--short-read 0 --prefill-head-alias`. A ballast held part of the VRAM so that the available amount took chosen values; every cell starts a fresh server, a short request, then one 24K-token prompt. Grid step about 200 MiB, so read the limits as +-100 MiB.

## Measured (what worked)

| Model | Context window | Works with at least this much available VRAM | Failed to start with this much or less |
| --- | ---: | ---: | ---: |
| Coder IQ1_M | 131072 | never (it failed even with 7481 MiB available) | 7481 MiB |
| Coder IQ1_M | 65536 | 7114 MiB | - |
| Coder IQ1_M | 32768 | n/a | - |
| IQ3_XXS | 131072 | 7480 MiB | 7288 MiB |
| IQ3_XXS | 65536 | 6912 MiB | 6718 MiB |
| IQ3_XXS | 32768 | 6677 MiB | - |
| IQ2_XS | 131072 | 6904 MiB | 6697 MiB |
| IQ2_XS | 65536 | 6694 MiB | - |
| IQ2_XS | 32768 | 6724 MiB | - |

No engine exit on the long prompt happened in any cell that started: with the KV cache reserved up front, a setup that starts also answers.

## Fitted requirement used by `tools/strata_fit_launch.py`

Available VRAM needed = weights + draft head + VRAM reserve + minimum expert cache + KV cache of the window (+ a 150 MiB safety margin).

| Context window | Coder IQ1_M | IQ3_XXS | IQ2_XS |
| ---: | ---: | ---: | ---: |
| 32768 | 6903 MiB | 6705 MiB | 6133 MiB |
| 65536 | 7176 MiB | 6978 MiB | 6406 MiB |
| 98304 | 7448 MiB | 7250 MiB | 6678 MiB |
| 131072 | 7721 MiB | 7523 MiB | 6951 MiB |
| 196608 | 8266 MiB (more than this card has) | 8068 MiB | 7496 MiB |
| 262144 | 8812 MiB (more than this card has) | 8614 MiB (more than this card has) | 8042 MiB |

Windows above 131,072 tokens are extrapolated (the sweep measured up to 131,072).
A card with more VRAM needs the same amounts: with about 9.5 GB of VRAM available every model reaches the model's maximum window (262,144 tokens).
