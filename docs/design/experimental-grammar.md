# Experimental model-written DS rules

The **Experimental grammar proposals** switch lets the analysis LLM propose
word-triggered action programs, including constructions absent from the existing
lexical templates. It is separate from ordinary vocabulary/construction assistance
and is off by default. This is a grammar-development experiment, not a claim of
unrestricted parsing or an automatic extension of the reviewed grammar.

## Try it

Connect OpenRouter, select a model, choose an English or Standard Modern Greek
sentence in Classical or Constructive DS, and tick **Experimental grammar
proposals**. This also enables the analysis LLM. Build the derivation. Jev can
remain enabled for dictionary sense preferences. The result panel shows each
proposal, its explanation, the compiled lexical programs and the outcome of
the DS replay. **Export JSON** retains this information for review.

For `A person entered the room with glasses`, there are two distinct gaps:
the ordinary noun entries need a determiner, and the maintained `with` entry
has a human-companion interpretation. A useful proposal must supply a bare
nominal construction and an appropriate object-taking PP interpretation.
Changing the noun to `human`, silently adding an article or ignoring the PP
would not be a faithful analysis. Even a successful object-accompaniment
analysis need not entail that the person is *wearing* the glasses.

`the person entered the room randomly` needs less machinery: ordinary analysis
LLM assistance now exposes the existing postverbal manner-adverb LINK templates.
It does not require experimental grammar. `quickly` remains available without AI.

## Execution

`dylan.experimental_grammar` first runs the existing grammar with dictionary or
corpus candidates. A complete result requires no generative call. A diagnosed
grammar/PCC violation is not overridden. Otherwise the selected chat model gets
the exact input, failure, stopping tree, semantic declarations, executable lexical
examples and the accepted action-language contract. It may return semantic
declarations and up to six rules. Each rule has a surface form, identifier,
explanation, conjunction of conditions, and sequence of effects.

The compiler wraps each program in `IF … THEN … ELSE abort`. It validates
declaration namespaces and signatures, selected-backend `Ty`/`Fo` syntax,
implemented labels and allowed effect classes. The allowed effects are `make`,
`go`, `gofirst`, `put`, `freshput`, `merge`, `semantic-adverb`, `semantic-pp`,
`semantic-comparison` and `semantic-modal`. Existing semantic operations can
be combined with new lexical structure; this is broader than filling slots
in a fixed list of vocabulary templates. Python, arbitrary macros, loops,
requirement deletion and changes to computational rules are not accepted.
Unknown effects are rejected rather than becoming the legacy factory's no-op.

A fresh parser tries the proposed actions before the original alternatives.
Normal DS introduction, anticipation, completion, thinning, elimination and
other applicable computational rules still perform the derivation. All input
tokens must be consumed and all requirements satisfied. An incomplete parse or
validation error is sent back once, with the preceding proposal, for a second
attempt. A proposal does not alter grammar files, subsequent requests or the
shared vocabulary cache. The browser retains the result until replaced/refreshed.

Limits are two model requests, six rules, twelve declarations, ten conditions
and 48 effects per rule. Effects are single lines of at most 600 characters.
Each provider call and parser replay has a deadline within the hosted request
budget. Jev retains one bounded sense-selection client across the baseline
and replays; its call allowance does not reset on every attempt. Jev does not
rank raw experimental programs as though they were reviewed dictionary senses.

## What “complete” means here

The result is labelled **Complete under experimental grammar**. This means DS
completed a derivation *assuming the model's new rules*. It does not establish
their linguistic correctness, intended interpretation, adequate restrictions,
or generalisation. A syntactically valid rule can overgenerate, choose the wrong
sense, or assert poorly motivated semantics. Mechanical checks are not a proof
that a proposed grammar is sound. The original-grammar baseline and rejected
attempts remain visible, and grammaticality stays independently unassessed.

Classical rules use their native individual/choice-term compiler. Constructive
rules use their native dependent-type compiler. The model must write the selected
backend's source syntax; printed tree labels are not executable source. TTR is
not translated into either system and has no experimental assistance in this
version. Paragraphs, dialogue, punctuation-triggered rules and computational-rule
induction are also outside this first version.

The JSON result records provider/model, raw proposals, validation/replay outcomes,
compiled programs, original grammar hash, proposal hash and timestamp. Repeating
a model call may produce a different proposal. To promote a useful proposal into
the maintained grammar, review its semantics and DS analysis, add positive and
negative examples and scope/ambiguity checks, test both intended backends, then
submit a normal source change through the [extension workflow](../community/extending.md).
Do not count experimental successes as reviewed or held-out grammar coverage.

## Verification

`tests/test_experimental_grammar.py` exercises real DS execution of fixture-written
programs, request isolation, backend separation, retries, invalid-program rejection,
PCC protection and the permission boundary. `tests/test_adverb_expansion.py` checks
the ordinary adverb path. Fixtures establish compiler/parser behaviour, not model
ability. `scripts/check_vocabulary_switches_browser.py --live` separately records
real checkbox payloads, billed provider requests and outcomes. Its `--experimental`
flag exercises raw rule generation; `--model`, `--backend` and `--sentence` make
the conditions explicit. It never saves credentials or authorization headers.

Live models can return invalid source, irrelevant rules, empty answers or timeouts.
Those remain failures. A model making requests and a model successfully analysing
the sentence are separate observations.
