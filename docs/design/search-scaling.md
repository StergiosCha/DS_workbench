# Search scaling

Measured with `scripts/scale_probe.py` and the committed synthetic fixture. k duplicates each lexical row; m adds mutually exclusive optional choices. Counts exclude display replay. Timings are machine-dependent.

| k | m | top_n | ok | tuples | computational attempts | lexical attempts | max children | ms |
|---:|---:|---:|:---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | True | 10 | 143 | 13 | 1 | 12.74 |
| 2 | 0 | 0 | True | 18 | 143 | 26 | 2 | 6.17 |
| 4 | 0 | 0 | True | 34 | 143 | 52 | 4 | 8.5 |
| 8 | 0 | 0 | True | 66 | 143 | 104 | 8 | 18.18 |
| 8 | 0 | 3 | True | 26 | 143 | 39 | 3 | 7.71 |
| 1 | 3 | 0 | True | 19 | 326 | 25 | 4 | 10.69 |
| 1 | 6 | 0 | True | 28 | 581 | 37 | 7 | 17.31 |
| 4 | 6 | 0 | True | 106 | 581 | 148 | 28 | 28.29 |

## M4a adjunction checkpoint, 2026-09-28

General and late unfixed adjunction are active in the maintained SMG, Grico and Pontic grammars. The table uses vocabulary-covered rows from `build/coverage/greek-clitics-top3.jsonl`, including negative controls. Pending M4a vocabulary is excluded. Timings include workbench tracing and grammar loading and were collected while regression checks were also running; rerun in isolation before using them for a performance gate.

| Grammar | Rows | Median ms | Median tuples | Median successful backtracks |
| --- | ---: | ---: | ---: | ---: |
| Grico classical | 12 | 32 | 3 | 0 |
| Grico constructive | 12 | 32.5 | 3 | 0 |
| Pontic classical | 17 | 52 | 5 | 0 |
| Pontic constructive | 17 | 52 | 5 | 0 |
| SMG classical | 32 | 51 | 3 | 0 |
| SMG constructive | 32 | 48 | 3 | 0 |

The new adapted word-order fixtures produce several children per word and require real backtracking on some orders. Final action traces now follow the selected derivation; the workbench displays returns to an earlier branch. Static prefiltering, structural memoization and fan-out ranking remain unimplemented. No lazy-semantic optimization or model ordering was enabled at this checkpoint.

## M4b approved vocabulary and alternative playback, 2026-09-28

The same vocabulary-covered row measure now includes approved M4a. Final corpus evidence is `/tmp/ds-corpus-m4b-final.log`; timings again include concurrent regression activity, loading and workbench tracing, so they are observations rather than a performance gate. Negative controls are included. Ordinary requests still ask for one complete analysis; optional additional search has separate counters in `reading_search.stats`.

| Grammar | Rows | Median ms | Median tuples | Median successful backtracks |
| --- | ---: | ---: | ---: | ---: |
| Grico classical | 15 | 60 | 4 | 0 |
| Grico constructive | 15 | 58 | 4 | 0 |
| Pontic classical | 17 | 54 | 5 | 0 |
| Pontic constructive | 17 | 54 | 5 | 0 |
| SMG classical | 33 | 56 | 8 | 0 |
| SMG constructive | 33 | 56 | 8 | 0 |

Alternative enumeration stops at the requested result count, available-search exhaustion, 100 examined leaves or an existing parser cap. A result limit does not establish exhaustive coverage. No static prefilter, structural memo, model ranking or lazy semantics was enabled.
