# Svarna and Triantafyllidis as lexical evidence during DS parsing

Status: first runtime integration implemented on 4 October 2026. The native
Standard Greek Classical and Constructive assistance paths can now retrieve
bounded source evidence for model proposals. The longer-term extensions below
remain proposals; no Svarna-side API or general morphology service was added.

## Implemented first delivery

The opt-in `live_greek_sources` request flag is available for assisted sentences
and paragraphs. `greek_source_corpus` selects `ud_ud_greek-gud` (default) or
`ud_ud_greek-gdt`. Other semantic systems, dialects and dialogue reject this
option. The browser explains the source queries and model disclosure before
enabling it. Source calls occur only when lexical model assistance is needed.

`greek_lexical_evidence.py` retrieves observations for at most four forms, up to
two candidate lemmas each, within an eight-second budget shared by the request.
Dictionary entries and concordances remain distinct from inferred lexical
frames. Validated server-issued evidence references survive compilation and
JSON export. The per-word **Why this analysis?** panel displays the observations,
inferences, missing results and unavailable sources. References are checked for
existence and surface association, not independently for linguistic relevance.

The request-local cache stores observations and failures, not promoted grammar
entries. A grammar-complete input can avoid both retrieval and model calls;
source outages do not turn incomplete DS derivations into verified results.
Source text and citations cannot override morphology or semantic compilation.

Live probes exposed a source limitation: Parliament returned zero for `και`,
`κυβέρνηση` and `έδωσε`; Europarl timed out. The small GDT and GUD filters
returned examples and are the initial choices. Their original split/record IDs
are absent from search responses, so these analyses cannot be counted as unseen
GDT/GUD evaluation. No new broad-coverage accuracy claim accompanies this feature.

## Source capabilities checked

Svarna's live OpenAPI exposes concordance search, collocations, n-grams, word
frequency, register comparisons and other corpus statistics. Search accepts
corpus, register, mode and speaker filters. Its current collocation endpoint
accepts a database and window size, but no corpus/variety filter. Database-wide
collocations must therefore not be reported as evidence for a specific dialect.
There is no documented lemma/morphology/dependency lookup endpoint in this API.

The live Triantafyllidis entry for `δίνω` (entry `1_10840`) provides irregular
forms, senses and examples. For instance, its header lists the active aorist
`έδωσα` and passive `δόθηκα`; examples include a giver, a transferred thing and
a recipient. These are useful lexical observations. The entry is HTML/prose,
not a machine-readable DS valency declaration or a full inflection engine.

An unrestricted Svarna search for `έδωσε` exceeded a 25-second probe limit.
Metadata and dictionary requests responded. A runtime integration must budget
retrieval separately, cache suitable public evidence and continue honestly when
a source is unavailable.

A subsequent query limited to the GDT corpus succeeded: seven matching
sentences, with three requested examples returned. Their fields were
`left_context`, `keyword`, `right_context`, `full_text`, `corpus`, `register`,
`mode`, `year` and `metadata`; the latter two were empty in these examples.
No original sentence ID, lemma, morphological features or dependency edges
were returned. Examples included `έδωσε στη δημοσιότητα τα ονόματα` and
`Αυτή η νίκη έδωσε στη Μπενφίκα την πρόκριση`, illustrating why lexical sense
and frame cannot be fixed from the surface verb alone. These observations are
not a new parsing evaluation.

## Proposed processing path

1. **Analyze the surface form.** Use known GDT mappings and a morphology layer
   to produce candidate lemmas/features. Retain ambiguities and the source of
   each claim. A model-generated lemma is a hypothesis until independently
   supported; stripping Greek endings is insufficient.
2. **Retrieve evidence.** Look up candidate lemmas in Triantafyllidis and fetch
   a small, relevant set of Svarna concordances for the observed form and
   supported alternatives. Keep corpus/variety/register metadata. A Standard
   dictionary can supply a gloss for a dialect form only when the relationship
   is supported; its morphology cannot silently replace the dialect's.
3. **Build lexical candidates.** Machine-readable features and reviewed mappings
   can instantiate existing templates without an LLM. Where the sources provide
   prose, an optional model proposes structured sense/frame/morphology analyses
   constrained by that evidence. Extracting an argument frame from an example
   is still an analysis, not a quoted source fact.
4. **Compile for the selected grammar.** Classical and Constructive use their
   existing separate semantic compilers. Validate arity, roles, nominal typing,
   morphology and supported constructions. TTR needs its own lexical compiler;
   Greek TTR support additionally needs suitable Greek construction resources.
5. **Run DS and retain alternatives.** Evidence may influence candidate ordering
   but must not erase alternatives or satisfy open requirements by assertion.
   A frequent neighboring PP does not establish that it is a selected argument.
6. **Report and reuse.** Display which observations were retrieved, which claims
   were inferred, which lexical program was tried and whether DS completed.
   Keep request-local proposals separate from reviewed reusable lexical entries.

An evidence item needs a source/entry identifier or content fingerprint, URL,
retrieval time, query, source text span, variety/register and relevant data-use
metadata. A lexical candidate needs sense identity, morphological alternatives,
frame/role hypotheses, evidence references, extraction method and target grammar.
The application must validate cited evidence IDs itself; a model must not invent
source links or silently turn its explanation into an attestation.

## Application changes

Add an explicit **Use Svarna + Triantafyllidis during parsing** option. The first
implementation should augment the native Standard Greek assistance path and
show a per-word **Why this analysis?** panel. Source queries should send the
necessary words/lemmas, not automatically upload the entire user paragraph.
The selected model receives relevant excerpts with the lexical task and failure
state; retrieved text is data, never executable instructions.

The implementation points are `research_sources.py` for bounded retrieval,
a new evidence/lemma layer, `Assistance.propose()` for evidence-aware proposals,
the existing lexical compiler/installer, and the browser's lexical report/export.
Lookup failures must remain distinguishable from zero results. A cache key must
include lemma/form, filters and source identity; parse success is not a reason
to mark a candidate linguistically reviewed.

The more durable Svarna-side extension is an annotation-aware lexical endpoint
returning surface form, lemma, UPOS/features, available dependency relations,
source sentence IDs and split/provenance metadata. For imported UD material,
preserve the original annotations where available. For unannotated corpora,
label automatic analyses and their model/version rather than implying manual
annotation. This would let Svarna supply a broader deterministic lexical service
instead of requiring the DS app to ship one small GDT export.

Triantafyllidis can enter through bounded lookup first. Any later mirrored index
or bulk redistribution needs the dictionary's own data-use terms assessed; the
GDT license says nothing about that separate source.

## Verification and promotion

Compare grammar/GDT alone, retrieved evidence without a model, model alone, and
model plus retrieved evidence on the same frozen inputs. Measure correct
lemma/sense/frame, semantic roles, DS completion, latency and provider cost
separately. Include PP argument/modifier contrasts, clitic valency, homonyms,
dialect mismatches and deliberately irrelevant evidence.

Hold-out separation must extend to live retrieval. Svarna's GDT corpus cannot
be assumed training-only: an evaluation passage or its annotation must not be
retrieved from another copy of the same source and then counted as unseen.
Track source IDs/splits and exclude evaluation records from retrieval, cached
candidates and reviewed-entry promotion.

This integration supplies evidence and lexical candidates. Broader grammar
coverage still requires explicit DS constructions and semantic validation.
