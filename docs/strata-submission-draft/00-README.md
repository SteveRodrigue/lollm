# Strata submission drafts (NOT PUBLISHED)

## TL;DR
Four drafts for the Strata project, written for you to post yourself (nothing was posted). Suggested order: (1) the 8 GB available-VRAM table (03), (2) the engine-exit bug report (02), (3) the head-alias crash bug report (04), (4) the benchmark pull request (01), which can link to the first three. Updated 18 Oct for engine 0.1.44.1, IQ3_XXS, the fast mode and the corrected coding-test grading. Everything is scanned for private data; the results folder to attach is built by `tools/prepare_pr_folder.py` into `docs/strata-submission-draft/pr-folder/`. Re-run it after any new result.


Nothing here has been posted anywhere. Posting needs the owner's approval, the owner's GitHub account, and a read-through for anything private.

| File | What it is | Where it would go |
| --- | --- | --- |
| `01-pr-description.md` | Pull request text for a community benchmark folder | Niko1221/Strata, PR adding `bench/results/2026-10-1x-community-rtx-3060-ti-8gb/` |
| `02-issue-coder-needle-crash.md` | Bug report: engine exits with code 1 on a long prompt | Niko1221/Strata, issue (bug report template) |
| `03-issue-8gb-vram-fit.md` | Note on the 8 GB VRAM margin: which setups start depends on the available VRAM | Niko1221/Strata, issue or a comment on the 8 GB discussion |
| `04-issue-head-alias-crash.md` | Bug report: `--prefill-head-alias` crashes the engine (access violation) on real long prompts with `--kv-grow` on; fast and stable without it | Niko1221/Strata, issue (bug report template) |

Data to attach (already redacted by Strata's own tool, scanned with `tools/scan_private.py`): `docs/strata-benchmarks.md`, `docs/strata-benchmarks-data/`, `docs/strata-benchmarks-coder-mirror*`, `docs/ts-project-comparison*.md`, `docs/vram-requirements*.md`, `docs/strata-benchmark-changelog.md`. The TS project project's source, file names and bug descriptions are not part of any of it.
