# Dynamic Syntax: theoretical coverage and an implementation programme

Research and source-code audit, 6–7 October 2026. This is a first substantial
evidence map and a working implementation programme. It distinguishes a
published analysis, a proposal, an implemented fragment, and a demonstrated
meaning. These are different achievements.

The companion `ds-theoretical-coverage.json` is the machine-readable catalogue.
The bibliography below identifies the versions actually inspected. Source
keys such as **[CKM05]** refer to those entries. A source's discussion of a
phenomenon does not make that phenomenon implemented in this workbench.

## 1. Findings that change our development strategy

DS has a substantial theoretical literature extending far beyond incremental
subject–verb–object parsing. It offers analyses of discontinuity, restrictive
and nonrestrictive relatives, resumption, scrambling, agreement, clitic
placement and person restrictions, copular constructions, ellipsis, and
interactive dialogue. There is also computational work on grammar induction,
generation, semantic updating, and feedback.

The central organizing principle is **reusable mechanisms with
language-specific lexical conditions**. A catalogue of isolated words such as
*because*, *when*, or *who* is therefore the wrong development unit. A useful
unit is a construction family with specified tree operations, semantic
composition, context assumptions, locality conditions, and failure controls.

Four findings are particularly consequential for this project:

1. **LINK is not a single semantic operation.** Restrictive relatives,
   nonrestrictive relatives, coordination, topic structures and adjuncts can
   all use LINK, but their evaluation differs. Reusing an edge type without
   specifying how meanings combine does not implement the analysis.
2. **DS is not inherently TTR.** The 2021 overview explicitly distinguishes
   tree-growth machinery from the representation of semantic content
   [HG21, §2.1, p.265]. Classical terms, TTR records, distributional semantics
   and the later Constructive proposal represent different choices. Sharing
   a parser does not establish semantic or grammatical parity.
3. **Theoretical breadth is not an off-the-shelf broad-coverage grammar.**
   The 2011 DyLan paper reports an implemented range of constructions, but
   also a small lexicon and limited coverage [PEH11, §§3,5]. That historical
   implementation claim cannot simply be inherited by a Python port or by
   a different semantic backend.
4. **A valid derivation is insufficient evidence of the intended meaning.**
   Type correctness, referent identity, argument roles, quantifier scope,
   modifier attachment, contextual licensing and lexical sense all need
   separate checks. Our LLM-assisted system currently addresses only some
   of these obligations.

The first implementation from this map is now a named-head nonrestrictive
relative family in native English Classical and Constructive DS. It follows
the explicit LINK/copy/MERGE/conjunction analysis in [CKM05, §3.1] and [HG21,
§2.5.1]. English restrictive relatives already existed; conflating their
restrictive semantics with the new supplemental assertion would be an error.
Greek relatives and a TTR parity audit are separate next work items.

## 2. Research method and evidence boundaries

### Search and selection

The review began with the core DS book, the four-dialect Greek-clitic thesis,
and their references, then added the 2021 framework overview, published
DS-TTR implementation papers from ACL Anthology, the ellipsis chapter,
interaction work, modification proposals, and the 2025 Constructive article.
Crossref was used for publication metadata and discovery. Author bibliographies
and references supplied further leads. The local archive contained both
complete documents and empty cloud placeholders; only readable documents
were used as evidence.

Direct sources include a complete 386-page prepublication book, a 396-page
thesis, journal articles, chapters, and computational papers. Review was
targeted: contents and relevant chapters/sections were inspected, not every
page of every document. Full source texts remain outside the repository;
the catalogue records retrieval locations and review scope. The bibliography
includes publicly resolvable links where available.

This is a structured, citation-led review, **not an exhaustive systematic
review of every DS publication**. Search engines and the project website were
not consistently accessible; primary publisher/ACL downloads and the local
archive provided the usable evidence. A 2026 handbook chapter was identified
through metadata but not reviewed. Its existence is recorded as a follow-up,
not treated as proof of additional construction coverage.

### Evidence labels

| Label | What it establishes |
|---|---|
| Worked analysis | Inspected rules, derivation, or explicit semantic treatment for the relevant mechanism. It can still cover a small fragment. |
| Implemented study | A source reports executable parsing, generation or learning. Its original conditions and evaluation remain attached to the claim. |
| Proposal or sketch | A mechanism is motivated or outlined; details or a full derivation remain open. |
| Secondary pointer | A reviewed source identifies another analysis; that underlying publication still needs direct inspection. |
| Metadata only | Bibliographic existence is verified; substantive claims are not drawn from it. |

Implementation labels are independent: **tested fragment**, **partial
infrastructure**, **not implemented in the native workbench**, and **not yet
audited**. In particular, “not yet audited” is the right label for many
inherited TTR capabilities. It must not silently mean either full support or
absence of support.

### Scope of the code audit

The implementation map uses maintained grammar files, atomic effects, design
notes and tests. Important locations include `relative_effects.py`,
`semantic_effects.py`, `causal_effects.py`, `native_dialogue.py`, the native
grammar directories, the `2015-english-ttr` grammar, and the semantic modules.
Older coverage plans are historical evidence, not current feature inventories.
The catalogue's file links provide starting points for reproducing the audit.

## 3. A mechanism-based taxonomy

The following eighteen categories separate construction families from their
semantic representations. Languages are those discussed in the cited
analyses; they are not a list of languages the app currently parses.

### C01. Core incremental growth and lexical programs

**Theory.** Types and formulae decorate binary semantic trees. Requirements
state what remains to be built. Lexical programs and computational operations
update the pointed tree. Introduction, prediction, anticipation, completion,
thinning and elimination provide basic growth [CKM05, ch.2; HG21, §§2.1–2.3].

**Current implementation.** The package supplies tree operations, action
parsing, requirements, a context DAG and backtracking. Native semantic effects
add backend-specific type checking and composition. Recorded operations drive
the browser visualization.

**Next obligation.** Treat action traces as testable derivation evidence.
Check the intermediate type and formula state, not only the final result.
Failure under a bounded incomplete grammar is not an independent judgment
that a natural-language sentence is ungrammatical.

### C02. Nominals, reference, quantification and scope

**Theory.** [CKM05, §§3.2–3.3] develops structured nominal terms, restrictive
content, epsilon/tau-style term operators and scope constraints. [C25,
§§3–4.2] replaces this semantic machinery with many-sorted dependent types,
Σ/Π and coercions. These are materially different analyses, not alternate
print styles for one formula.

**Current implementation.** Names, selected determiners, singular count nouns,
contextual definites, intersective refinements and limited quantifier scope
work in native English. Distributive *all* with plural forms denotes
individual-level quantification. Greek has a smaller case-sensitive DP
inventory. General possessives, mass/count interpretation, numerical
quantification, bare plurals and collective/cumulative readings remain gaps.

**Next obligation.** Separate reference identification from existence
assertions. A contextual definite must not become a fresh arbitrary constant
without an exposed assumption. Build tests that distinguish one shared
existential from a separate existential per universal.

### C03. Predication, valency and copular families

**Theory.** DS lexical programs project predicate–argument structure.
[CKM05, ch.8] treats predicative, existential *there be*, equative and
specificational copulas through underspecification and contextual update.
These are several related constructions, not one semantically empty *be*.

**Current implementation.** Native active intransitive/transitive and selected
ditransitive, dative, clausal and PP-complement frames work. Nominal and
adjectival copulas and selected locations are present. Corpus/WordNet
occurrences propose frames; they do not establish exhaustive lexical valency.
General existential *there*, equative and specificational analyses are absent
from the native coverage claim.

**Next obligation.** Implement *there be* as a sourced referential and
predicational analysis with explicit contextual conditions. Merely ignoring
*there* and accepting the remaining noun phrase would not reproduce ch.8.

### C04. Flexible order, case and discontinuity

**Theory.** Unfixed positions, local and general adjunction, case filters
and MERGE capture delayed placement without moving a previously fixed
constituent. [CKM05, §§2.4–2.5, ch.6] develops this for dislocation and
Japanese scrambling. [HG21, §2.4] explains why two nodes with the same
unfixed address cannot remain distinct.

**Current implementation.** Unfixed nodes and address constraints exist;
reviewed Greek case-marked names support several orders. A finite set of
working orders is not a complete scrambling grammar.

**Next obligation.** Test incremental availability and incompatible case
combinations. Add multiargument and embedded cases only with explicit
locality conditions. Japanese/Korean analyses inform mechanisms but are not
evidence that identical Greek or English lexical programs are correct.

### C05. Relatives, resumption, extraction and islands

**Theory.** [CKM05, chs.3–4] gives nonrestrictive and restrictive relatives,
crossovers, and cross-language resumption patterns. A LINK can originate at
an identified individual or inside a nominal restriction. The copied term
and evaluation point differ. The dominance relation used for a gap does not
automatically cross LINK boundaries [CKM05, §3.1.2, p.80].

**Current implementation.** Native English has restrictive subject/object
gaps with LINK, head copying and MERGE. This increment adds named-head
nonrestrictives. The existing restriction to local subject/direct-object
gaps remains. Greek `που`, clitic resumption in relatives, PP gaps and
unbounded extraction are not covered by these entries.

**Next obligation.** Greek `που` must interact with case, pro-drop and clitics;
it cannot be an English *who* alias. English nonlocal relatives require
explicit intervening-clause and island tests. Do not turn off locality checks
to make a difficult example pass.

### C06. Modification: adjectives, adverbs, PPs and comparison

**Theory.** There is no single settled DS implementation for all modifiers.
[C17] explicitly describes the earlier literature as sparse and contrasts
in-tree adjectival refinement with LINK treatments. It proposes different
attachment levels for sentence, VP and temporal adverbs. [C25, §§4.4–4.5]
works through dependent adjective refinements and adverbial LINK options.
[PEH11, §2.1] demonstrates event-related record extension in DS-TTR.

**Current implementation.** Native intersective adjectives, selected adverbs,
PP argument frames, PP modifiers and nominal comparisons exist. Selected
arguments satisfy a verb's explicit requirements; modifiers build additional
LINK structure. Present temporal modifiers retain an opaque contribution;
they do not supply a full event/time calculus.

**Next obligation.** Establish event and situation semantics before claiming
general temporal, manner, agent-oriented or speech-act modification. Preserve
attachment alternatives. Subsective/intensional adjectives, degree semantics
and clausal comparison need separate treatment from intersective adjectives
and nominal similes.

### C07. Coordination and shared material

**Theory.** [CKM05, §§5.4,7.3–7.4] combines LINK, contextual sharing and
late adjunction for coordination, right-node raising and agreement effects.
Right-node raising involves additional assumptions about intonationally
licensed update; it is not demonstrated merely by a conjunction lexical item.

**Current implementation.** Selected clause and VP coordination work in the
native fragments. General NP coordination, gapping, right-node raising,
shared complements and their number interpretation are not implemented as
a full family.

**Next obligation.** Separate proposition conjunction, predicate conjunction,
group-forming nominal coordination and shared-argument composition. Use
positive/negative pairs that expose argument duplication, omission and
accidental sharing.

### C08. Anaphora, binding and contextual dependencies

**Theory.** Metavariables receive content through constrained substitution
[CKM05, §§2.5,3.1.3–3.1.4; HG21, §2.4.3]. Reflexives impose local conditions;
personal pronouns can depend on wider context. Context can include partial
trees and action histories, not just a list of previously mentioned names.

**Current implementation.** Selected speaker/hearer references, named
antecedents and local English reflexives are available. The app exposes
assumed antecedents. This does not establish discourse salience, donkey
anaphora, plural antecedents, arbitrary logophoricity or binding across every
construction.

**Next obligation.** Store multiple antecedent candidates with provenance,
number/person/case constraints and scope accessibility. A model may rank
compatible candidates; it must not erase binding constraints or turn a
guessed antecedent into a verified fact.

### C09. Clitic placement, clusters and person restrictions

**Theory.** [C10, chs.3–6] analyzes Standard Modern, Cypriot, Grico/Grecia
Salentina and Pontic Greek. [CK11] develops person restrictions through
the timing of fixing underspecified structure. Case can trigger immediate
structural enrichment before another unfixed node is introduced
[CK11, pp.144–145].

**Current implementation.** The workbench contains reviewed placement
fragments for four varieties, with more developed SMG/Grico clusters,
ditransitives and strong PCC controls. Those supported lexical programs do
not cover all claims or variants in the thesis.

**Next obligation.** Extend by construction environment and source example,
including contrasting person combinations. Dialect labels must identify
distinct grammars rather than spelling substitutions. A shared finite-verb
template does not establish a shared clitic system.

### C10. Auxiliaries, restructuring, tense, aspect and voice

**Theory.** The core book explicitly sets passive/progressive aside at the
start of ch.8. Later work must therefore be consulted. [C10, §3.4.3.2,
pp.143–146] develops clitic climbing by treating auxiliaries/restructuring
predicates as contributions to a complex situation argument rather than
ordinary independent biclausal predicates. It refers to the work later
published as Cann's 2011 English auxiliary chapter. [KC16] also points to
that chapter for passive-related structural conditions.

**Current implementation.** Native do-support, selected modal operators,
Greek finite forms and several particles do not amount to tense/aspect or
voice semantics. General passive, progressive, perfect, raising/control
and restructuring are not in the native broad-coverage claim.

**Next obligation.** Obtain and inspect Cann (2011) and the relevant
restructuring derivations in full. Build an event/situation representation,
then implement auxiliary sequences and role mappings. Do not implement
passive simply by swapping two strings in an active predicate.

### C11. Clause linkage: causal, temporal, conditional and concessive

**Theory.** The literature includes a dedicated conditional thesis
(Gregoromichelaki 2006, identified in [HG21] and [KE19]) and treatments of
Greek subordination and clitic triggers [C10, §§4.6–4.7]. These establish a
research route, not equivalence between every connective and conjunction.

**Current implementation.** The app now has a reusable finite-clause family
with distinct causal, temporal, conditional, concessive and contrastive
relations, preposed/postposed orders and local content closure. Relations
are opaque, typed predicates over contents. They do not compute temporal
order, counterfactuality, causation, concessive expectations or conditional
entailments.

**Next obligation.** Review the conditional analysis directly. Connect
construction choices to a developed semantics and context model. Until then,
LLM selection of *since* as temporal or causal remains a lexical/contextual
hypothesis, even when the DS derivation completes.

### C12. Ellipsis and fragments

**Theory.** [CKM05, §9.2; KE19, §§1.2–1.3; PEH11, §3.2] distinguish
formula reuse, action rerun and continuation of an existing partial tree.
These support strict/sloppy VP ellipsis, fragment answers, corrections and
other contextual dependencies. [C25, §4.3] proposes a typed history of DS
actions and an explicit rerun example.

**Current implementation.** Shared continuation and local repair exist, but
they are not a general implementation of VP ellipsis, sluicing, nominal
ellipsis or strict/sloppy alternatives. The native pipeline does not yet
retrieve and validate a typed reusable predicate history for arbitrary *does
too* examples.

**Next obligation.** Begin with named-subject predicate reuse, then distinguish
strict formula reuse from sloppy action rerun. Freshen witnesses and rebind
indexicals correctly. An ellipsis resolver must fail when no licensed
antecedent is available; it must not invent missing content with an LLM.

### C13. Questions, split utterances, repair and grounding

**Theory.** [KC16; KE19; E15] analyze dialogue through incremental structure,
action histories and participant-dependent contexts. [E15, §§2.3–3.2] adds
self/other coordination pointers to model feedback and clarification. These
are distinct from the semantic tree's construction pointer. The model's
*no* can signal branch abandonment, not necessarily propositional negation.

**Current implementation.** Native English supports a bounded shared polar
question/reflexive/answer fragment, speaker changes, continuation and local
repair. The screen's shared tree is not a complete model of two participants'
grounding states or knowledge. Wh-question interpretations, clarification
subtypes and nonlinguistic grounding are mostly missing.

**Next obligation.** Make context histories and participant commitments
explicit. Add short-answer and clarification families with answer-type and
binding checks. Preserve repaired material and distinguish a new proposition
from continued growth of the current tree.

### C14. Information structure and peripheral constructions

**Theory.** [CKM05, §§4.2,5.1–5.3] analyzes left topics, focus-related
alternatives, right dislocation, extraposition and late adjunction. [HG21]
provides secondary pointers to Japanese/Rangi clefts and Japanese multiple
focus analyses.

**Current implementation.** Initial named Greek topics have a small
executable fragment. General hanging topics, afterthoughts, clefts and
prosodic licensing are not broadly implemented. A structural strategy label
in the UI is not an independent topic/focus or discourse-felicity judgment.

**Next obligation.** Pair form with discourse assumptions and information
structure. Keep structural alternatives available when the same word order
supports different analyses. Read the cleft papers before generalizing from
the topic fragment.

### C15. Agreement, plurality and typological tests

**Theory.** [CKM05, ch.7] derives order-sensitive full and partial agreement
for Swahili conjoined nominals; singular/plural and noun-class information
interact with when structure becomes fixed. [HG21, §§2.4,3] points to Rangi
auxiliary order, Japanese case, Korean incrementality, Kazakh differential
object marking and Mandarin minimizers.

**Current implementation.** These languages are not active workbench
grammars. Selected Greek person/number/case restrictions and English
distributive plurals are much smaller claims than full agreement and plurality.

**Next obligation.** Use these analyses as stress tests of general mechanisms.
Do not introduce universal rules from English or Greek alone. Distinguish
lexical morphological annotation, agreement licensing and semantic plurality.
The secondary pointers need direct-source review before implementation.

### C16. Historical development and variation

**Theory.** [C10] connects changing clitic placement to routinization and
generalized parsing triggers. [HG21] identifies related work on Greek and
Spanish change. These are explanatory historical proposals with empirical
corpus conditions, not executable grammars for every historical stage.

**Current implementation.** Historical panels explain a sourced account;
the four modern fragments are executable. The panels should not be read
as demonstrations that Koine or medieval sentences can be parsed generally.

**Next obligation.** Encode a stage-specific lexicon and distributional
evidence before offering historical parsing. Distinguish alternative
historical hypotheses and register/period constraints.

### C17. Learning, search and generation

**Theory.** [EPH13] learns lexical action hypotheses from utterances paired
with semantic trees, using DAG intersections and probability estimates.
[ECH13] extends the research to child-directed dialogue data. [PEH11; E15]
describe parsing/generation over shared incremental representations.

**Current implementation.** The app searches a reviewed action inventory,
optionally expands lexical entries with bounded model proposals, and uses
Jev for lexical preferences. This is not the grammar induction algorithm
from the literature. Source lookup is not training, and a replay accepting
an alternative is not a learned grammar update.

**Next obligation.** Establish an adjudicated semantic dataset before any
learning claim. Compare dictionary-only, model-assisted and Jev-ranked runs
with matched inventories and budgets. Report accuracy separately from
completion, abstention, latency and cost.

### C18. Semantic architectures and interfaces

**Theory.** [HG21, §2.1] makes representational flexibility explicit.
[PEH11; E15] show TTR records, manifest fields, dependencies, subtyping and
event-related enrichment. [C25] develops nominal types, coercions, dependent
quantification and action contexts. [KV19] is a short distributional-semantics
proposal; it is not a specification for our native backends.

**Current implementation.** Classical and Constructive modes share execution
but compile separate native meanings. The TTR path uses its own record
algebra and inherited grammars. There is no general translation from completed
native formulae into faithful TTR analyses, or vice versa.

**Next obligation.** Define a semantic contract per construction and backend:
roles, reference identity, dependency scope, available inference and retained
partial information. “Same sentence accepted” is weaker than equivalence.

## 4. Cross-backend implementation obligations

| Area | Classical and Constructive obligations | TTR obligation |
|---|---|---|
| Nonrestrictive relative | Share the identified head; keep supplemental assertion separate from nominal restriction; close local witnesses. | Reuse the head's referent/path; preserve dependencies when merging records; avoid freshening the shared individual away. |
| Restrictive relative | Classical CN predicate conjunction versus Constructive dependent nominal refinement. | Extend the appropriate restrictor record before reference/quantification; do not flatten it into matrix assertions. |
| Ellipsis | Typed predicate reuse or validated action rerun; distinguish binding and witness freshness. | Preserve record dependencies and intended shared fields while freshening only new referents/events. |
| PP/modifier | Identify selected slot versus adjunct; preserve attachment and eventual event/situation scope. | Add role/event constraints to the right record or LINK structure; record extension alone must not choose an attachment silently. |
| Clause relation | Distinct locally closed contents; event, modal and discourse semantics where claimed. | Keep clauses and event identities distinct; do not flatten dependent clauses into one undifferentiated record. |
| Dialogue | Participant-sensitive reference and accessible action histories; explicit repair boundary. | Record/context updates plus participant coordination state; distinguish tree pointer from grounding pointers. |

TTR is not an inferior or intrinsically nonconstructive interpretation.
Likewise the workbench's label “Constructive” names a specific implemented
MLTT-inspired proposal; it is not a claim that every other type-theoretic
approach lacks constructive content.

## 5. First implementation: supplemental relatives

The initial implementation follows [CKM05, §3.1.1–3.1.2, especially (3.6),
(3.9), (3.13)]. The source uses “John, who Sue likes, smokes.” Our existing
vocabulary gives an analogous executable example:

```
John, who Mary knows, walks.
  main:       walk(john)
  supplement: know(mary, john)
  result:     walk(john) ∧ know(mary, john)
```

The opening comma starts a LINKed proposition from the identified head.
The relative pronoun copies the head to an unfixed node; MERGE fixes it at
the subject or direct-object position. A closing delimiter requires the
relative to be complete before returning to the matrix. Final LINK evaluation
conjoins the propositions. The original relative subtree remains inspectable.

In Constructive mode an internal indefinite stays local:

```
John, who knows a woman, walks.
walk(john) ∧ Σ x:woman. know(john, x)
```

It must not become `Σ x:woman. (walk(john) ∧ know(john,x))` merely because
the engine carries witnesses while composing. The implementation closes each
proposition before conjunction. Classical mode instead retains its local
epsilon term. The Constructive adaptation is ours, tested using the existing
native term system; the Classical source is not misrepresented as an MLTT
specification.

The tests cover both gap positions and both matrix argument positions;
negation and modifiers in the matrix or relative; local indefinites;
shared identity; recorded LINK/unfixed/MERGE/return operations; malformed
and unsupported cases; and alternative complete analyses. Constructive
exports are compiled with Coq when installed. This checks exported typing,
not empirical truth or grammatical acceptability.

The implementation also fixes propagation of an adverb's updated meaning:
recomputation stops at a relative's LINK root instead of walking through the
inverse LINK and erasing the nominal host. Sealing after supplemental
evaluation prevents a later return to the original matrix VP from discarding
the extra assertion.

Scope is explicit: main-clause identified constant heads, local subject/direct
object gaps, `who`/`which`, written delimiters, supported negation/adverbs and
internal indefinites. Quantified hosts, general definite descriptions, Greek
`που`, extraction across embeddings, animacy selection and supplement
projection through content-taking clauses remain outside this increment.
The latter combinations are blocked rather than assigned an unchecked
projection analysis. See `docs/design/nonrestrictive-relatives.md`.

## 6. Prioritized implementation programme

### P0. Evidence and semantic regression infrastructure — started

Maintain this catalogue as the single theory-to-code index. Every feature
gets a source key, precise passage, theoretical status, target language,
backend obligations, context assumptions, positive meanings and negative
controls. Store authored examples separately from published judgments and
held-out evaluation data. Existing small coverage numbers remain historical
baselines; this review does not update them by assertion.

**Exit criterion:** a proposed coverage claim can be traced from a source to
an executable derivation and its expected meaning, without reading a chat log.

### P1. Relative family and reference — first English increment complete

Follow with a sourced Standard Greek `που` fragment, including head case,
clause-internal role and pro-drop/clitic interactions. Extend English
nonrestrictives only after specifying definite/quantified hosts and
projection. In parallel as a workstream, audit existing TTR relative programs
against the same identity and role cases; this is a plan for subsequent work,
not a claim that this audit has already been performed.

**Exit criterion:** meaningful positive and locality/binding controls in both
native systems for each advertised language; separate TTR results reported.

### P2. Contextual predicate reuse and ellipsis

Implement an accessible typed predicate-history interface. Begin with
`John knows Mary. Bill does too.` Then add reflexive/possessive contrasts
that distinguish strict from sloppy readings. Use [KE19], [PEH11] and
[C25, §4.3], not a free-text model completion.

**Dependencies:** context accessibility, variable freshening, scope-aware
reference, repeatable action replay. **Exit criterion:** correct changed
subject, preserved object, no witness leakage, and refusal without an
appropriate antecedent.

### P3. Nominal coordination, possessives and common determiners

Develop a number/reference representation that can support coordinated NPs
without confusing them with proposition conjunction. Review fuller nominal
analyses for possessives, numerals, mass/count interpretation and plural
readings. The Swahili agreement chapter supplies valuable structural tests,
but does not by itself specify all English/Greek nominal semantics.

**Exit criterion:** distinguish distributive and collective interpretations
where supported, and do not accept the latter under an individual-only
encoding. Keep unsupported reading classes visible.

### P4. Events, auxiliaries, voice and selected complements

Directly review Cann (2011), Marten (2002), and the restructuring/clitic
climbing sections. Implement a minimal event/situation layer with explicit
reference-time assumptions. Add perfect/progressive/passive families and
case/role mappings on that basis. Distinguish control, raising and ordinary
finite complementation rather than assigning one generic clausal frame.

**Exit criterion:** tense/aspect contributions survive composition;
passive agent/theme roles are checked; incompatible auxiliary combinations
fail; native and TTR semantics each satisfy their own contracts.

### P5. Questions, answers and agreement

Broaden wh-dependencies, short answers and clarification using context
histories. Extend Greek person/number/case coverage and English agreement
where it conditions acceptance. Use minimal contrasts and independently
sourced restrictions. Dialogues must be evaluated as sequences with speaker
and context state, not only as concatenated sentences.

### P6. Clause semantics and discourse attachment

Replace unsupported semantic claims with developed analyses of temporal,
conditional and causal content. Inspect the conditional thesis directly.
Add argument-versus-adjunct and attachment alternatives to evaluation.
General causal reasoning or counterfactual inference should not be advertised
because the syntax accepts an opaque `condition(main, antecedent)` term.

### P7. Wider typology and empirical scale

Expand dialect and historical fragments from source judgments; directly
review the Rangi, Japanese, Korean, Kazakh and Mandarin pointers before coding them.
Use the resulting diversity to test the general machinery. Scale lexicon
coverage and search only after constructing reliable semantic tests.

Priority is based on reusable coverage and current prerequisites, not on a
claim that every missing analysis is equally mature. P2–P6 can be developed
in separate feature branches as resources permit, but each family retains
its own entry and exit criteria.

## 7. A meaningful role for the LLM and Jev

The larger models are useful for proposing lexical analyses, identifying
candidate construction families, retrieving relevant evidence, suggesting
counterexamples and diagnosing a failed derivation. They do not supply a
verified DS analysis simply by producing a plausible description.

The proposed operational path is:

1. Inspect tokens, current tree, accessible context and the reviewed
   construction inventory for the selected language/backend.
2. Propose a typed lexical entry, an existing construction/reading choice,
   or an explicit unsupported-construction diagnosis with evidence.
3. Validate that proposal against the selected compiler and grammar contract.
4. Execute DS and inspect requirements, identity, role and scope invariants.
5. Retain alternative analyses, uncertainty, sources, model calls and failed
   attempts in the result.

For new grammar development, an LLM can draft action programs and tests in
the repository, but adding a reviewed family is a software/research change,
not something silently approved during an end user's parse. Runtime model
proposals remain bounded by the implemented inventory.

Jev's current useful role is to rank compatible lexical senses as context
arrives. Future uses include ranking compatible attachment/antecedent
candidates and deciding when to abstain, after calibration. These would be
new features. The current implementation must not be described as already
providing them. Typed probabilities are preferences, not proofs of truth,
grammaticality, or correctness of the chosen DS analysis.

The new nonrestrictive relative family works without the LLM because the
missing resource was a construction program. With that program present,
existing lexical assistance can supply eligible content words. This is how
the formal grammar and models can contribute different, measurable things.

## 8. Evaluation: what broad coverage must mean

Use three distinct datasets:

- **Source-linked construction suites:** positive meanings and sourced
  contrasts, with dialect/context conditions. Authored regressions are
  marked as such. These establish targeted implementation behavior.
- **Development text:** natural sentences/passages used while engineering
  the grammar. Useful for error analysis; not an unbiased coverage estimate.
- **Frozen held-out text:** independently sampled English and Greek, with
  declared sampling unit, source/register, license and split. Do not add
  failed test sentences to the development suite and continue calling the
  same set held out.

Report all of the following with denominators: token lexical coverage,
sentence derivation completion, whole-paragraph completion, semantic
correctness for adjudicated items, ambiguity/abstention, cap/timeouts,
latency, provider failures and model cost. Unknown words and unsupported
constructions remain failures in overall coverage; report their categories
separately. A later complete sentence does not repair an earlier paragraph
context gap.

The 2013 induction paper is a useful warning about interpretation of numbers.
[EPH13, §5, Table 2] reports results on 200 generated short sentences with a
90/10 split, excludes unseen test words, and distinguishes parse coverage
from formula accuracy. Its high top-three coverage is not evidence for
general unrestricted-text accuracy. Likewise our passing regression tests
are not a new held-out accuracy figure.

Do not reduce “verified” to “the root has a type.” Test whether the
derivation consumes the intended words, preserves both sides of a relation,
binds the intended variables, retains referential distinctions, and exposes
contextual assumptions. Completion, semantic typing and empirical adequacy
should remain separate fields in the application.

## 9. Bibliography and review ledger

Page numbers below distinguish physical PDF pages from printed page numbers.
“Inspected” indicates targeted review of the relevant passages, not an assertion
that every derivation in a long source was independently checked.

**[CKM05]** Ronnie Cann, Ruth Kempson and Lutz Marten. *The Dynamics of
Language: An Introduction*. Elsevier, 2005. Inspected version: 12 December
2004 final draft, 386 PDF pages, local file `cann-et-al-dec12 (1).pdf`.
Contents and selected passages in chs.2–9; especially printed pp.74–80
(PDF84–90), §§3.2–3.3, §5.4, §§6.1–6.2, ch.7, §8.3 and §9.2.
Publication-level and draft-level pagination must not be conflated.

**[HG21]** Christine Howes and Hannah Gibson. “Dynamic Syntax: The Dynamics
of Incremental Processing: Constraints on Underspecification.” *Journal of
Logic, Language and Information* 30, 263–276, 2021.
<https://doi.org/10.1007/s10849-021-09334-x>. Full article inspected. This
provides both a contemporary framework overview and explicitly secondary
pointers to papers in the special issue.

**[C10]** Stergios Chatzikyriakidis. *Clitics in Four Dialects of Modern
Greek: A Dynamic Account*. PhD thesis, King's College London, 2010.
396-page local PDF `chatzikyriakidis-phdthesis.pdf`. Contents, §2.2.2,
selected clitic/PCC material and §3.4.3.2 inspected. Detailed future feature
work must return to each dialect's conditions, not only the abstract.

**[CK11]** Stergios Chatzikyriakidis and Ruth Kempson. “Standard Modern and
Pontic Greek Person Restrictions: A Feature-Free Dynamic Account.” *Journal
of Greek Linguistics* 11, 127–166, 2011.
<https://doi.org/10.1163/156658411X599983>. Inspected locally as
`jgl-article-p127_3.pdf`, particularly the structural/case account at
printed pp.144–145. This is evidence for that account, not a new population
study of present-day acceptability.

**[KC16]** Ruth Kempson, Ronnie Cann, Eleni Gregoromichelaki and Stergios
Chatzikyriakidis. “Language as Mechanisms for Interaction.” *Theoretical
Linguistics* 42(3–4), 203–275, 2016.
<https://doi.org/10.1515/tl-2016-0011>. Inspected version: 52-page draft dated
21 April 2016, `tling-draft.pdf`, selected sections on growth, context,
interaction and references. Draft and final pagination differ.

**[KE19]** Ruth Kempson, Eleni Gregoromichelaki, Arash Eshghi and Julian
Hough. “Ellipsis in Dynamic Syntax.” In *The Oxford Handbook of Ellipsis*.
<https://doi.org/10.1093/oxfordhb/9780198712398.013.9>. Crossref records
publication in 2019; some bibliographies cite 2018. Inspected version:
24-page draft explicitly dated 4 October 2016, locally named
`KempsonEtAl18Ellipsis_preprint.pdf`. Relevant discussion: §§1.2–1.3,
especially PDF13–16 on reuse, PDF17–20 on interaction, PDF20–21 on islands.
The filename is not treated as the draft's publication date.

**[PEH11]** Matthew Purver, Arash Eshghi and Julian Hough. “Incremental
Semantic Construction in a Dialogue System.” IWCS 2011, 365–369.
<https://aclanthology.org/W11-0144/>. Full five-page paper inspected;
§2 describes DS-TTR/event semantics and §3 the DyLan implementation.

**[E15]** Arash Eshghi, Christine Howes, Eleni Gregoromichelaki, Julian
Hough and Matthew Purver. “Feedback in Conversation as Incremental Semantic
Update.” IWCS 2015, 261–271.
<https://aclanthology.org/W15-0130/>. Inspected §§2–3, especially record
dependencies, parsing DAGs, coordination pointers and clarification.

**[EPH13]** Arash Eshghi, Matthew Purver and Julian Hough. “Probabilistic
Induction for an Incremental Semantic Grammar.” IWCS 2013.
<https://aclanthology.org/W13-0110/>. Inspected abstract, §§4.4–4.6 and
evaluation §5. Learning assumptions and generated-data limitations are
retained in the discussion above.

**[ECH13]** Arash Eshghi and colleagues. “Incremental Grammar Induction
from Child-Directed Dialogue Utterances.” Workshop on Cognitive Modeling
and Computational Linguistics, 2013, 94–103.
<https://aclanthology.org/W13-2611/>. Title/abstract and bibliographic
identification inspected from the local paper. Included as an implemented
research direction; this report makes no numerical accuracy claim for it.

**[C17]** Stergios Chatzikyriakidis. “Modification in Dynamic Syntax.”
2017 conference abstract, two content pages plus a repository cover.
<https://www.researchgate.net/publication/313634514>. Full abstract inspected.
It explicitly motivates alternatives; it is not treated as a full published
grammar or a consensus analysis of every modifier class.

**[C25]** Stergios Chatzikyriakidis. “Constructive Dynamic Syntax.”
*Languages* 10(11), 269, 2025.
<https://doi.org/10.3390/languages10110269>.
Publisher PDF: <https://mdpi-res.com/d_attachment/languages/languages-10-00269/article_deploy/languages-10-00269.pdf>.
Inspected §§3–4 and conclusion, with particular attention to nominal typing,
Σ/Π, §4.3 action contexts and modifier alternatives. A foundational proposal
with worked examples, not an unrestricted implemented grammar.

**[KV19]** Ruth Kempson and colleagues. “Why Natural Language Models Must
Be Partial and Shifting: A Dynamic Syntax with Vector Space Semantics
Perspective.” Local two-page IWCS 2019 contribution
`kempson.etal_IWCS_19.pdf`. Title and proposal scope inspected. This motivates
an architectural option; no distributional backend is added to this app.

### Sources to acquire or review directly next

- Kempson, Meyer-Viol and Gabbay (2001), *Dynamic Syntax: The Flow of Language
  Understanding*: the foundational monograph, repeatedly cited in the reviewed
  sources. This review uses [CKM05] and [HG21] for directly inspected mechanisms.
- Ronnie Cann (2011), “Towards an Account of the English Auxiliary System,”
  in *The Dynamics of Lexical Interfaces*, pp.279–317: identified in [KC16].
- Lutz Marten (2002), *At the Syntax-Pragmatics Interface: Verbal
  Underspecification and Concept Formation in Dynamic Syntax*: identified in
  [C17], relevant to valency/modification.
- Eleni Gregoromichelaki (2006), *Conditionals: A Dynamic Syntax Account*:
  identified in [HG21] and [KE19]; necessary before claiming the workbench
  implements the theoretical conditional analysis.
- Miriam Bouzouita (2008), *The Diachronic Development of Spanish Clitic
  Placement*: identified in [KC16].
- Kempson and Kiaer (2010), “Multiple Long-Distance Scrambling: Syntax as
  Reflections of Processing,” *Journal of Linguistics* 46, 127–192;
  Gibson (2016), “A Unified Dynamic Account of Auxiliary Placement in Rangi,”
  *Lingua* 184, 79–103; Seraku and Gibson (2016), “A Dynamic Syntax Modelling
  of Japanese and Rangi Clefts,” *Language Sciences* 56, 45–67: identified
  in [HG21].
- Japanese case, Kazakh differential object marking and Mandarin minimizers
  papers summarized in [HG21, §3]: secondary evidence only at this stage.
- “Dynamic Syntax,” *The Oxford Handbook of Philosophy of Linguistics*,
  2026, <https://doi.org/10.1093/oso/9780198879640.003.0020>: metadata verified;
  chapter contents not reviewed.

## 10. Relation to the project foundation

The software foundation is the `dynamicsyntax` Python package and its
`dylan` engine, derived from the DyLan implementation tradition documented in
[PEH11]. This project builds on its action interpreter, trees, records and
context/search machinery. The workbench adds native Classical/Constructive
compilation, grammar families, diagnostics, operation playback, paragraph
and dialogue flows, source investigation, bounded model assistance and
visible Jev comparisons. The new relative family is another explicit
grammar/semantic extension on that foundation.

The research programme does not relabel those additions as inherited
features. Equally, the original literature's implemented capabilities are
not automatically advertised as working in this port: they need regression
evidence in the selected grammar and semantic backend.
