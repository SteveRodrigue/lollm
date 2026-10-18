**TL;DR**
- Adds the first 8 GB NVIDIA community report: RTX 3060 Ti, Ryzen 7 5800X3D, 32 GB RAM, Windows 11, engine 0.1.43.1 and 0.1.44.1, models IQ2_XS, Coder IQ1_M and IQ3_XXS.
- Real coding task (8 bugs injected into a TypeScript project, prompts of 16K, 64K and about 120K tokens, fully fixed = the whole test suite passes): IQ3_XXS fixed 29 of 32 attempts (91%), IQ2_XS 23 of 32, Coder 23 of 32. All three solved the ~120K-token prompts (IQ2_XS 8 of 8, Coder 8 of 8). Per fix the Coder is the fastest (64K: about 15 min against 31 for IQ2_XS and 47 for IQ3_XXS).
- 8 GB finding: what starts depends on the AVAILABLE (free) VRAM, not on what uses the rest. Measured table in the folder (`vram-requirements*.md`), e.g. IQ2_XS with a 131,072 window needs about 7,500 MiB available with the KV cache reserved up front.
- Engine 0.1.44.1 `--prefill-head-alias --short-read 0` with `--kv-grow` off ("fast mode") ingested real 55 to 60K-token prompts at 80 to 85 tok/s against 28 to 45 in the default setup (1.6 to 2.1x less time per 64K prompt on all three models), with no engine exit in over 100 requests and no measurable loss of accuracy at equal output room. With `--kv-grow` on the flag crashed the engine on every real long prompt (separate issue).
- Caveats: one machine, few repeats (1 to 3 per prompt), speed drifts up to 35 to 50% between runs; RAM is the limit (31.9 GiB in use in every run). Results only, no engine changes. A changelog lists runs that were discarded and why, and a grading correction made along the way.

## Title
Community benchmark: RTX 3060 Ti 8 GB, Ryzen 7 5800X3D, 32 GB DDR4, Windows 11 (engine 0.1.43.1 and 0.1.44.1, IQ2_XS, Coder IQ1_M and IQ3_XXS)

Issue: n/a (results only)

## Summary
First 8 GB NVIDIA report for the community list. One desktop, Strata from the official Windows releases (0.1.43.1, commit a0116b27, then 0.1.44.1), models Qwen3.8-Flash-Next IQ2_XS, the Coder IQ1_M and Strata's IQ3_XXS, `--spec 4 --mtp`, `--kv q4_0`, `--vram-reserve-mib 1024`, `--mmap-experts`. Speed suite (`tools/strata_bench.py`, 3 runs, medians and ranges), a settings sweep, 32K/128K recall, a soak test, an available-VRAM sweep (a ballast holds part of the VRAM), and a coding test (bugs injected into a frozen snapshot of a TypeScript project; the model answers with a diff, the diff is applied and the project's test suite decides).

## What changed
Adds only a results folder: `bench/results/<date>-community-rtx-3060-ti-8gb/` with `README.md` (findings first; hardware including measured RAM, VRAM and PCIe bandwidth), per-variant `results.json`, the available-VRAM tables, the coding-test comparison tables (with the time per request and the minutes per fix) and a changelog of runs that were discarded and why.

## Extra Notes
- Hardware measured on the machine: DDR4-3600 (4 x 8 GB), about 34 GB/s read; VRAM about 410 GB/s; PCIe 3.0 x16 about 13 GB/s; NVMe about 3.3 GB/s; Resizable BAR on.
- Coding test, default setup (`--kv-grow` on, 131,072 window), 16K and 64K, two runs per bug, full fixes out of 32: IQ3_XXS 29, IQ2_XS 23, Coder 23. IQ3_XXS is the only one that solves bug 2 reliably; none solves bug 4 reliably. Median time per 64K request: IQ2_XS 22 min, IQ3_XXS 43 min, Coder 8 min.
- Fast mode (`--prefill-head-alias --short-read 0`, no `--kv-grow`), same prompts: median time per 64K prompt 823 s (IQ2_XS; default 1,337 s), 1,228 s (IQ3_XXS; 2,554 s), 260 s (Coder; 491 s). With a window that leaves enough room for the answer (98,304) the 64K fixes were IQ2_XS 7/8, IQ3_XXS 7/8, Coder 6/8, in line with the default setup. With a 65,536 window the answer can run out of room after a 57K prompt (6 to 10K tokens left); do not compare accuracy across windows.
- Grading: a patch is applied strictly, then ignoring whitespace, then by its changed lines; a fix that makes the whole test suite pass counts, whatever it looks like. The first strict grading scored correct fixes with slightly wrong context lines as failures; both results are kept (`results-strict/` next to each run) and the correction is listed in the findings (item 0).
- Available VRAM: about 7,600 to 7,700 MiB of the 8,192 are available on an idle desktop. A launcher (`tools/strata_fit_launch.py` in my repository) computes the largest window from the available VRAM, shows it and asks before starting; happy to share it.
- Limits: one machine, few repeats, speed suites use synthetic prompts, a few runs were discarded after overlapping jobs (listed in the changelog).
- Related issues (separate): the engine exit on a long prompt with `--kv-grow` on (draft 02), the 8 GB VRAM margin (draft 03), and the head-alias crash with `--kv-grow` on (draft 04).
