# 8 GB cards: what fits depends on the AVAILABLE VRAM (measured table)

**TL;DR**
On an 8 GB card the deciding number is the VRAM that is available (free) when Strata starts, not what is using the rest. Measured with a ballast (KV cache reserved up front, `--kv-grow` off, one 24K-token prompt per cell, engine 0.1.44.1; 0.1.43.1 agrees within one 200 MiB grid step). Available VRAM needed:

| Model | 32,768 | 65,536 | 131,072 | 131,072 in fast mode (`--prefill-head-alias --short-read 0`) |
| --- | ---: | ---: | ---: | ---: |
| IQ2_XS | about 6,760 MiB | about 6,680 MiB | about 7,650 MiB | about 6,900 MiB |
| IQ3_XXS | about 6,940 MiB | about 7,370 MiB | never started (7,500 MiB tried) | about 7,480 MiB |
| Coder IQ1_M | about 7,490 MiB | never started (7,500 MiB tried) | never started | 65,536 from about 7,110 MiB; 131,072 never |

An 8 GB card has about 7,600 to 7,700 MiB available when nothing else uses it, so a browser can decide whether a 128K window starts. Strata's recommended resident Coder config does not start at 131,072 tokens on 8 GB at all. Fast mode needs less VRAM at the same window (the output head's VRAM is lent to the prompt path). Suggestion: a short 8 GB section in the docs with this table, and a startup message that states the available VRAM and what the chosen window needs.

## What happened
With the same flags the outcome changed with the available VRAM: IQ2_XS with `--spec 4 --mtp --kv q4_0 --mmap-experts --vram-reserve-mib 1024 --max-context 131072` and without `--kv-grow` started when about 7,600 MiB were available and not when about 7,300 MiB were (`no VRAM is left for the expert cache: it needs at least 325 slots (468 MiB), about 555 MiB more than this card has free`). The default config (with `--kv-grow`) starts in both cases, but its KV cache then grows into the free VRAM, and I saw the engine exit on the first long request when less than about 1 GiB was free at that moment (separate issue).

## The table (RTX 3060 Ti 8 GB, engine 0.1.43.1 and 0.1.44.1)
See `vram-requirements.md`, `vram-requirements-0.1.44.1.md` and `vram-requirements-0.1.44.1-fast.md` in the results folder: for each model and window the lowest available VRAM at which it worked and the highest at which it failed to start, plus the fitted requirement (weights + draft head + reserve + minimum expert cache + KV cache of the window).

Other observations on the same card:
- Prompt speed on 16K word-list prompts was about 420 tok/s only in the `no-kv-grow` config (tiny expert cache, 75 to 118 experts); changing the reserve, the context or removing MTP lost it again. At 32K and above it was 65 to 75 tok/s, and on real code prompts 15 to 65 tok/s. Is the prompt path borrowing expert-cache slots (`prompt loan`) in one case and allocating its own buffers in the other?
- Strata's recommended resident config for the Coder (`--resident-experts --kv int8`) does not start at 131,072 tokens on 8 GB (KV 1931 MiB, short by 1816 MiB).
- The model card says Strata runs these GGUFs from 8 GB of VRAM. That holds for starting and for prompts up to about 120K tokens with the default flags, but the margin is thin.

## Suggestion
A line in `docs/MODELS.md` or `docs/OLDER_GPUS.md` on 8 GB cards (what fits, which flags to avoid, check `nvidia-smi` for the free memory first), and an engine message at startup that names the available VRAM and what the chosen window needs. I wrote a small launcher that does the second part from the free VRAM (`tools/strata_fit_launch.py` in my repository; it shows the window and asks before starting, has a fast mode and an `--allow-kv-grow` mode, and checks windows above the measured range with the engine); I tested it for real: with 7,690 MiB available it computed 217,088 tokens for IQ2_XS in fast mode, the engine refused (about 700 MiB short), it shrank to 131,072 and started. Windows above 131,072 are extrapolated: IQ2_XS in fast mode starts at 163,840 tokens with 7,390 MiB or more available and not at 196,608 even with 7,590 MiB. Happy to share it.
