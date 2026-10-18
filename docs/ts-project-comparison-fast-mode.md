# TS project tests: side-by-side

Score per bug test: 1 = the diff applies, +1 touches the right file, +1 the target test passes, +1 the whole suite passes. `no diff` = the model produced no usable diff (typically its output budget went to reasoning). Recall tests score 1 per correct answer.

| Test | default: score | fast: score | default: speed | fast: speed |
| --- | --- | --- | --- | --- |
| bug-1@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 26 tok/s, 15K tokens | 32 tok/s, 15K tokens |
| bug-2@16000 | 0.00/4 (0/2 full, 2 no diff) | 0.00/4 (0/2 full, 2 no diff) | 41 tok/s, 15K tokens | 40 tok/s, 15K tokens |
| bug-3@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 31 tok/s, 15K tokens | 26 tok/s, 15K tokens |
| bug-4@16000 | 2.00/4 (1/2 full, 1 no diff) | 0.00/4 (0/2 full, 2 no diff) | 43 tok/s, 14K tokens | 67 tok/s, 14K tokens |
| bug-5@16000 | 0.00/4 (0/2 full, 2 no diff) | 0.00/4 (0/2 full, 2 no diff) | 44 tok/s, 14K tokens | 34 tok/s, 14K tokens |
| bug-6@16000 | 4.00/4 (2/2 full) | 2.00/4 (1/2 full) | 34 tok/s, 15K tokens | 31 tok/s, 15K tokens |
| bug-7@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 34 tok/s, 15K tokens | 30 tok/s, 15K tokens |
| bug-8@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 34 tok/s, 14K tokens | 23 tok/s, 14K tokens |
| recall@16000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 33 tok/s, 13K tokens | 29 tok/s, 13K tokens |
| bug-1@64000 | 4.00/4 (2/2 full) | 0.00/4 (0/1 full, 1 no diff) | 31 tok/s, 55K tokens | 51 tok/s, 55K tokens |
| bug-2@64000 | 0.00/4 (0/2 full, 2 no diff) | 0.00/4 (0/1 full, 1 no diff) | 44 tok/s, 56K tokens | 33 tok/s, 56K tokens |
| bug-3@64000 | 2.00/4 (1/2 full) | 4.00/4 (1/1 full) | 28 tok/s, 60K tokens | 23 tok/s, 60K tokens |
| bug-4@64000 | 2.00/4 (1/2 full, 1 no diff) | 0.00/4 (0/1 full, 1 no diff) | 45 tok/s, 58K tokens | 33 tok/s, 58K tokens |
| bug-5@64000 | 0.00/4 (0/2 full, 1 no diff) | 0.00/4 (0/1 full, 1 no diff) | 35 tok/s, 56K tokens | 32 tok/s, 56K tokens |
| bug-6@64000 | 2.00/4 (1/2 full) | 4.00/4 (1/1 full) | 20 tok/s, 57K tokens | 20 tok/s, 57K tokens |
| bug-7@64000 | 4.00/4 (2/2 full) | 4.00/4 (1/1 full) | 26 tok/s, 58K tokens | 24 tok/s, 58K tokens |
| bug-8@64000 | 2.00/4 (1/2 full) | 4.00/4 (1/1 full) | 25 tok/s, 56K tokens | 33 tok/s, 56K tokens |
| recall@64000 | 4.00/4 (2/2 full) | 4.00/4 (1/1 full) | 21 tok/s, 57K tokens | 17 tok/s, 57K tokens |

## Share of repeats that fully fixed the bug (bug tests only)

| Size | default | fast |
| --- | --- | --- |
| 16000 | 11/16 | 9/16 |
| 64000 | 8/16 | 4/8 |
