# First DS search calibration

The current Jev questions do not improve search in the measured native
English/SMG fragments. Automatic preferences remain off. This result concerns
ordering existing DS choices, not Jev's general language ability or the separate
DeepSeek lexical expansion service.

## Sample and method

The runner deduplicated 344 grammar/surface pairs from the existing English
and Greek regression corpora, using classical and constructive English and SMG.
Lexical `top_n=0` retained all entries. Local recording matched ordinary parsing
in outcomes, meanings, cap status and search counters on all 344 cases.

The capture contained 261 distinct decision states. Of these, 109 had a
reference choice on a successful primary path and were sent to OpenRouter
`typesafe/jev-1.13-20260917`. Identical states were queried once. Two states
had conflicting reference paths across sentences and were excluded from
single-reference scores. The other 107 constitute the scored sample.

The reference is retrospective agreement with a recorded successful path,
not an annotation that all other choices are linguistically wrong. The model
receives only the actual prefix, current word, pointer/tree, grammar and
candidates. All labelled states were checked against their source prefixes.
Future words, completed meanings, corpus judgments and reference choices stay
in the evaluation process. Failed paths are retained for outcome-parity replay
but supply no successful-path labels.

The questions and 0.50 preference threshold were frozen before the live run.
This is an initial measurement, not a held-out test after prompt tuning.
There are fewer independent states per grammar/family than the activation
criteria require; repeated prefixes were not counted as extra examples.

## Results

The two ordering hooks were replayed separately. Backtracks below count
successful backward search steps across that grammar's cases; they do not
include the additional work of enumerating readings.

| Grammar | Hook | Scored states | Path agreement | Normal → replay backtracks |
| --- | --- | ---: | ---: | ---: |
| English classical | lexical | 11 | 100% | 0 → 0 |
| English constructive | lexical | 12 | 100% | 0 → 0 |
| English classical | tree | 2 | 0% | 0 → 0 |
| English constructive | tree | 2 | 0% | 0 → 0 |
| SMG classical | lexical | 17 | 41.2% | 109 → 113 |
| SMG constructive | lexical | 17 | 35.3% | 99 → 103 |
| SMG classical | tree | 23 | 60.9% | 109 → 110 |
| SMG constructive | tree | 23 | 56.5% | 99 → 99 |

All 688 replay comparisons preserved the original parse outcome, completeness,
meaning and cap status. No candidate pruning or lexical top-N cuts occurred.
Unqueried states encountered during replay retained normal order; the report
records replay hits and misses. These are frozen-response experiments, not a
claim that every possible live search trajectory has been tested.

All 109 provider requests succeeded. Total cost: USD 0.005976768. Median
latency: 553 ms; 95th percentile: 806 ms. Replay timing excludes network calls.
Correctly ranking entries that DS already filters cheaply does not establish
a speed improvement. Neither hook reduced backtracking in any measured group.

The runtime gate now explicitly requires reduced backtracking, outcome parity,
actual replay hits and complete sampled responses in addition to its minimum
sample/agreement or gain criteria. Grammar, question/state, ranking code, client,
model and provider fingerprints invalidate stale evidence. No gate was enabled.
The workbench displays the measured lack of benefit instead of saying only
that calibration has not been performed.

## Reproduce and inspect

Aggregate evidence is in `data/decision/calibration-2026-09-30.json`.
The 109 typed answers, identities, costs and timings are archived in
`data/decision/answers-2026-09-30.json`, without credentials or prompt text.
Full captured states, case-level comparisons and logs remain under the ignored
`build/decision/calibration/` directory. Reconstruct states and replay archived
answers without network calls:

```sh
DS_DECISION_PROVIDER=openrouter .venv/bin/python scripts/calibrate_decisions.py collect
DS_DECISION_PROVIDER=openrouter .venv/bin/python scripts/calibrate_decisions.py evaluate --responses data/decision/answers-2026-09-30.json
```

Offline collection/replay needs no API key. For a new live measurement, `query` uses the configured OpenRouter key;
`--per-group` bounds unique requests and `--workers` allows at most four.
Existing responses are reused. `evaluate --install-gates` installs only
qualifying evidence and saves the aggregate UI status. `--summary PATH`
exports a compact report. Changed grammars or decision code require a new
capture; changed state/question hashes cannot reuse old answers.

## Verification and next work

Regression tests deliberately prefer an unsuccessful analysis and verify
backtracking to success. Exhaustive small-fixture checks retain all three
fixed/unfixed/topic analyses in both semantic modes, including their tree
decorations and meanings. Tests also cover reference isolation, model identity,
stale evidence, and public summaries. Browser checks cover measured status and
local recording in both modes.

The next coverage step is explicit PP and additional quantifier construction
families, with typed lexical reuse. After the candidate inventory grows, a new
benchmark should target contextual sense/valency choices where normal search
actually does substantial work. Keep Greek dialect evaluation separate and
preserve the distinction between parser coverage and sourced grammaticality.
