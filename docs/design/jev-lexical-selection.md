# Jev lexical selection

**2026-10-07 controls:** The visible **Use Jev** checkbox selects word-meaning
preferences; **Use analysis LLM** independently permits the missing-word fallback.
Both default off, including after connecting OpenRouter. In Jev mode the browser
sends `allow_model_fallback: false` when the analysis LLM is off. This bypasses
both generative calls and cached generative candidates, including when preparing
the shared comparison inventory. With both models enabled the fallback supplies
vocabulary only, not the full open-text construction loop. Legacy API clients
omitting the flag retain the previous fallback behavior; send an explicit boolean
for reproducible use. Reports expose `model_requests` separately from Jev's
`selection.live_calls`; failed provider attempts count too.

**2026-10-04 update:** **See Jev in action** runs two actual DS parses on one
shared candidate inventory, displays both meanings, and exposes sense
probabilities, observed prefixes and DS-checked revision playback. See
[the comparison contract](jev-comparison.md). This does not enable the separate
search-order calibration gates or extend Jev assistance to Greek/TTR.

**2026-10-01 update:** runtime selection now uses a sense-only question and can
reconsider an earlier word as more input arrives, with each revision checked by DS
replay. Frame choices are left to DS continuation. See
[PP and incremental revision](pp-and-revision.md) for current behavior and checks.
The factorized sense/frame contract and benchmark below document the original
2026-09-30 implementation; its frozen questions and measurement remain unchanged.

The workbench has an optional **Dictionary + Jev lexical preferences** vocabulary
mode for native English classical and constructive DS. It supplies new vocabulary
through existing grammar templates, ranks supplied analyses using the observed
prefix, and lets DS execute and check their action programs.

Select a native English grammar, open **Expand the vocabulary**, choose this mode,
and try `john lends mary a book.` or `john lends a book to mary.` The lexical report
shows the prefix, preferred sense/frame, model probabilities, cache status, and
the expanded entries on the primary DS derivation. The tree still unfolds through
individual actions and pointer movements. Alternative analyses have their own
playback under **Complete analyses**. Probabilities describe model preferences;
they are not calibrated probabilities of linguistic correctness.

The API option is `lexical_mode: "jev"`. The separate `decision_mode` control governs
entry/tree search calibration and remains off by default. Its earlier measurement
found no search benefit; lexical opt-in does not enable those search hooks.
OpenRouter configuration is documented in [openrouter-jev.md](openrouter-jev.md).

## Candidate and execution contract

1. Authored grammar entries remain authoritative. Only missing words are expanded.
2. The local Princeton WordNet 3.0 index supplies available morphology, noun senses
   and verb frames. In this mode it is consulted before the bundled extension, so
   an extension entry cannot hide dictionary alternatives. WordNet-less forms may
   use the bundle.
3. Every proposal passes the existing surface, predicate, domain, arity and template
   validator before installation. Classical templates retain CN/epsilon/tau
   structure; constructive templates retain their typed predicates and Coq output.
   `lend` remains a `lend` predicate when instantiated with a give-family template.
4. At an actual lexical lookup, Jev sees the active left prefix, current word,
   grammar, speaker, tree and compiled candidates. It never sees later words,
   reference answers or a grammaticality label. Base/finite programs for the same
   analysis are grouped. Shared WordNet synsets count as one sense across frames.
5. One request asks separate Choice questions for **sense** and **frame**, omitting
   dimensions with only one option. Each includes `uncertain`. A non-uncertain
   choice needs at least 0.50 probability before it affects ordering. Reliable
   dimensions contribute their marginal probabilities to the ordering weight;
   uncertain dimensions do not erase a useful preference in the other dimension.
6. DS considers every candidate in that order and may backtrack. Completion
   heuristics still apply. Jev removes no programs and assigns no semantic truth
   or grammaticality judgments. The API defaults to `top_n=0` in this mode; an
   explicitly supplied entry limit and the ordinary parser caps still apply and
   remain visible in the result.

There are at most eight fresh Jev requests per parse, including alternative-reading
search. A new tree at an old prefix can require another decision. More than 254
candidate groups bypass ranking. Unavailable, invalid or uncertain answers leave
normal candidate order available. Validated answers are cached locally with
provider/model, question, prefix/tree and candidate-program identities; repeated
parses can reuse them. A cache hit has no network request. Answer validation and
the model-version check apply before use.

If the dictionary has neither a candidate nor a morphology analysis and the
analysis LLM is enabled, the selected lexical model can propose entries.
It receives the prefix through that form, approved template descriptions and the
semantic profile. This fallback runs during inventory preparation, before DS
execution; its result must pass the same validator. There is at most **one fresh
generative request per parse**, though cached proposals can supply other words.
Recognized unsupported plurals/participles do not trigger this fallback. Closed
classes, new constructions and additional words cannot be injected by a proposal.

## Separate lexical benchmark, 2026-09-30

The frozen [32 development probes](../../data/lexical-selection/benchmark.json)
use authored contrasting prefixes and reference WordNet synsets. References were
written before the first live call. The model receives only the prefix/candidates
and the fixed questions; probe IDs, reference labels and source commentary are
withheld. Some prefixes deliberately exceed current DS construction coverage.
The benchmark supplies an empty tree and tests contextual lexical selection,
not parsing. It is a small development sample, not an independently annotated
held-out corpus or evidence of broad parser coverage.

| Asked dimension | Jev reference matches | Dictionary-first matches |
| --- | ---: | ---: |
| Sense | 30 / 31 | 10 / 31 |
| Category/frame | 22 / 26 | 24 / 26 |

Only questions actually asked enter these denominators. Single-option dimensions
are not counted as model successes. One of 32 requests failed; its asked dimensions
count as incorrect. The frame sample mostly distinguishes nouns from verbs, with
only three verb probes; it is not a broad valency evaluation. In particular Jev
preferred a transitive frame for the loan sense of `lends`, and an intransitive
frame where the `whispers` prefix should leave valency open. The frozen references
and questions were not changed to improve these scores.

Model: `typesafe/jev-1.13-20260917`. Median request latency: 624 ms. Reported call
cost: USD 0.00488754; the failed response supplied no cost. The typed responses and
[results](../../data/lexical-selection/results.json) are committed. Reproduce
without network after installing the pinned dictionary:

```sh
.venv/bin/python scripts/benchmark_lexical_selection.py
```

`--live` explicitly queries missing responses. Use a separate `--responses` and
`--output` file for another run; do not silently replace the frozen measurement.
State/question hashes, answer schemas and pinned provider/model identities are
checked on replay.

## Integration evidence and limits

Four live sentence/mode checks completed: both give-family surface orders, each
in classical and constructive DS. Both constructive outputs compiled with Coq.
Repeated parses used zero fresh Jev calls. The double-object derivation used the
loan predicate `lend_vhho02324182`. At the real prefix `john lends`, however, Jev
reported uncertain sense and preferred the transitive frame. On the `to` example,
DS recovered dative analyses and returned the dictionary-first bestow-quality
sense before the loan sense. Both remained available. This demonstrates why a
complete, well-typed derivation cannot be treated as proof of sense accuracy.

`scripts/check_lexical_selection.py --live` verifies those integration cases,
pointer traces, Coq and cache reuse. Unit tests deliberately select a wrong frame
and verify recovery; they also cover both senses in alternative readings,
prefix isolation, invalid cached/provider answers, fallback validation/budget,
unsupported morphology and separation from the search gate. The browser check is
`scripts/check_lexical_selection_browser.py`; it exercises the real local server.

The dictionary mapping still lacks general countability, agreement, tense and
participial/plural realization. Jev cannot add PPs, quantifiers, passives or Greek
clitic rules that the grammar does not implement. Greek expansion remains the
separate sourced construction/morphology track. The next useful evaluation is a
larger independently reviewed sense/valency set, including ambiguous prefixes
from sentences the DS grammar can actually process.
