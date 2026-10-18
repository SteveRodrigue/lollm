# TS project tests: side-by-side

Score per bug test: 4 = the diff applies (strict, ignoring whitespace, or by its changed lines) and the whole test suite passes (a different fix that works counts); below that: 1 = applies, +1 touches the right file, +1 the target test passes. The speed column gives the median decode speed, the prompt size and the median time per request (minutes). `no diff` = the model produced no usable diff (typically its output budget went to reasoning). Recall tests score 1 per correct answer.

| Test | iq2: score | coder: score | iq2: speed | coder: speed |
| --- | --- | --- | --- | --- |
| bug-1@135000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 21 tok/s, 119K tokens, 37.0 min | 23 tok/s, 119K tokens, 18.1 min |
| bug-3@135000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 20 tok/s, 117K tokens, 35.3 min | 19 tok/s, 117K tokens, 12.9 min |
| bug-7@135000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 16 tok/s, 118K tokens, 34.9 min | 21 tok/s, 118K tokens, 13.0 min |
| recall@135000 | 4.00/4 (2/2 full) | 4.00/4 (2/2 full) | 14 tok/s, 116K tokens, 33.5 min | 21 tok/s, 116K tokens, 12.2 min |

## Share of repeats that fully fixed the bug (bug tests only)

| Size | iq2 | coder |
| --- | --- | --- |
| 135000 | 6/6 | 6/6 |

## Time per request (all tests of a size, minutes)

| Size | iq2: median / total | coder: median / total |
| --- | --- | --- |
| 135000 | 35.1 / 281 (8 requests) | 13.6 / 113 (8 requests) |

## Minutes per full fix (total time of all bug attempts / attempts that fully fixed the bug; lower wins when accuracy is level)

| Size | iq2 | coder |
| --- | --- | --- |
| 135000 | 35.7 | 14.7 |

## Bugs that every attempt of every model fixed: median minutes per request (the fastest model wins these)

| Test | iq2 | coder |
| --- | --- | --- |
| bug-1@135000 | 37.0 | 18.1 |
| bug-3@135000 | 35.3 | 12.9 |
| bug-7@135000 | 34.9 | 13.0 |
