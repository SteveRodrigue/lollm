**TL;DR**
The engine exits (code 1, HTTP 503) on the first long request after it starts, when less than about 1 GiB of VRAM is free at that moment (328 to 620 MiB in my logs). It happened in the needle test (32K, every time) and in real 119K-token coding prompts (about half of the starts). Reserves 1024 to 1400 and a 64K window do not prevent it; 1600+ does not start. Strata restarts the engine and a retry gets through. On engine 0.1.44.1 with 7,240 to 7,470 MiB available: cold start 1 of 9 ok, with a short warm-up request first 3 of 9 ok, reserve 1200/1300 0 of 3 each; with `--kv-grow` off (KV reserved up front) no exit in any of about 25 cells that started. Request: a clearer startup check or an automatic retry, or guidance for 8 GB cards (suggestion: do not grow the KV cache into the last 1 GiB of free VRAM).


## What happened
`tools/needle_bench.py --lengths 32k,128k --depths 50` makes the engine exit with code 1 about 22K tokens into the 32K prompt, every time. Server log: `strata serve: WARNING: only 328 MiB of VRAM free at the start of this request (below 1024 MiB) ... Add --vram-reserve-mib 2112`, then `the engine stopped unexpectedly (exit code 1)`, HTTP 503 to the client.

Setup: Coder IQ1_M, `--spec 4 --mtp`, `--kv q4_0 --kv-grow`, `--mmap-experts`, `--max-context 131072`. Same result with `--vram-reserve-mib` 1024 (462 MiB free at the request start) and 1400 (328 MiB free), with `--max-context 65536`, and when a short request is sent first. `--vram-reserve-mib 1600` and above does not start (expert cache gets 0 slots, short by 832 MiB).

It is not specific to the needle prompt: the same exit happened once in a real coding run, on the first request after a fresh server start (119K-token TypeScript prompt through `/v1/chat/completions`, thinking on): `only 620 MiB of VRAM free at the start of this request`, exit code 1, HTTP 503; Strata restarted the engine; asking for the same prompt again crashed it a second time (514 and 555 MiB free) and succeeded on the third try. The first long request after an engine start crashed in about half of the starts I observed. Other real prompts on the same setup (55K, 95K and 117 to 119K tokens, about 40 requests) ran without an exit, so it looks like an intermittent engine exit when less than about 1 GiB of VRAM is free at the start of a long request, which depends on how much VRAM is available at that moment.

Expected: the 32K needle request completes, or the engine reports that it cannot.

Repro: start the Coder config above on an 8 GB card with about 7,600 MiB of VRAM available at the start, then `python tools/needle_bench.py --lengths 32k --depths 50`.

## Strata version, GPU, OS
Engine 0.1.43.1 (release), commit a0116b27, and 0.1.44.1 (probe in the TL;DR), RTX 3060 Ti 8 GB, driver 616.92, Windows 11, 32 GB RAM.

## Engine log
Attach the engine log of the failing run (redacted by the benchmark tool: `reports/.../server.log`).
