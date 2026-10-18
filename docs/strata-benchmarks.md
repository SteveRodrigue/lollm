# Strata on an 8 GB GPU: setting-by-setting benchmark

Measured 2026-10-12 on a consumer desktop with an **NVIDIA GeForce RTX 3060 Ti** (8 GiB VRAM) and 31.9 GiB RAM. Strata project 0.1.43.1, commit `a0116b27`, engine 0.1.43.1. Model: qwen3.8-flash-next-iq2_xs (IQ2_XS), 131072-token context. Each variant changes one thing from the baseline config; 3 run(s) per test, medians with ranges. Speed only: no output-quality check was run.

## Findings (draft; numbers are final unless marked TODO)

0. **Grading correction (17 Oct, applies to every coding-test number below).** The first scorer applied the model's patch with a strict `git apply`, which fails when a model retypes the unchanged context lines with a slightly wrong indentation or drops one, even though the changed line is right; and it gave a fix that works only 3 of 4 points if it touched another file than the injected one. Re-grading all answers that had scored below the maximum, with a tolerant apply (strict, then ignoring whitespace, then the changed lines alone, located by content) and "a fix that makes the whole test suite pass counts as solved", moved 15 of 67 failed answers to full marks (of the other 52, 48 had no patch at all and 4 had a patch that still did not apply). Full fixes at 16K + 64K, default mode: **IQ2_XS 23 of 32 (72%, was 19), IQ3_XXS 29 of 32 (91%), Coder 23 of 32 (72%, was 18)**; fast mode (65,536 window): IQ2_XS 14 of 24, IQ3_XXS 20 of 32, Coder 25 of 32; fast mode, 64K, 98,304 window: IQ2_XS 7/8, IQ3_XXS 7/8, Coder 6/8. The old strict results are kept next to each run (`results-strict/`). Items 7, 7b, 12 and 13 below use the corrected numbers; the 120K-token runs (item 8) were re-graded too (Coder 7 of 8 became 8 of 8). Bug 8, which looked unfixable, was solved in every setup once the grading was fixed: the models found the exact line and only the diff's context was off.


Hardware: RTX 3060 Ti 8 GB (PCIe 3.0 x16), Ryzen 7 5800X3D, 32 GB DDR4-3600, Windows 11, Strata engine 0.1.43.1, model
Qwen3.8-Flash-Next IQ2_XS unless stated. Everything below was measured on this one machine with the normal desktop running; wherever VRAM matters the figure given is the AVAILABLE (free) VRAM when Strata starts.

1. **It runs on 8 GB, but RAM is the real limit.** About 31 tok/s chat decode, with system RAM at 31.9 GiB in use in every
   run (the experts are memory-mapped from the SSD). Capping RAM near 30 GiB (`--resident-budget-gib 20`) holds peak use at 30.7 GiB but
   cuts decode by about 75%.
2. **Prompt speed is not one number.** Short synthetic prompts (4K to 16K tokens) reached about 420 tok/s only with `--kv-grow`
   removed (`no-kv-grow`); in the normal config they run at about 45. That fast mode is fragile: adding almost any other
   change (a smaller reserve, a smaller context, no MTP) lost it again, it did not hold at 32K and above (65 to 75 tok/s), and real code
   prompts ingested at 15 to 50 tok/s. A 128K prompt takes about 32 minutes (IQ2_XS) to ingest.
3. **`no-kv-grow` needs a lot of available VRAM.** Overnight it started; later it did not (555 MiB short for the expert cache) because less VRAM was available. A setup that only just fits depends on
   how much VRAM is available when it starts; what uses the rest does not matter. The default config (`--kv-grow` on) starts with less available VRAM, but its KV cache then grows into whatever is left (see item 6).
4. **Leave the defaults alone for these:** turning off the route-tail skip cut decode by 58%; removing the draft layer (`no-mtp`)
   cut decode by 29% (prompts got faster, 104 vs 42 tok/s at 16K, but still far from the fast mode).
5. **Long context works, with limits.** A hidden code word was found at 32K and 128K. A 160K window (128K prompt plus
   about 31K of output) ran at 26 down to 19 tok/s decode. At a 192K window the card is full and decode fell to about 5.8 tok/s
   and the 128K prompt took 55 minutes. On this card the practical ceiling is about 160K.
6. **Coder IQ1_M** (the pruned coding model, 256 of 512 experts) fits RAM better and handles real long code prompts well on this card with the
   normal flags (`--kv-grow` on, reserve 1024 MiB): a 10 minute soak passed (178 requests, no failures), and two real ~95K-token prompts (a recall
   test and a bug fix) both scored full marks in 7 to 11 minutes each, ingesting at about 225 tok/s against about 45 to 50 tok/s for IQ2_XS on the
   same prompts (IQ2_XS needed 30 to 37 minutes). Chat decode is lower (17 tok/s against about 31). Two limits: Strata's own recommended
   resident config does not start at 131,072 tokens on 8 GB, and Strata's needle-in-a-haystack tool crashed the engine
   (exit code 1, 'only 328 to 462 MiB of VRAM free at the start of the request') at about 22K tokens into a 32K prompt with reserves 1024 and 1400, with a 64K
   or 128K window and with a warm-up request first, while most real code prompts ran fine; the same exit then also hit one 119K-token real prompt (the first request after a server start, 620 MiB of VRAM free), so it is an intermittent engine exit when less than about 1 GiB of VRAM is free at the start of a long request (it hit the first long request after an engine start in about half of the starts), not something specific to the needle text; the one prompt that crashed twice in a row succeeded on the third try. Reserves of 1600 and up do not start. Strata restarts the engine by itself, so a client that retries after a 503 gets through. On engine 0.1.44.1 a probe (32K needle as the first long request after a fresh start, `--kv-grow` on, 7,240 to 7,470 MiB available) ended in an engine exit in 8 of 9 cold starts; a short warm-up request first did not reliably help (3 of 9 ok), and reserves of 1200 and 1300 MiB made it worse (0 of 3 each). With `--kv-grow` off (KV cache reserved up front) no exit occurred in any cell that started.
7. **Real coding tasks (a TypeScript project, bugs injected into a frozen snapshot, 3 to 8 bugs):** IQ2_XS fixed two of three bugs
   at 16K, 64K and about 100K tokens of prompt and found every constant in a recall test; the third bug used the whole 16K output
   budget on reasoning and produced no patch. On the same 8 bugs and settings (`--kv-grow` on, 32K output budget, two repeats per prompt) IQ2_XS fully fixed 11 of 16 attempts at 16K and 12 of 16 at 64K
   (23 of 32), the Coder 12 of 16 and 11 of 16 (23 of 32): no difference in correctness (see `ts-project-comparison-3way.md`; with the corrected grading, item 0). Both models
   produced no usable patch in some attempts (9 of 32 for IQ2_XS, 7 of 32 for the Coder) because the 32K output budget was used up by reasoning; those are the only failures left on bugs 1, 6 and 8, while bugs 2, 4 and 5 are the hard ones (IQ2_XS fixed bug 2 in 0 of 4 attempts, bug 5 in 1 of 4). On the ~95K-token prompts both scored full marks, but the Coder took 7 to 11 minutes and IQ2_XS 24 to 27 minutes.

7b. **IQ3_XXS** (Strata's own 3-bit file, same `baseline` setup, 32K output budget) was clearly the most accurate on the same 8 bugs: **14 of 16** attempts fully fixed at 16K and **15 of 16** at 64K (two runs per bug; the 64K repeat ran on engine 0.1.44.1: first run 8/8, second 7/8), 29 of 32 in all, against IQ2_XS 23/32 (11/16 and 12/16) and the Coder 23/32 (12/16 and 11/16; corrected grading, item 0), and it solved the recall test every time. Only 2 of its 32 attempts ended without a patch (IQ2_XS 9, Coder 7).
    The price is speed: prompt ingestion about 22 to 31 tok/s (64K prompts took 33 to 48 minutes, against about 25 for IQ2_XS and 9 to 15 for the Coder) and decode about 16 to 23 tok/s. Its available-VRAM requirement has not been measured yet.
8. **At about 120K tokens of real code (116 to 119K real tokens in a 131,072 window), IQ2_XS solved all 8 attempts** (three bug fixes and a recall test, two runs each, `--kv-grow` on), **the Coder 8 of 8**
   (with the corrected grading, item 0: one patch had scored 0 because its context lines did not match the file, the fix itself was right). The Coder needed 11 to 18 minutes per prompt (ingest about 165 tok/s), IQ2_XS 34 to 38 minutes (about 56 tok/s).
   One of the Coder's requests needed three tries because of the engine exit described in item 6.

9. **Strata's `--calibrate` found nothing worth keeping.** For IQ2_XS it suggested `--spec-min-p 0.7` (+6% in its own sweep) and `--pcie-frac 0.35`; run through the full suite
   (three runs each plus a baseline re-run) they were no better than the baseline re-run (chat decode 31 to 33 against 30.5 tok/s). For the Coder it kept every default (all gains under 3%).
10. **Run-to-run drift is large.** Inside one session the same baseline setup went from 38.7 to 30.5 tok/s chat decode and from 22.3 to 11.3 tok/s agent decode; the first run
    after an idle period was the fastest. Compare setups only inside one session, re-run a baseline last, and read the ranges.

11. **How much AVAILABLE VRAM each setup needs** (the VRAM that is free when Strata starts; measured with a ballast, KV cache reserved up front with `--kv-grow` off, one 24K-token prompt per cell; full table in `vram-requirements.md`).
    IQ2_XS: a 131,072-token window works from about 7,500 MiB available, 65,536 from about 6,900 MiB, 32,768 from about 6,700 MiB. Coder IQ1_M: 32,768 from about 7,300 MiB, and it did not start at 65,536 or 131,072 even with 7,500 MiB available.
    (This card has 8,192 MiB in total, and about 7,600 to 7,700 MiB are available when nothing else is using it.) No engine exit happened in any cell that started, so the exits on long requests seen with `--kv-grow` on come from the KV cache growing into the free VRAM.
    A launcher that computes the window from the available VRAM (`tools/strata_fit_launch.py`, constants in `configs/vram-model.json` fitted to this table) shows the available VRAM each window needs before it starts
    and asks for confirmation; on a 12 GB card both models reach the model's 262,144 maximum.
    IQ3_XXS (engine 0.1.44.1, same method): 32,768 works from about 6,940 MiB available, 65,536 from about 7,370 MiB, and 131,072 did not start even with 7,500 MiB available (the fitted requirement is about 7,890 MiB); see `vram-requirements-0.1.44.1.md` (engine 0.1.43.1: `vram-requirements.md`; the two engines agree within one grid step).

12. **A faster mode for 8 GB cards on engine 0.1.44.1: `--prefill-head-alias --short-read 0` with `--kv-grow` off and a 65,536-token window.** On IQ2_XS it ingested real 55 to 60K-token prompts at 80 to 83 tok/s against 28 to 45 in the default setup (a 64K prompt took 12 to 16 minutes instead of 17 to 30), ran all 27 wide-TS project prompts without an engine exit, and fixed 14 of 24 bugs against 23 of 32 in the default setup (corrected grading; no meaningful difference in accuracy; small samples). Dropping `--kv-grow` alone gave 53 tok/s. With `--kv-grow` on, the flag crashed the engine (access violation, exit code 3221225477) in 9 of 9 attempts on the same prompts.

13. **The fast mode on all three models** (wide TS project set; 16K x2 and 64K; zero engine exits): median wall time per 64K prompt 823 s for IQ2_XS (default mode 1,337 s), 1,228 s for IQ3_XXS (2,554 s) and 260 s for the Coder (491 s), so 1.6 to 2.1 times faster. The accuracy at 64K in this first fast-mode run is **not comparable** with the default mode: it used a 65,536-token window, which leaves only 6 to 10K tokens of output room after a 57K prompt, and the models that reason longest ran out (IQ3_XXS: 7 of 16 attempts without any patch, against 0 of 16 in the default mode; the Coder 4 of 16). Re-run with a 98,304 window (one attempt per bug, `docs/ts-project-comparison-fast-mode-98k.md`): full fixes at 64K IQ2_XS 7/8, IQ3_XXS 7/8, Coder 6/8 (65,536 window: 4/8, 9/16, 12/16; default mode, 131,072 window: 12/16, 15/16, 11/16 over two runs), so with enough output room fast mode is within the noise of the default mode for IQ2_XS and the Coder and perhaps a little lower for IQ3_XXS (one attempt per bug, not conclusive). IQ3_XXS fast mode at 131,072 did not fit (7,523 MiB available needed, 7,319 available). At 16K, where the room is ample, the fast mode fixed 10 of 16 (IQ2_XS), 11 of 16 (IQ3_XXS) and 13 of 16 (Coder), against 11, 14 and 12 in the default mode. Over all attempts (16K + 64K, 65,536 window) fast mode fixed IQ2_XS 14 of 24, IQ3_XXS 20 of 32, Coder 25 of 32, against 23, 29 and 23 of 32 in the default mode: IQ3_XXS stays ahead in the default mode, the Coder does as well in the fast mode as in the default one. **Time per request (median / total over all attempts):** at 64K, default mode IQ2_XS 22.3 min / 416 min, IQ3_XXS 42.6 / 779, Coder 8.2 / 175; fast mode (65,536 window) 13.7 / 125 (9 requests), 20.2 / 342, 4.4 / 66; fast mode with the 98,304 window 12.1, 25.4 and 4.7 min per request. At 16K: default 5.9, 9.7, 5.1 min; fast 3.8, 5.6, 3.0 min. The comparison tables (`ts-project-comparison*.md`) now list the time per request next to the speed. A model that is more accurate but slower pays for it: IQ3_XXS needs about 2x the time of IQ2_XS and 5x the Coder's for each 64K fix. **Minutes per full fix** (total time of all attempts / attempts fully fixed; a better measure than accuracy alone, and the one that decides when models fix the same bugs): at 64K default mode IQ2_XS 31.4, IQ3_XXS 46.9, Coder 14.9; fast mode (65,536 window) 28.3, 34.7 and 5.2; fast mode (98,304 window) 17.7, 38.2 and 9.6. At 16K default 12.1, 14.8, 9.8; fast 11.7, 15.6, 5.9. On the bugs that every attempt of every model fixed, the Coder was the fastest on almost all (64K, default mode: 6 to 10 minutes against 20 for IQ2_XS and 39 to 41 for IQ3_XXS). So IQ3_XXS buys its extra fixes (bugs 2, 4 and 5 where the others fail) with about 4x the time on the bugs all three solve.

14. **The three hard bugs (2, 4 and 5) at 64K, fast mode, 98,304 window, three attempts each** (the first run plus two more): full fixes out of 3: **Coder** bug 2 1, bug 4 1, bug 5 3; **IQ2_XS** bug 2 0 (all three attempts used the whole 32K budget without a patch), bug 4 1, bug 5 3; **IQ3_XXS** bug 2 3, bug 4 0 (2 attempts without a patch), bug 5 3. So IQ3_XXS is the only model that solved bug 2 reliably and none solves bug 4 reliably; the extra time is spent on exactly these. Median minutes per request: Coder 7.6 to 11.5, IQ2_XS 17.5 to 19.0, IQ3_XXS 26 to 38. IQ3_XXS fast mode at a 106,496 window did not fit the VRAM available at the time (7,319 MiB needed, 7,230 available); 98,304 is the largest window run for it.

15. **Grading environment (18 Oct).** The tests ran against the `node_modules` of the live TS project repository; when that folder was reinstalled at 23:22 on 17 Oct without one package (which the snapshot still needs), every test run after it failed on a missing import, whatever the model wrote (a perfect fix scored 2/4). The affected results (the IQ3_XXS hard-bug set and part of the later re-grade) were graded again against a frozen install built offline from the snapshot's own lock file (`logs/ts-project-snapshots/<snapshot>/node_modules_frozen/`); the results above are the re-graded ones. Lesson: freeze the dependencies with the snapshot.

Caveats: one machine, few repeats, speed suites use synthetic prompts, results drift by up to 50% between runs on the same
setup (prompt speed), and several runs were discarded for operator errors (see `strata-benchmark-changelog.md`).

## Hardware

| Component | Details |
| --- | --- |
| CPU | AMD Ryzen 7 5800X3D 8-Core Processor (8 cores / 16 threads, base 3401 MHz, L3 96.0 MiB) |
| RAM | 31.9 GiB total: 4 module(s): 8 GiB DDR4-3600, 8 GiB DDR4-3600, 8 GiB DDR4-3600, 8 GiB DDR4-3600; rated 3600 MT/s, running 3600 MT/s |
| RAM bandwidth (measured) | read 35.6 GB/s, copy 38.9 GB/s (read+write traffic), 8 threads; theoretical 57.6 GB/s (3600 MT/s x 8 B x 2 channels (assumed)) |
| GPU | NVIDIA GeForce RTX 3060 Ti: 8192 MiB VRAM, 38 SMs, L2 3.0 MiB, 256-bit bus, memory clock up to 7001 MHz, SM clock up to 2100 MHz |
| VRAM bandwidth (measured) | 397.8 GB/s device-to-device copy (read+write traffic) |
| GPU power limit | 240.00 W (default 240.00 W, max 325.00 W) |
| PCIe link | max Gen3 x16; idle Gen1 x16; under load Gen3 x16 |
| PCIe bandwidth (measured) | host to GPU 13.05 GB/s pinned, 11.98 GB/s pageable; GPU to host 13.18 GB/s pinned, 12.16 GB/s pageable |
| Resizable BAR | BAR1 8192 MiB (enabled (BAR >= VRAM)) |
| GPU driver | 616.92 |
| Model drive | WD_BLACK SN850X 1000GB (NVMe SSD, 932 GiB); sequential read 3.34 GB/s (unbuffered, 2 GiB) |
| OS | Windows 11 (10.0.26300); power plan: Balanced |

Bandwidths are measured with `tools/strata_hwinfo.py` (RAM: 8 threads numpy read/copy; VRAM: `cudaMemcpy` device-to-device, counting read+write traffic; PCIe: 256 MiB `cudaMemcpy`, link read from `nvidia-smi` while copying; disk: unbuffered sequential read from the middle of the model file). Background load was not controlled.

## Results

Decode = tokens generated per second; prompt = prompt tokens ingested per second on a fresh (uncached) prompt; TTFT = time to first token. Peak RAM = highest system memory in use (total minus available, file cache excluded) while the variant ran. Percentages are relative to the first baseline run.

| Variant | Chat decode tok/s | Chat TTFT s | 4K prompt tok/s | 16K prompt tok/s | 16K TTFT s | Agent decode tok/s | Agent TTFT s | Agent cache hit % | Peak RAM in use GiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 32.7 (21.0-40.0) | 1.12 (0.99-3.07) | 51 (50-57) | 42 (41-42) | 384.0 (378.6-388.0) | 16.1 (5.5-23.6) | 71.83 (32.67-83.62) | 68.8 | 31.9 |
| no-kv-grow | 31.4 (15.9-40.9) (-4.0%) | 1.07 (0.94-1.66) | 416 (240-419) (+717.3%) | 419 (411-426) (+902.2%) | 38.4 (37.7-39.1) | 19.8 (3.6-29.3) (+23.0%) | 37.51 (13.65-52.44) | 68.7 | 31.9 |
| kv-k8v4 | 37.5 (19.1-42.6) (+14.7%) | 1.03 (0.89-1.72) | 54 (53-55) (+6.3%) | 42 (42-42) (+1.0%) | 380.2 (378.0-382.4) | 19.4 (9.4-30.2) (+20.5%) | 67.42 (33.14-81.34) | 68.7 | 31.8 |
| no-mtp | 23.3 (12.7-35.2) (-28.7%) | 1.58 (1.02-2.81) | 78 (74-86) (+52.3%) | 104 (96-105) (+150.0%) | 153.8 (152.5-167.1) | 14.8 (9.1-23.3) (-8.1%) | 29.34 (19.47-55.71) | 68.9 | 31.9 |
| reserve-700 | 29.0 (17.2-37.2) (-11.3%) | 1.13 (0.86-1.98) | 82 (76-88) (+61.3%) | 90 (84-91) (+116.0%) | 177.9 (176.9-190.6) | 18.1 (7.3-26.3) (+12.4%) | 37.88 (22.38-55.47) | 68.6 | 31.9 |
| ctx-32k | 33.5 (17.3-44.9) (+2.4%) | 1.13 (0.88-1.90) | 76 (70-78) (+48.7%) | 68 (68-69) (+63.2%) | 235.4 (232.8-235.9) | 11.5 (3.0-14.0) (-28.6%) | 49.93 (24.86-62.03) | 68.6 | 31.9 |
| tail-skip-off | 13.6 (10.4-17.5) (-58.4%) | 2.52 (2.01-3.84) | 46 (46-52) (-8.6%) | 41 (40-42) (-1.0%) | 387.6 (380.8-397.3) | 11.8 (8.7-16.5) (-26.7%) | 66.88 (33.33-90.64) | 68.6 | 31.9 |
| ram-cap | 8.1 (7.0-8.9) (-75.2%) | 4.10 (3.85-4.39) | 144 (144-144) (+182.9%) | 132 (131-132) (+214.6%) | 122.3 (122.2-122.5) | 8.4 (7.4-9.3) (-47.8%) | 22.90 (13.52-29.29) | 68.8 | 30.7 |
| nkg-reserve-700 | 21.5 (14.4-36.9) (-34.3%) | 1.40 (1.19-2.24) | 51 (49-53) (+0.4%) | 40 (39-41) (-3.6%) | 398.4 (387.7-412.7) | 12.8 (6.3-24.7) (-20.5%) | 69.56 (33.21-94.45) | 68.8 | 31.9 |
| nkg-no-mtp | 30.1 (14.7-33.4) (-8.0%) | 1.33 (1.07-2.56) | 77 (72-78) (+50.7%) | 71 (69-71) (+68.9%) | 227.5 (226.8-233.6) | 11.3 (8.8-13.6) (-29.8%) | 47.95 (23.28-52.89) | 68.9 | 31.9 |
| nkg-ctx-64k | 22.1 (17.3-37.8) (-32.4%) | 1.31 (1.01-2.23) | 49 (49-52) (-3.9%) | 51 (50-52) (+22.2%) | 314.4 (306.8-321.9) | 18.2 (13.6-25.0) (+13.0%) | 63.91 (30.08-67.72) | 68.6 | 31.9 |
| nkg-recheck | 26.9 (17.1-38.2) (-17.7%) | 1.40 (1.00-1.90) | 367 (293-381) (+621.8%) | 393 (385-397) (+840.9%) | 40.9 (40.5-41.8) | 18.9 (11.0-24.4) (+17.4%) | 33.86 (13.71-43.60) | 68.8 | 31.9 |
| baseline-recheck | 30.4 (20.4-40.6) (-7.0%) | 1.12 (0.93-1.96) | 79 (73-88) (+54.8%) | 62 (61-63) (+47.8%) | 260.0 (255.5-263.5) | 12.6 (9.2-23.2) (-21.7%) | 50.41 (21.02-61.28) | 68.6 | 31.9 |
| nkg-en | 34.6 (15.1-42.3) (+5.8%) | 1.05 (0.91-1.54) | 273 (233-280) (+437.1%) | 278 (273-279) (+564.6%) | 57.9 (57.6-58.8) | 25.5 (12.7-30.3) (+58.4%) | 40.69 (19.41-61.74) | 68.9 | 31.9 |
| reserve-2048 | 29.1 (15.1-35.2) (-11.0%) | 1.42 (1.09-1.74) | 51 (49-52) (+0.6%) | 41 (41-41) (-1.7%) | 391.1 (388.1-391.7) | 16.1 (8.7-19.8) (+0.0%) | 70.14 (35.70-88.62) | 68.8 | 31.9 |

Drift check: the baseline re-run at the end differs by -7.0% in chat decode and +47.8% in 16K prompt speed; differences smaller than that are noise.

## What each variant changes

- **baseline**: the config as it is now (`--spec 4 --mtp`, `--kv q4_0`, `--kv-grow`, reserve 1024 MiB, 131072 context)
- **no-kv-grow**: without `--kv-grow` (documented as incompatible with the low-RAM/mmap mode)
- **kv-k8v4**: `--kv k8v4` instead of `q4_0` (docs: 23% less KV than 8-bit, better quality than 4-bit)
- **no-mtp**: no `--mtp` (`--spec 4` stays: a native pack requires it): frees the draft layer's 0.7-1 GiB for the expert cache
- **reserve-700**: `--vram-reserve-mib 700` (default-ish) instead of 1024
- **ctx-32k**: `--max-context 32768` instead of 131072
- **tail-skip-off**: `STRATA_ROUTE_TAIL_SKIP=0`: exact routing, no skipped missed experts
- **ram-cap**: RAM capped for a 32 GB PC: `--resident-budget-gib 20`, `STRATA_RESIDENT_HEADROOM_GIB=2`, `STRATA_RESIDENT_PIN=0` (pageable)
- **nkg-reserve-700**: no `--kv-grow` + `--vram-reserve-mib 700`
- **nkg-no-mtp**: no `--kv-grow` + no `--mtp` (`--spec 4` stays)
- **nkg-ctx-64k**: no `--kv-grow` + `--max-context 65536`
- **nkg-recheck**: no `--kv-grow` again, last: drift check for the best setting
- **baseline-recheck**: the baseline again, last (drift check)
- **nkg-en**: no `--kv-grow` + the English draft vocabulary actually applied (`draft_vocab: en`, ~215 MiB less VRAM)
- **reserve-2048**: `--vram-reserve-mib 2048` (hypothesis: more free VRAM for the prompt path, fewer cached experts)

## Launch line and settings of the baseline

```text
strata.exe --pack iq2_xs --native Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 131072 --vram-reserve-mib 1024 --kv q4_0 --kv-grow --mmap-experts
```

Server settings: `model_name=qwen3.8-flash-next-iq2_xs`, `port=8080`, `gpu=0`, `gpus_asked=True`, `open_browser=False`

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
