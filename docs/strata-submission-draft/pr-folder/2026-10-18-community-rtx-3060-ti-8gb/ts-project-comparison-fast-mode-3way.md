# TS project tests: side-by-side

Score per bug test: 4 = the diff applies (strict, ignoring whitespace, or by its changed lines) and the whole test suite passes (a different fix that works counts); below that: 1 = applies, +1 touches the right file, +1 the target test passes. The speed column gives the median decode speed, the prompt size and the median time per request (minutes). `no diff` = the model produced no usable diff (typically its output budget went to reasoning). Recall tests score 1 per correct answer.

| Test | iq2: score | iq3: score | coder: score | iq2: speed | iq3: speed | coder: speed |
| --- | --- | --- | --- | --- | --- | --- |
| bug-1@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 32 tok/s, 15K tokens, 3.4 min | 21 tok/s, 15K tokens, 5.5 min | 39 tok/s, 15K tokens, 2.9 min |
| bug-2@16000 | 0.00/4 (0/2 full, 2 no diff) | 2.00/4 (1/2 full) | 2.00/4 (1/2 full, 1 no diff) | 40 tok/s, 15K tokens, 15.4 min | 21 tok/s, 15K tokens, 22.3 min | 40 tok/s, 15K tokens, 10.4 min |
| bug-3@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 26 tok/s, 15K tokens, 2.0 min | 20 tok/s, 15K tokens, 2.9 min | 37 tok/s, 15K tokens, 0.8 min |
| bug-4@16000 | 0.00/4 (0/2 full, 2 no diff) | 0.00/4 (0/2 full, 2 no diff) | 3.00/4 (1/2 full) | 67 tok/s, 14K tokens, 9.6 min | 47 tok/s, 14K tokens, 13.5 min | 40 tok/s, 14K tokens, 3.4 min |
| bug-5@16000 | 0.00/4 (0/2 full, 2 no diff) | 0.00/4 (0/2 full, 2 no diff) | 2.00/4 (1/2 full, 1 no diff) | 34 tok/s, 14K tokens, 17.7 min | 22 tok/s, 14K tokens, 26.2 min | 43 tok/s, 14K tokens, 12.8 min |
| bug-6@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 31 tok/s, 15K tokens, 2.9 min | 20 tok/s, 15K tokens, 6.9 min | 41 tok/s, 15K tokens, 3.5 min |
| bug-7@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 30 tok/s, 15K tokens, 2.0 min | 19 tok/s, 15K tokens, 3.6 min | 39 tok/s, 15K tokens, 1.2 min |
| bug-8@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 23 tok/s, 14K tokens, 5.2 min | 21 tok/s, 14K tokens, 4.9 min | 41 tok/s, 14K tokens, 3.3 min |
| recall@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 29 tok/s, 13K tokens, 1.5 min | 25 tok/s, 13K tokens, 1.9 min | 40 tok/s, 13K tokens, 0.3 min |
| bug-1@64000 | 0.00/4 (0/1 full, 1 no diff) | 2.00/4 (1/2 full, 1 no diff) | 4.00/4 (2/2 full) | 51 tok/s, 55K tokens, 14.7 min | 21 tok/s, 55K tokens, 21.5 min | 37 tok/s, 55K tokens, 5.1 min |
| bug-2@64000 | 0.00/4 (0/1 full, 1 no diff) | 0.00/4 (0/2 full, 2 no diff) | 2.00/4 (1/2 full, 1 no diff) | 33 tok/s, 56K tokens, 16.4 min | 21 tok/s, 56K tokens, 22.1 min | 41 tok/s, 56K tokens, 4.5 min |
| bug-3@64000 | 4.00/4 (1/1 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 23 tok/s, 60K tokens, 12.5 min | 17 tok/s, 60K tokens, 16.3 min | 36 tok/s, 60K tokens, 2.2 min |
| bug-4@64000 | 0.00/4 (0/1 full, 1 no diff) | 0.00/4 (0/2 full, 2 no diff) | 0.00/4 (0/2 full, 2 no diff) | 33 tok/s, 58K tokens, 15.7 min | 23 tok/s, 58K tokens, 20.4 min | 36 tok/s, 58K tokens, 4.8 min |
| bug-5@64000 | 0.00/4 (0/1 full, 1 no diff) | 0.00/4 (0/2 full, 2 no diff) | 2.00/4 (1/2 full, 1 no diff) | 32 tok/s, 56K tokens, 16.3 min | 23 tok/s, 56K tokens, 21.5 min | 36 tok/s, 56K tokens, 5.8 min |
| bug-6@64000 | 4.00/4 (1/1 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 20 tok/s, 57K tokens, 11.8 min | 17 tok/s, 57K tokens, 17.7 min | 37 tok/s, 57K tokens, 3.4 min |
| bug-7@64000 | 4.00/4 (1/1 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 24 tok/s, 58K tokens, 12.1 min | 20 tok/s, 58K tokens, 16.8 min | 39 tok/s, 58K tokens, 2.2 min |
| bug-8@64000 | 4.00/4 (1/1 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 33 tok/s, 56K tokens, 13.7 min | 20 tok/s, 56K tokens, 19.8 min | 38 tok/s, 56K tokens, 3.4 min |
| recall@64000 | 4.00/4 (1/1 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 17 tok/s, 57K tokens, 11.6 min | 11 tok/s, 57K tokens, 14.9 min | 40 tok/s, 57K tokens, 1.6 min |

## Share of repeats that fully fixed the bug (bug tests only)

| Size | iq2 | iq3 | coder |
| --- | --- | --- | --- |
| 16000 | 10/16 | 11/16 | 13/16 |
| 64000 | 4/8 | 9/16 | 12/16 |

## Time per request (all tests of a size, minutes)

| Size | iq2: median / total | iq3: median / total | coder: median / total |
| --- | --- | --- | --- |
| 16000 | 3.8 / 120 (18 requests) | 5.6 / 175 (18 requests) | 3.0 / 77 (18 requests) |
| 64000 | 13.7 / 125 (9 requests) | 20.2 / 342 (18 requests) | 4.4 / 66 (18 requests) |

## Minutes per full fix (total time of all bug attempts / attempts that fully fixed the bug; lower wins when accuracy is level)

| Size | iq2 | iq3 | coder |
| --- | --- | --- | --- |
| 16000 | 11.7 | 15.6 | 5.9 |
| 64000 | 28.3 | 34.7 | 5.2 |

## Bugs that every attempt of every model fixed: median minutes per request (the fastest model wins these)

| Test | iq2 | iq3 | coder |
| --- | --- | --- | --- |
| bug-1@16000 | 3.4 | 5.5 | 2.9 |
| bug-3@16000 | 2.0 | 2.9 | 0.8 |
| bug-6@16000 | 2.9 | 6.9 | 3.5 |
| bug-7@16000 | 2.0 | 3.6 | 1.2 |
| bug-8@16000 | 5.2 | 4.9 | 3.3 |
| bug-3@64000 | 12.5 | 16.3 | 2.2 |
| bug-6@64000 | 11.8 | 17.7 | 3.4 |
| bug-7@64000 | 12.1 | 16.8 | 2.2 |
| bug-8@64000 | 13.7 | 19.8 | 3.4 |
