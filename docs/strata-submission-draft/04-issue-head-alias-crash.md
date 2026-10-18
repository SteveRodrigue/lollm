# `--prefill-head-alias` crashes the engine (access violation) on real long prompts when `--kv-grow` is on; fast and stable without it

**TL;DR**
On an 8 GB RTX 3060 Ti (Windows 11, engine 0.1.44.1), IQ2_XS with `--prefill-head-alias --short-read 0` and `--kv-grow` on exits with code 3221225477 (0xC0000005) about 20K tokens into every real 55 to 60K-token coding prompt: 9 of 9 attempts (3 prompts x 3 retries), 772 MiB of VRAM free at the request start. The same prompts with `--kv-grow` off (window 65,536) ran without any exit, and ingested at 81 to 83 tok/s against 53 tok/s with the flag off and 28 to 45 tok/s in the default setup. The 16K synthetic benchmark ran fine with `--kv-grow` on. Request: refuse the combination with a clear message, or fix the crash; and a note in `docs/PREFILL_HEAD_ALIAS.md` that it should be used without `--kv-grow` on 8 GB cards.

## What happened
Config: IQ2_XS pack, `--spec 4 --mtp`, `--kv q4_0 --kv-grow`, `--vram-reserve-mib 1024`, `--max-context 131072`, `--mmap-experts`, plus `--short-read 0 --prefill-head-alias` (the engine refuses the flag unless `--short-read` is 0). Requests: real TypeScript coding prompts of 54.6K, 57.1K and 60.0K tokens through `/v1/chat/completions` (thinking on). Every attempt: `the engine stopped unexpectedly (exit code 3221225477)` at about 20,000 tokens read (about 250 s), last log line `only 772 MiB of VRAM free at the start of this request ... Add --vram-reserve-mib 1280`; Strata restarts the engine and the next attempt crashes at the same place.

## Comparison on the same three prompts (one run each, window 65,536, `--kv-grow` off unless noted)
| Setup | Ingest (tok/s) | Wall time | Engine exits |
| --- | ---: | ---: | ---: |
| default (`--kv-grow` on, window 131,072; earlier run) | 28 to 45 | 1,000 to 1,800 s | 0 |
| `--kv-grow` off, no head alias | 53 | 1,090 to 1,200 s | 0 |
| `--kv-grow` off, head alias + `--short-read 0` | 81 to 83 | 700 to 980 s | 0 |
| `--kv-grow` on, head alias + `--short-read 0` | n/a | n/a | 9 of 9 attempts |

On the standard 16K synthetic suite (IQ2_XS, `--kv-grow` on) the flag gave 79 tok/s at 16K against 62 and 42 for two baseline runs, and about +1 s time to first token on short chats, as documented.

## Strata version, GPU, OS
Engine 0.1.44.1 (release), source 296b59d2, RTX 3060 Ti 8 GB, driver 616.92, Windows 11, 32 GB RAM, about 7,300 MiB of VRAM available at the start.

## Engine log
Attach the engine log (redacted by the benchmark tool).
