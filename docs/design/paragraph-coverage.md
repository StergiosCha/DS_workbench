# Paragraph parsing and the coverage target

The target is an unseen Greek or English paragraph with a verified DS derivation
for every sentence and context carried across sentence boundaries. Current work
does **not** meet this target.

The model-assisted path added on 2026-10-02 provides a proposal/compile/retry loop
for both languages. See [verified assistance](assisted-open-text.md) and its
separate development probe; it does not establish unrestricted coverage.

## Measured baseline, 2026-10-01

| Native backend | English paragraphs | English sentences | Greek passages | Greek sentences |
|---|---:|---:|---:|---:|
| Classical | 0/6 | 0/19 | 0/6 | 0/18 |
| Constructive | 0/6 | 0/19 | 0/6 | 0/18 |

The frozen sample and source metadata are in
[`unseen-passages.json`](../../data/coverage/unseen-passages.json); per-sentence
failures are in [`paragraph-baseline.json`](../../data/coverage/paragraph-baseline.json).
Sampling uses seed 20261001, 40–160 whitespace tokens, and unit-boundary filters.
It does not inspect lexicon membership or parse results. English uses original
NLTK Gutenberg blank-line paragraphs, including older literature, verse and
dialogue. Greek uses three consecutive sentences from one document in the GDT
r2.17 **test** split because original paragraph boundaries are unavailable. The
Greek lexical index uses only the **training** split. Svarna sample requests
timed out during this run; no source results were invented.

This is a small engineering baseline, not a representative accuracy estimate.
It becomes regression material after inspection. Further coverage claims require
fresh samples, including contemporary English/Greek prose, without filtering out
unsupported constructions. Development examples in `everyday-bilingual.json`
are constructed probes and must never be presented as unseen-text performance.

Reproduce:

```sh
.venv/bin/python scripts/sample_paragraph_coverage.py /path/to/gutenberg.zip /path/to/el_gdt-ud-test.conllu
.venv/bin/python scripts/audit_paragraph_coverage.py --output data/coverage/paragraph-baseline.json
```

## Implemented pipeline

`POST /api/parse` or `/api/parse/stream` accepts a `paragraph` string, grammar,
scope and lexical options. Paragraph, sentence and dialogue inputs are exclusive.
Paragraphs support native English and Standard Modern Greek classical/constructive
grammars, one selected analysis per sentence. Limits: 6,000 characters, 400 tokens,
24 sentences; an individual sentence has a 2,000-character/160-token limit.
Oversized sentences remain counted as failures. Hosted request bodies allow
32 KiB, while the worker retains its 55-second and 4 MiB response bounds.

Segmentation returns exact character spans. It handles common abbreviations,
initials, decimal points, closing quotation marks and Greek question semicolons.
Ambiguous abbreviation/quotation boundaries remain a limitation. Text is never
rewritten or silently omitted to obtain a successful parse.

Each sentence uses the same parser context. Only completed, type-checked DS trees
are retained for subsequent sentences; failed hypotheses restore the earlier
context and rule bindings. Every later row identifies excluded sentence indices.
Successful later sentences do not turn an incomplete paragraph into a success.
Basic named antecedents are accessible; arbitrary discourse anaphora, existential
witness accessibility, tense and full agreement are not solved by this pipeline.
Definite referent names are scoped per sentence and their identification remains
an explicit assumption.

Within the isolated worker, a sentence has a three-second parsing budget and the
paragraph a 23-second processing budget. Timeouts and unattempted sentences stay
in the denominator. Direct library use from non-main threads relies on the
caller's timeout, since POSIX alarms belong to the main thread.

Inspection uses actual recorded word states and the selected DS action sequence.
Operation replay is omitted for paragraphs to bound payload size; unusually
large word traces explicitly retain only initial/final snapshots. Sentence mode
still provides full operation replay. JSON exports contain the whole paragraph;
Coq exports apply to the selected constructive sentence. Coq files are exported,
not compiled by the hosted service. Regression tests compile representative
exports locally.

Verification means completion and semantic type checks **relative to the chosen
grammar and lexical hypotheses**. It is not a truth or grammaticality oracle.
Model proposals, WordNet senses and corpus frame hypotheses never set success.

## Coverage work still required

The measured failures include missing closed classes as well as open vocabulary,
quotations, possessives, number/agreement, auxiliaries, questions, coordination,
passives and clausal/adjunct constructions. Greek also needs systematic inflection,
contracted preposition/article forms, nominal modification and embedded clauses.
Dictionary growth alone cannot address these families.

The next acceptance step is a documented construction inventory and genuine DS
programs for these families in both languages, with positive source evidence,
negative controls and semantic exports. Each change must be assessed against the
frozen sample and a fresh sample; complete-passage rates remain the primary
metric. A generic dependency parser or an LLM-generated tree must not be labelled
as a verified DS derivation.
