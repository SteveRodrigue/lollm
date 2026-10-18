# TS project tests: side-by-side

Score per bug test: 4 = the diff applies (strict, ignoring whitespace, or by its changed lines) and the whole test suite passes (a different fix that works counts); below that: 1 = applies, +1 touches the right file, +1 the target test passes. The speed column gives the median decode speed, the prompt size and the median time per request (minutes). `no diff` = the model produced no usable diff (typically its output budget went to reasoning). Recall tests score 1 per correct answer.

| Test | iq2: score | iq3: score | coder: score | iq2: speed | iq3: speed | coder: speed |
| --- | --- | --- | --- | --- | --- | --- |
| bug-1@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 26 tok/s, 15K tokens, 5.9 min | 20 tok/s, 15K tokens, 7.7 min | 33 tok/s, 15K tokens, 6.0 min |
| bug-2@16000 | 0.00/4 (0/2 full, 2 no diff) | 2.00/4 (1/2 full, 1 no diff) | 4.00/4 (2/2 full) | 41 tok/s, 15K tokens, 16.3 min | 21 tok/s, 15K tokens, 26.8 min | 31 tok/s, 15K tokens, 11.8 min |
| bug-3@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 31 tok/s, 15K tokens, 3.5 min | 20 tok/s, 15K tokens, 4.3 min | 33 tok/s, 15K tokens, 1.7 min |
| bug-4@16000 | 2.00/4 (1/2 full, 1 no diff) | 4.00/4 (2/2 full) | 2.00/4 (1/2 full, 1 no diff) | 43 tok/s, 14K tokens, 10.6 min | 21 tok/s, 14K tokens, 19.0 min | 39 tok/s, 14K tokens, 8.8 min |
| bug-5@16000 | 0.00/4 (0/2 full, 2 no diff) | 2.00/4 (1/2 full, 1 no diff) | 0.00/4 (0/2 full, 2 no diff) | 44 tok/s, 14K tokens, 15.1 min | 22 tok/s, 14K tokens, 23.4 min | 39 tok/s, 14K tokens, 14.7 min |
| bug-6@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 2.00/4 (1/2 full, 1 no diff) | 34 tok/s, 15K tokens, 6.8 min | 21 tok/s, 15K tokens, 7.7 min | 37 tok/s, 15K tokens, 7.5 min |
| bug-7@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 34 tok/s, 15K tokens, 3.1 min | 20 tok/s, 15K tokens, 5.0 min | 20 tok/s, 15K tokens, 2.4 min |
| bug-8@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 34 tok/s, 14K tokens, 5.1 min | 21 tok/s, 14K tokens, 9.8 min | 31 tok/s, 14K tokens, 5.7 min |
| recall@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 33 tok/s, 13K tokens, 2.5 min | 26 tok/s, 13K tokens, 3.3 min | 25 tok/s, 13K tokens, 0.7 min |
| bug-1@64000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 2.00/4 (1/2 full, 1 no diff) | 31 tok/s, 55K tokens, 18.6 min | 17 tok/s, 55K tokens, 38.1 min | 35 tok/s, 55K tokens, 10.9 min |
| bug-2@64000 | 0.00/4 (0/2 full, 2 no diff) | 4.00/4 (2/2 full) | 2.00/4 (1/2 full, 1 no diff) | 44 tok/s, 56K tokens, 30.4 min | 18 tok/s, 56K tokens, 50.3 min | 37 tok/s, 56K tokens, 12.9 min |
| bug-3@64000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 28 tok/s, 60K tokens, 20.5 min | 18 tok/s, 60K tokens, 38.6 min | 33 tok/s, 60K tokens, 6.2 min |
| bug-4@64000 | 2.00/4 (1/2 full, 1 no diff) | 2.00/4 (1/2 full) | 2.00/4 (0/2 full) | 45 tok/s, 58K tokens, 29.7 min | 21 tok/s, 58K tokens, 52.5 min | 31 tok/s, 58K tokens, 9.2 min |
| bug-5@64000 | 2.00/4 (1/2 full, 1 no diff) | 4.00/4 (2/2 full) | 2.00/4 (1/2 full, 1 no diff) | 35 tok/s, 56K tokens, 28.4 min | 20 tok/s, 56K tokens, 53.1 min | 30 tok/s, 56K tokens, 17.7 min |
| bug-6@64000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 20 tok/s, 57K tokens, 19.5 min | 16 tok/s, 57K tokens, 38.7 min | 28 tok/s, 57K tokens, 9.9 min |
| bug-7@64000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 26 tok/s, 58K tokens, 20.5 min | 18 tok/s, 58K tokens, 39.9 min | 28 tok/s, 58K tokens, 6.1 min |
| bug-8@64000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 25 tok/s, 56K tokens, 21.0 min | 16 tok/s, 56K tokens, 40.7 min | 30 tok/s, 56K tokens, 9.1 min |
| recall@64000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 21 tok/s, 57K tokens, 19.4 min | 11 tok/s, 57K tokens, 37.8 min | 26 tok/s, 57K tokens, 5.5 min |

## Share of repeats that fully fixed the bug (bug tests only)

| Size | iq2 | iq3 | coder |
| --- | --- | --- | --- |
| 16000 | 11/16 | 14/16 | 12/16 |
| 64000 | 12/16 | 15/16 | 11/16 |

## Time per request (all tests of a size, minutes)

| Size | iq2: median / total | iq3: median / total | coder: median / total |
| --- | --- | --- | --- |
| 16000 | 5.9 / 138 (18 requests) | 9.7 / 214 (18 requests) | 5.1 / 119 (18 requests) |
| 64000 | 22.3 / 416 (18 requests) | 42.6 / 779 (18 requests) | 8.2 / 175 (18 requests) |

## Minutes per full fix (total time of all bug attempts / attempts that fully fixed the bug; lower wins when accuracy is level)

| Size | iq2 | iq3 | coder |
| --- | --- | --- | --- |
| 16000 | 12.1 | 14.8 | 9.8 |
| 64000 | 31.4 | 46.9 | 14.9 |

## Bugs that every attempt of every model fixed: median minutes per request (the fastest model wins these)

| Test | iq2 | iq3 | coder |
| --- | --- | --- | --- |
| bug-1@16000 | 5.9 | 7.7 | 6.0 |
| bug-3@16000 | 3.5 | 4.3 | 1.7 |
| bug-7@16000 | 3.1 | 5.0 | 2.4 |
| bug-8@16000 | 5.1 | 9.8 | 5.7 |
| bug-3@64000 | 20.5 | 38.6 | 6.2 |
| bug-6@64000 | 19.5 | 38.7 | 9.9 |
| bug-7@64000 | 20.5 | 39.9 | 6.1 |
| bug-8@64000 | 21.0 | 40.7 | 9.1 |
