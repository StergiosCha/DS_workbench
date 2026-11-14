# First scored literature diagnostic

Implemented on branch codex/literature-diagnostic-v1 in a separate checkout.
The existing working directory's pending parser and manuscript edits are not
part of this change.

## Question and materials

Does a declared component check number against the subject NP head when a
PP contains an intervening noun with the opposite number?

The diagnostic uses all 19 items in each of the previously selected SyntaxGym
number_prep and reflexive_prep_masc suites: 38 four-condition item sets,
152 condition sentences, and 19 shared lexical frames. Hu, Gauthier, Qian,
Wilcox and Levy (2020), *A Systematic Assessment of Syntactic Generalization in
Neural Language Models*, supplies the source framework and materials.

Source repository:
https://github.com/cpllab/syntactic-generalization

The existing literature manifest pins commit
43f1f86b746254406dafc89bd17b9d4976607ef6 and the two file hashes. The importer
checks them before every run. MIT attribution and upstream prediction formulas
are included in the output. Regions, condition names and lexical content are
preserved; the input sentence joins nonempty regions with spaces. Engines
lowercase and split on whitespace. Multiword prepositions are lexical entries
over observed token spans, with no future-word access.

This is a **derived licensing diagnostic**, not the original regional-surprisal
evaluation. The original inequalities remain unscored because these engines do
not supply normalized next-word probabilities. No reading-time measurements or
human grammaticality ratings are created by this transformation.

## Protocol and development status

data/experiments/literature-diagnostic-v1.json was committed as a0a02a3 before
implementation and scoring. The materials had already been inspected. This is
not a preregistration or a held-out evaluation.

All 19 shared lexical frames are development material. Both suites informed the
lexicon. No significance tests or independence-based confidence intervals are
reported. The per-suite families are paired across suites, not 38 independent
lexical draws. A later train/test split must also account for overlap of nouns
across item numbers, rather than assuming those 19 frames are lexically disjoint.

During development, the initial lexical fragment lacked progressive *is
playing tennis* and the NP complement in *enjoy tennis*. Both entries were
added to all five configurations equally. Source items were neither removed
nor rewritten.

## Executable components

feature_engine.py combines the existing categorial application machinery and
lambda terms with the existing typed-feature unifier. The new lexical fragment
supports subject NPs with PP modifiers, the tested finite-verb complements,
and a local reflexive object. It does not replace either original CCG lexicon.

Forward and backward application construct an incremental chart. Determiners
and prenominal modifiers inherit the nominal head from their complement.
Postnominal PP modification preserves the head on the left and records the
intervening nominal separately. When NP and S\NP combine, the enabled
constraints unify the controller's number with the finite verb's requirement
and/or the local reflexive's requirement. Past verbs here carry no number
requirement. Third-person reference is fixed by the declared fragment.

| Configuration | Subject–verb number | Reflexive number | Controller |
| --- | --- | --- | --- |
| ccg-feature-head-v1 | Checked | Checked | Subject NP head |
| ccg-feature-none-v1 | Disabled | Disabled | Subject NP head |
| ccg-feature-nearest-v1 | Checked | Checked | Last nominal in subject NP |
| ccg-feature-no-agreement-v1 | Disabled | Checked | Subject NP head |
| ccg-feature-no-binding-v1 | Checked | Disabled | Subject NP head |

All five use exactly the same lexicon and application rules; the report records
their lexicon hashes. The nearest-noun variant changes the number controller,
not the semantic referent of the reflexive. In all variants its semantic term
is bound to the local subject. This is an intentionally incorrect control on
these number-distractor materials, not a general linear processing model.

This is a limited CCG plus typed-feature hybrid, not a complete HPSG grammar,
binding theory or theory of English. Gender and antecedent ambiguity are not
tested. Masculine reference is assumed to be contextually available; occupation
nouns are not assigned masculine lexical gender. The lambda interpretations
are inspectable, but the licensing score does not validate every meaning.
The labels adopt the source's intended singular/plural contrast. This fragment
treats *themselves* as plural-only and excludes singular-they reflexives.
Consequently the negative label is not a claim that every such string is
ungrammatical across interpretations or varieties of English.

The new component is available to the neutral experiment host through explicit
trusted registration:

    from dylan.experiments.feature_engine import register
    from dylan.experiments.contracts import Configuration, Observation
    from dylan.experiments.host import Session

    register()
    session = Session(Configuration(grammar="ccg-feature-head-v1", memory="count-v1"))
    try:
        event = session.observe(Observation(
            "the student near the sailors is good", task="sentence"))
    finally:
        session.close()

Native memory cues are rule/category tuples from the retained categorial
derivations. Existing memory and response components can consume them. This
diagnostic does not fit or score those components. The existing web configuration
catalog is not silently expanded; the new report is a standalone interactive
artifact. No LingEmbed export adapter for these annotated signs is claimed.

## Scoring and unavailable analyses

A positive condition requires a complete derivation. A negative receives
rejection credit only when an otherwise complete S derivation has an explicit
enabled feature conflict. Unknown vocabulary, unsupported structures, search
bounds, exceptions and worker timeouts are unavailable.

Each family requires all four source conditions to be evaluable. It passes
only if all four decisions are correct. Condition accuracy and positive/
negative rates are secondary outcomes. An accept-all system consequently has
50% condition accuracy and zero passing families.

Every engine receives only its ID and the sentence strings in an isolated
worker, without suite labels, expected outcomes or region metadata. The chart
allows 32 words and 256 signs per cell; original engines retain their original
bounds. Each engine worker has a 120-second bound. Scores identify the source
files, protocol, runtime source manifest and output conditions. A source change
during evaluation prevents writing a mixed-version report.

## Recorded result

| Configuration | Evaluable families | Correct families | Condition accuracy |
| --- | ---: | ---: | ---: |
| Subject-head constraints | 38/38 | 38 | 100% |
| Both constraints disabled | 38/38 | 0 | 50% |
| Nearest-noun controller | 38/38 | 0 | 0% |
| Agreement disabled | 38/38 | 19 | 75% |
| Reflexive checking disabled | 38/38 | 19 | 75% |

The unextended DS reference yields 148 vocabulary gaps and four construction
gaps. The three unextended CCG configurations yield 152 vocabulary gaps each.
They have zero complete evaluable families, so no matched architectural
accuracy comparison is available. Their results are not scored as zero
linguistic accuracy.

The full component's result verifies the stated dependency on these
source-informed development items. It does not establish discovery, held-out
generalization, a neural benefit, human processing adequacy or a winning theory.

## Reproduce and inspect

From an environment installed with the project's development dependencies:

    python -m dylan.experiments.diagnostic --fetch
    python -m pytest -q tests/test_experiment_feature_engine.py tests/test_experiment_diagnostic.py

An existing pinned cache can be supplied with --cache. The default outputs are
build/experiments/literature-diagnostic-v1/results.json, report.md and report.html.
The HTML opens offline, filters by suite/family/configuration, displays source
critical regions and constraint decisions, and downloads the complete JSON.

The committed aggregate in data/experiments/literature-diagnostic-results-v1.json
contains provenance, counts and scores. Detailed source sentences and derivation
records stay in the ignored build output. No model calls or credentials are
needed for reproduction.

Next scientific step: extend reference coverage from explicit analyses and
construct lexical/material splits plus cases that distinguish competing
grammatical analyses. Normalized predictive probabilities or a calibrated
response model are separate additions before scoring surprisal or human RT.
