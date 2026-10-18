# Strata 8 GB benchmark: what was discarded and why

Runs that were thrown away, so nobody wonders why a number is missing. Everything here was measured on one machine
(RTX 3060 Ti 8 GB, 32 GB RAM); see `strata-benchmarks.md` for the hardware.

| When (2026-10-13) | What | Why it was discarded |
| --- | --- | --- |
| 11:41 to 12:27 | IQ2_XS 128K+64K generation run | A second job started a Strata benchmark on the same port at 11:43. Windows lets two servers listen on one port, so requests of the two jobs were mixed. |
| 11:43 to 12:30 | Coder resident-config soak and standard suite | Same overlap: they attached to the server of the 128K+64K run instead of starting their own. |
| 12:28 to 14:51 | Coder soak, Coder standard suite, Coder 128K needle, IQ2_XS 128K+64K generation (second try), IQ2_XS wide TS project | A queue that had been "stopped" kept running and used port 8080 at the same time. Results could have come from either model. All were re-run alone later. |
| before 11:23 | `no-mtp`, `combo`, `combo-no-mtp` (first attempts) | Defined wrongly (`--spec` was removed too, which a native pack refuses) or impossible (`--kv k8v4` without `--kv-grow` leaves no VRAM for the expert cache). Fixed or dropped; the failures are real and are listed in the main report. |
| 2026-10-14 01:29 | IQ2_XS wide TS project run on `no-kv-grow` (partial, 22 responses) | Windows Update restarted the PC mid-run. After the restart that setup no longer started under the normal desktop GPU load, so the comparison was redone from scratch on the setup that does start (`baseline`). |

What changed afterwards: every tool that starts a server now refuses a busy port, takes a lock so only one GPU job runs,
checks that the server answering is the model it configured (name and context), and records the GPU memory the desktop
was using before the start.

## 2026-10-17/18: coding-test grading corrected (not a discarded run, a regrade)
- The first scorer applied the model's diff with a strict `git apply` and gave 3 of 4 points to a working fix in another file than the injected one. 15 of 67 failed answers were fixes with slightly wrong context lines (indentation, a dropped line). The scorer now also tries `--ignore-whitespace` and the changed lines alone, and a fix that makes the whole test suite pass counts as solved. Old results are kept in `results-strict/` next to each run.
- Test environment: the tests ran against the dependencies folder of a live repository; when it was reinstalled at 23:22 on 17 Oct without one package, every test run after that failed on a missing import. The affected results (the IQ3_XXS hard-bug set and a re-grade) were graded again against a frozen install built offline from the snapshot's own lock file.
- IQ3_XXS fast mode at 131,072 and at 106,496 tokens did not run: the available VRAM at the start (7,319 and 7,230 MiB) was below what the launcher's model says they need (7,523 and 7,319 MiB).
