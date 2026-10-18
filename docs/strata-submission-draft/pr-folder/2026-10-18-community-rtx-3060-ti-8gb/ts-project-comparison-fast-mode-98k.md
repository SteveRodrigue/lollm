# TS project tests: side-by-side

Score per bug test: 4 = the diff applies (strict, ignoring whitespace, or by its changed lines) and the whole test suite passes (a different fix that works counts); below that: 1 = applies, +1 touches the right file, +1 the target test passes. The speed column gives the median decode speed, the prompt size and the median time per request (minutes). `no diff` = the model produced no usable diff (typically its output budget went to reasoning). Recall tests score 1 per correct answer.

| Test | iq2-fast98: score | iq3-fast98: score | coder-fast98: score | iq2-fast98: speed | iq3-fast98: speed | coder-fast98: speed |
| --- | --- | --- | --- | --- | --- | --- |
| bug-1@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 26 tok/s, 55K tokens, 12.0 min | 19 tok/s, 55K tokens, 25.0 min | 36 tok/s, 55K tokens, 3.6 min |
| bug-2@64000 | 0.00/4 (0/1 full, 1 no diff) | 4.00/4 (1/1 full) | 0.00/4 (0/1 full, 1 no diff) | 50 tok/s, 56K tokens, 21.9 min | 17 tok/s, 56K tokens, 48.1 min | 43 tok/s, 56K tokens, 14.8 min |
| bug-3@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 26 tok/s, 60K tokens, 12.1 min | 13 tok/s, 60K tokens, 22.5 min | 33 tok/s, 60K tokens, 2.3 min |
| bug-4@64000 | 4.00/4 (1/1 full) | 0.00/4 (0/1 full, 1 no diff) | 2.00/4 (0/1 full) | 32 tok/s, 58K tokens, 18.8 min | 17 tok/s, 58K tokens, 54.5 min | 36 tok/s, 58K tokens, 7.1 min |
| bug-5@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 36 tok/s, 56K tokens, 18.6 min | 16 tok/s, 56K tokens, 41.9 min | 34 tok/s, 56K tokens, 17.8 min |
| bug-6@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 22 tok/s, 57K tokens, 11.5 min | 14 tok/s, 57K tokens, 27.8 min | 37 tok/s, 57K tokens, 4.8 min |
| bug-7@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 22 tok/s, 58K tokens, 11.9 min | 12 tok/s, 58K tokens, 22.0 min | 38 tok/s, 58K tokens, 2.7 min |
| bug-8@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 34 tok/s, 56K tokens, 17.3 min | 17 tok/s, 56K tokens, 25.4 min | 39 tok/s, 56K tokens, 4.7 min |
| recall@64000 | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 4.00/4 (1/1 full) | 18 tok/s, 57K tokens, 11.3 min | 10 tok/s, 57K tokens, 21.8 min | 33 tok/s, 57K tokens, 2.0 min |

## Share of repeats that fully fixed the bug (bug tests only)

| Size | iq2-fast98 | iq3-fast98 | coder-fast98 |
| --- | --- | --- | --- |
| 64000 | 7/8 | 7/8 | 6/8 |

## Time per request (all tests of a size, minutes)

| Size | iq2-fast98: median / total | iq3-fast98: median / total | coder-fast98: median / total |
| --- | --- | --- | --- |
| 64000 | 12.1 / 136 (9 requests) | 25.4 / 289 (9 requests) | 4.7 / 60 (9 requests) |

## Minutes per full fix (total time of all bug attempts / attempts that fully fixed the bug; lower wins when accuracy is level)

| Size | iq2-fast98 | iq3-fast98 | coder-fast98 |
| --- | --- | --- | --- |
| 64000 | 17.7 | 38.2 | 9.6 |

## Bugs that every attempt of every model fixed: median minutes per request (the fastest model wins these)

| Test | iq2-fast98 | iq3-fast98 | coder-fast98 |
| --- | --- | --- | --- |
| bug-1@64000 | 12.0 | 25.0 | 3.6 |
| bug-3@64000 | 12.1 | 22.5 | 2.3 |
| bug-5@64000 | 18.6 | 41.9 | 17.8 |
| bug-6@64000 | 11.5 | 27.8 | 4.8 |
| bug-7@64000 | 11.9 | 22.0 | 2.7 |
| bug-8@64000 | 17.3 | 25.4 | 4.7 |
