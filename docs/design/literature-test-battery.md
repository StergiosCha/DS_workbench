# A literature-based test battery for the modular host

Literature and materials checked on 2026-10-29. This is a proposed scientific
target and source inventory, not a claim that the current grammar fragments
already support these datasets. The earlier 24-family synthetic pilot remains
a software/design rehearsal.

**Recommendation:** use controlled regional syntactic tests, compositional
inference, history-dependent processing, discourse manipulations and naturalistic
human reading times as separate blocks. A single accuracy or RT score would
obscure what each module contributes.

The machine-readable [selection manifest](../../data/experiments/literature-selection-v1.json)
records verified counts, source versions, downloaded-file hashes, original
prediction formulas and availability limits. Retrieved materials remain under
ignored `build/experiments/literature/`.

## 1. Controlled syntax and incremental expectations: SyntaxGym

[Hu, Gauthier, Qian, Wilcox & Levy (2020), *A Systematic Assessment of Syntactic
Generalization in Neural Language Models*](https://aclanthology.org/2020.acl-main.158/)
provides 34 suites, 33 adapted from earlier work and one novel, grouped into six
classes of syntactic phenomena. The experiments compare critical regions and
often factorial interactions rather than only whole-sentence probabilities.
Their repository supplies the actual items, regions and formal predictions.

I downloaded and inspected these **10 suites: 253 item families, 956 condition
sentences**. Counts below are verified from the JSON, not estimates from the paper.
Here “families” means item sets counted within suites. Lexical material is shared
across some suites, so 253 is not a count of independent lexical families.

| Target | Suite identifiers | Families | Conditions | Component hypotheses tested |
| --- | --- | ---: | ---: | --- |
| Garden-path disambiguation | `npz_ambig`, `npz_obj`, `mvrr` | 76 | 304 | Lexical valence, maintenance of alternatives, commitment and revision |
| Pending main clause | `subordination` | 23 | 92 | Expectations induced by incomplete dependencies |
| Filler–gap dependencies | `fgd_subject`, `fgd_object` | 48 | 192 | Licensing a gap and predicting an unfilled argument position |
| Agreement and reflexives with distractors | `number_prep`, `reflexive_prep_masc` | 38 | 152 | Feature agreement, antecedent constraints, later retrieval extensions |
| Nested predicate–argument compatibility | `center_embed` | 28 | 56 | Correct assignment of predicates to nested arguments |
| Pseudocleft completion | `cleft` | 40 | 160 | Complement category and construction-conditioned expectations |

The `center_embed` contrast exchanges the two predicates; it is **not** a clean
dependency-length manipulation. Likewise, the selected agreement/reflexive
suites test grammatical matching across distractors; they alone do not establish
human attraction effects. For that distinction, use the experimental motivation
in [Dillon, Mishler, Sloggett & Phillips (2013), *Contrasting intrusion profiles
for agreement and anaphora*](https://doi.org/10.1016/j.jml.2013.04.003).
I verified that citation, but did not obtain its participant data here.

A concrete garden-path item is:

- As the criminal shot the woman **yelled** at the top of her lungs.
- As the criminal shot, the woman **yelled** at the top of her lungs.
- As the criminal fled the woman **yelled** at the top of her lungs.
- As the criminal fled, the woman **yelled** at the top of her lungs.

The supplied prediction at *yelled* includes two simple inequalities and an
interaction: the comma should alleviate difficulty more after *shot* than after
*fled*. Merely accepting all four completed sentences does not pass this
processing test. Use the source's full criterion, not just the interaction sign.

The pinned repository version is
`43f1f86b746254406dafc89bd17b9d4976607ef6` (MIT license).
I left `fgd_hierarchy` out: its JSON has separate `<` and `=` predictions for
the same region-6 subject-gap contrast. That needs checking against the intended
paper analysis before defining a score. No source formula was silently repaired.

**Evidence boundary:** these files specify model-surprisal tests inspired by
psycholinguistics. They are not participant reading-time datasets. A parser's
search counter, number of chart edges or cue activation is not automatically
surprisal. An engine needs a normalized predictive model for that score, or a
separately declared/calibrated response model for human RT prediction.

## 2. Meaning: FraCaS, including Greek

The [FraCaS/MultiFraCaS materials](https://gu-clasp.github.io/multifracas/)
provide **346 inference problems** involving generalized quantifiers, plurals,
anaphora, ellipsis, adjectives, comparatives, temporal reference, verbs and
attitudes. They test whether a hypothesis follows from one or more premises.

This is a direct test of whether semantic and discourse components add anything
beyond constructing a syntactic representation. Relevant modules include
quantifier interpretation, reference tracking, ellipsis resolution and inference.
Preserve the distinction between *entailed*, *contradicted* and *unknown*.

The original English test-suite PDF and a Greek XML version were downloaded.
The latter has 346 problem records with Greek text, English counterparts and
additional annotations. MultiFraCaS also offers an extended Greek version.
The checked mirror revision is `580ed0a73bd125185648a7fb6cfcbc7339506851`.

Use the original FraCaS consortium deliverable (Cooper et al., 1996), with
[MacCartney & Manning (2007), *Natural Logic for Textual Inference*](https://aclanthology.org/W07-1431/)
for an explicit discussion of machine scoring. That paper identifies
degenerate/ill-defined cases and reports a restricted 183-case evaluation;
**346 source records must not be represented as 346 unproblematic scored cases**.
This suite supplies authored inference judgments, not participant RT distributions.

## 3. Memory and adaptation: preserve experimental history

Keep [Nielsen & Christiansen, *Evidence for the representation of non-hierarchical
structures in language*](https://www.nature.com/articles/s41562-025-02387-z)
as the chunk/sequence-priming block. Its [public materials](https://osf.io/ymndq/)
are already reconstructed locally: 497 participants and 26,962 retained pairs
across four studies. The small original DS coverage is a grammar-implementation
limitation, not grounds to discard the test. These data have already been
inspected, so they are a reference replication, not an untouched final holdout.

Add [Fine, Jaeger, Farmer & Qian (2013), *Rapid Expectation Adaptation during
Syntactic Comprehension*](https://doi.org/10.1371/journal.pone.0077661) to test
adaptation to changing distributions of relative-clause/main-verb structures.
Appendix S2 supplies Experiment 2 items, fillers and their block order; I
downloaded and inspected it. This is a useful manipulation for no-memory,
count-based and recency-based configurations because history changes while
grammatical licensing stays constant.

Raw participant responses for Fine et al. were not verified here. Do not claim
a fresh quantitative replication from its materials alone. Preserve exposure
order, estimate effects from available human data, and assess reliability rather
than treating the published effect size as a fixed target.

## 4. Context: vary prior discourse, retain the target construction

[Davis & van Schijndel (2020), *Interaction with Context During Recurrent Neural
Network Sentence Processing*](https://psyarxiv.com/8r65d/), has a
[materials repository](https://github.com/forrestdavis/GardenPath) containing
three useful sets: given/new status and definiteness; one versus two possible
referents; and temporal context. These adapt earlier psycholinguistic designs.

The referential materials contrast a context introducing one relevant patient
with one introducing two patients, followed by a reduced or unreduced relative
clause. I downloaded both context sets and the reduced continuations. This lets
us hold a target construction constant while testing whether discourse/reference
information changes the model's expectations.

The pinned version is `3f6a8affce3e9641fc5128103897d023569f29cf`. Repository
results are LM outputs, not human observations. The contexts are currently much
longer than the host's bounded CCG input allowance; supporting them requires a
real discourse interface rather than truncating away the manipulation.

## 5. Generalization: corrected Natural Stories

[Futrell et al. (2021), *The Natural Stories corpus*](https://github.com/languageMIT/naturalstories)
contains ten naturalistic stories with rare constructions and word-level human
self-paced reading data. Use it after controlled diagnostics, holding out whole
stories and/or participants and retaining lexical covariates and spillover terms.
Naturalistic associations alone do not isolate a syntactic mechanism.

**Use the corrected release.** The repository's 2025-05-12 notice says that SPR
data in the original release were misaligned by one position. The checked
revision `4700daad696e942f5aba23c957a7423d0de66612` includes that correction.
Earlier 2020/2021 Story 3 corrections are also documented. Preserve story/token
IDs and the forms participants actually saw. I verified the documentation and
RT-file listing; the large participant table was not downloaded in this search.

## 6. Dialogue and broad regression

For DS-specific motivations, retain a separate block of cross-speaker
completions, fragments and repairs, grounded in corpus evidence and designs
such as [Purver, Cann & Kempson (2006), *Grammars as Parsers: Meeting the Dialogue
Challenge*](https://doi.org/10.1007/s11168-006-9007-x). Its bibliographic record
was verified, but I did not obtain a ready-made normed task dataset or full text
in this search. It is a curation task, not an immediately scored benchmark.

[BLiMP (Warstadt et al., 2020)](https://github.com/alexwarstadt/blimp) is useful
as a broad supplementary licensing regression: 67 × 1,000 generated minimal
pairs with human validation on a sample. It should not replace the processing,
context or semantic-inference blocks, and sampled validation is not validation
of every generated pair.

## How to use this battery fairly

1. Freeze phenomenon coverage and source versions before extending the grammars.
   Do not define the scientific benchmark by the strings the toy fragments happen
   to recognize today. Begin with a declared diagnostic subset, retaining a
   separate development partition by lexical family/template.
2. Keep whole condition families together in splits, grouping shared lexical
   material across related suites as well as within each suite. Preserve critical regions,
   empty gap regions, punctuation, context and exposure order. Record adaptation
   histories exactly; random sentence shuffling destroys the manipulation.
3. Separate grammatical rejection, unknown vocabulary, search limits and missing
   mechanisms. Report both coverage and performance on a common supported sample.
   A negative item cannot earn credit merely because its words are unknown.
4. State each configuration's observable prediction: licensing, regional
   expectation, calibrated RT, exposure interaction, reference interpretation or
   entailment. Report these outcomes separately and show ablations within each
   compatible component combination.
5. Compare mechanisms, not tradition names. HPSG/LFG/CCG can be given incremental
   processors; DS is not the only architecture capable of incrementality. Two
   frameworks with the same observable predictions on an item are not
   distinguished by that item. Equal finite-sample scores also do not prove
   formal equivalence.
6. Keep direct LLM/Jev judgments, assisted symbolic configurations and unaided
   symbolic configurations separate. Public benchmark success does not establish
   performance on material unseen during model training. Human responses remain
   the criterion for cognitive adequacy.

The first implementation target should therefore be the **10-suite controlled
block plus a declared FraCaS subset**, with separate priming/context and human-RT
tracks. Add the curated dialogue block as its own experiment. This changes the
workbench from a collection of compatible analyses into a platform that can
expose differences in their empirical predictions.
