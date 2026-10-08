# Verified assistance for open text

**4 October update:** the [construction interface](construction-assistance.md)
now accepts finite-clause relation hypotheses alongside vocabulary. Older
content-word-only descriptions below describe the initial implementation.

Select **Open text · LLM + verified DS** after connecting an OpenRouter key.
Connecting selects this mode automatically; the chosen model works for both
English and Standard Modern Greek. The service never uses a different user's
key, stores the supplied key, or returns a model-written tree as a derivation.

The system first compiles WordNet or Greek training-corpus entries. For missing
content words, the model proposes contextual lemmas, senses, argument domains,
case, gender, person, number and finite/nonfinite morphology. Local code validates
the entire batch, instantiates reviewed lexical action templates, and installs
it atomically. Surface forms cannot introduce action code or formulas. Closed
classes remain governed by explicit grammar programs.

A failed DS derivation can trigger an additional lexical analysis, including a
missing sense of a known word. The retry receives the original sentence, selected
backend, failed token, current tree requirements and earlier lexical analyses.
Validation errors also receive bounded correction attempts. Original entries are
retained. Three provider calls and three derivation attempts per sentence are
upper bounds; a paragraph shares its three-call budget across all sentences.
Models may omit entries or propose incorrect morphology and senses. Completion
therefore establishes a DS derivation relative to those lexical assumptions,
not an independent judgment of grammaticality, intended meaning or truth.

## Distributive plurals and provider-call policy

English `all people`, `all children`, regular plurals, and `all the ...` now
execute native DS actions as subjects or objects, including inside conjunction.
`all` requires a plural restrictor; a plural entry cannot fill `a` or `every`.
WordNet's suppletive `people -> person` mapping uses the human-being sense,
not the body or grammatical-category senses that pluralize as `persons`.
Singular noun sorts provide the individual quantification domain.

Classical `all` composes an explicit `forall(x,e,implies(restrictor(x),P(x)))`;
Constructive `all` composes a dependent product over the nominal sort. `all the`
adds an explicit contextual restriction, `in_context`, whose extension is supplied
by the context. This does not implement unrestricted plural, collective, mass,
cardinality or agreement semantics. Earlier tau-based `every` entries retain
their existing interpretation; they are not used as a shortcut for `all`.

Intersective adjective refinement projects a dependent nominal pair to its
individual before applying an object predicate. This matters for stacked
restrictions such as `all the black dogs`, and is checked by Coq regressions.

A missing closed-class entry prevents unrelated model expansion for that
sentence. Other paragraph sentences can still receive assistance. Provider
unavailability, including HTTP 429, stops further model calls for the request
while DS attempts the remaining text with available entries. The UI reports the
number of model calls, including explicitly when no model call was made.

The reported sentence `A man opens the door and all people enter the room`
completes in both native backends with zero model calls. This is a regression
result; it is not a new population coverage estimate.

## Constructions

The maintained Classical and Constructive grammars now include copular locations
(here/there/nearby/upstairs/downstairs/inside/outside; εδώ/εκεί/κοντά/μέσα/έξω/πάνω/κάτω),
English copular location PPs and Greek σε and στο/στον/στη/στην contractions,
full-clause conjunction, English VP conjunction with a shared subject, and
case/gender-checked Greek intersective attributive adjectives. These are general
families, not whole-sentence rewrites.

Positive English modals require a bare verb and introduce explicit content
operators. These operators have no supplied modal axioms, and negative modal
scope is deliberately unsupported. Past/present morphology is not interpreted
as a temporal calculus. Conjunction retains both clause derivations in LINK
structure. VP coordination chooses a compatible shared subject domain; it does
not weaken human-only predicates to accept objects.

For `A man is here`, Classical gives a location predicate of an epsilon term;
Constructive gives a Sigma witness of type man with the location property. No
location coordinate is invented. Constructive conjunction of witness types
exports as a Coq product; content operators accept Type so they can contain
Sigma witnesses without a Prop/Type universe error. Positive regression examples
are checked by Coq when available.

TTR still uses its own original grammar. This feature explicitly rejects TTR
assistance; it does not relabel a Classical or Constructive tree as TTR. A TTR
construction compiler and its independent tests remain needed.

## Limits and evidence

Paragraphs keep every source sentence and count every failure. Only completed
derivations supply discourse context; failed sentences restore context, meta
bindings, lexical entries and semantic declarations. Word traces and selected
DS rule sequences are exported. Model attempts and the actual derivation retry
history are included in JSON. Basic named antecedents work; unrestricted
anaphora and existential discourse reference do not.

The hosted worker has a 55-second deadline inside the deployment's 60-second
limit. Assisted paragraphs have 50 seconds overall, individual DS searches four
seconds, provider calls at most 22 seconds, and a shared maximum of three calls.
Ordinary paragraph mode retains the 23-second/three-second search budgets.

The six passages in `data/coverage/open-text-probe.json` are hand-written
engineering probes with both simpler prose and unsupported plural, perfect,
embedded and passive-like constructions. They are not a random sample. The
first two runs are retained beside the final results to expose schema errors
and model variability; later runs are development regressions. The earlier
Gutenberg/GDT baseline remains zero without model assistance. Neither result
supports a claim of unrestricted paragraph coverage.

Reproduce the live probe with the locally configured OpenRouter credentials:

```sh
.venv/bin/python scripts/audit_assisted_coverage.py
```

No production key or shared model cache is required. Fresh source sampling and
substantial plural, auxiliary, embedding, quotation and discourse work remain
necessary for broad accuracy.

## User-facing explanation and controls

The composer now shows the effective settings for the **next** parse. The guide
separates the deterministic DS engine, non-model lexical sources, the selected
LLM's proposals/retries, and Jev's independent lexical/search preferences. It
explains the Classical/Constructive/TTR semantic contracts and what completion
checks establish under lexical assumptions.

“Use dictionaries only” selects English dictionary/bundled mode and disables Jev
search ordering. Its Standard Greek equivalent selects the local corpus lexicon;
unsupported grammars use their original lexicon. A connected key can remain in
the tab but is not attached to requests that do not use AI. Result summaries are
based on returned provenance, not the currently selected settings. Assisted
request counts are cumulative within the paragraph up to the displayed sentence.
Model proposals, cached proposals, provider failures and Jev requests are described
separately; a completed derivation does not certify a proposed sense.

The PP guide explicitly distinguishes a **role** (modifier) from the construction
mechanism (**LINK**). English postverbal `in`/`at`/companion `with` build LINK
modifier trees with their own DP complements and opaque propositional operators.
Selected `on` and give-family `to` complements occupy ordinary required argument
slots with preposition requirements. Copular location PPs supply predicates.
Executable buttons run these cases, plus matrix/embedded attachment, with AI
turned off in either native backend. NP PP attachment, event/spatial inference,
instrumental `with`, arbitrary selected prepositions and general polysemy are not
claimed. English PP examples are not evidence of equivalent Greek/TTR coverage.

## Greek ditransitive frames and completion at the end of input

The corpus compiler and Greek LLM schema now expose the existing
`verb-ditransitive` action template. Its argument order is **subject, accusative
theme, genitive indirect object**, matching the maintained Greek grammar (the
English give templates use their separately documented argument order). Case,
clitic placement, PCC and referent resolution continue through the same rules.

The GDT index version2 records positive `obj`/Acc + `iobj`/Gen frame evidence. It
pairs that evidence with independently attested tensed singular active-indicative
forms of the same lemma. Form occurrence and frame occurrence remain separate in
provenance; this is a lexical hypothesis, not proof that all senses share a frame.
Generic obliques, clausal arguments, passive/plural forms and dependent perfective
forms are not automatically mapped to this template. The pinned training source
is unchanged; held-out text is not used. Twenty form/frame candidates were added.

`Της το έδωσε` originally chose a two-argument corpus frame, leaving `της`
unresolved. The missing third argument is now available from corpus evidence.
When all words have been consumed but the tree is incomplete, sentence/paragraph
mode also tries retained DS alternatives (at most32candidate paths) before
requesting model repair. It does not append punctuation. Successful search keeps
the real path and records rollback/replay; unsuccessful search restores the
original prefix/context. Dialogue/control inputs retain their incremental policy.
The exported `completion_search` distinguishes completion, exhaustion and limits.

Both native systems now complete `Της το έδωσε` with zero model calls and the
three-place meaning `el_dino_863958_v3(pro, theme, her)`, under the demo referents.
Tense meaning is still not modeled. With Astra, `Της το χάρισε` also completed in
both systems using one model proposal each. Tests additionally exercise repair of
an existing transitive analysis, wrong clitic order, PCC and Coq compilation.
These observations are regressions, not a new general coverage estimate.

## Destination PPs and nominal similes (2026-10-03)

The native English and SMG grammars now distinguish selected destination
arguments from LINK modifiers. Greek `verb-prepositional-se` requires σε and an
accusative destination; στο/στον/στη/στην also construct the definite DP and check
gender. A curated singular present/past inventory for μπαίνω and πηγαίνω includes
this frame and a bare alternative. The bare alternative marks its selection of
σε so a generic static-location adjunct cannot silently replace its destination
frame. The argument order is subject, destination. English exposes selected
`prepositional-to` and `prepositional-into` frames to lexical proposals; existing
ordinary direct-object frames remain available for English enter.

Greek postverbal σε and its contractions additionally build location LINKs for
other completed predicates. Their accusative DP templates retain case/gender
checks without reusing the clause-object template's incompatible VP output
filter. Common nouns inside these LINKs leave their pointer for ordinary upward
completion; existing clause noun completion still returns to the clause for
clitics. English into/onto/toward(s) introduce explicit path LINK operators. These
are semantic operators without an event calculus or spatial inference axioms.

Greek `σαν [ένα/μια/έναν] + singular adjective(s) + noun` and English
`like a/an + singular adjective(s) + noun` introduce nominal simile LINKs.
`semantic-comparison(manner_like)` composes a **CN description** with the copied
VP, preserving the original subject domain. A Classical description is a fresh
variable/restrictor pair; a Constructive description is a nominal type refined
by dependent Σ types. The article in this construction introduces no existential
witness. `manner_like(description, proposition)` does not assert a peacock's
existence or that George is a peacock. No resemblance or figurative-inference
axioms are claimed. Constructive export declares its CN argument as Type and is
checked with Coq. Greek descriptions require accusative adjective/noun agreement;
English requires its comparison article. Referential, plural and clausal similes
remain outside this extension.

The lexical model schema exposes the new selected frames and explains the
already implemented comparison constructions. It still cannot supply rules,
trees or formulas. Greek σαν is protected against open-class reclassification.
New noun/adjective hypotheses can instantiate the same comparison rules; an
incorrect lemma, sense or frame remains a lexical assumption even after DS
completion. Existing TTR grammars and their assistance boundary are unchanged.

`scripts/build_everyday_extensions.py` invokes `scripts/build_pp_extensions.py`
after rebuilding the everyday sections. Edit these generators, not just their
four generated grammar directories. The guide includes executable offline
Greek and English examples and states the interpretation limits.

Regression coverage includes the original comma-terminated Greek input,
multiple nouns/verbs, modifier orders, subject witnesses, agreement failures,
missing complements, three-sentence paragraphs, new model-frame fixtures,
Classical restrictors, Constructive Coq exports and existing clitic behavior.
These are construction regressions, not a new open-text accuracy estimate.
