# Quotation after Gregoromichelaki (2017)

Source review and implementation plan, 7 November 2026. **No quotation fragment
has been implemented by this review.** The existing dialogue facilities are
prerequisites, not a tested implementation of this account.

## Inspected source

Eleni Gregoromichelaki, *Quotation in Dialogue*, published in *The Semantics
and Pragmatics of Quotation* (2017), pp.195–255,
[DOI 10.1007/978-3-319-68747-6_8](https://doi.org/10.1007/978-3-319-68747-6_8).
The user supplied `Downloads/Gregoromichelaki160117upload.pdf`, a 74-page
author manuscript created on 16 January 2017. **Page numbers below refer to
that manuscript, not the published chapter.** Its fingerprint is in the
research library record `GQ17` and the dated source manifest.

Inspected: opening examples and argument; §7.1; §7.2 on DS-TTR and context;
§§7.3.1–7.3.3 on quotation; conclusion. The image-based macros (95), (98),
(117) and (133) were also visually inspected, on pp.48, 50, 55 and 62.
This is a review of the formal account, not a claim to have audited every
comparison with other theories in §§2–6. The earlier five-page *Procedural
Syntax and Interactions* manuscript is a separate source.

## What the account requires

Quotation belongs to the same incremental grammar as ordinary dialogue.
The account uses **DS-TTR**: context, utterance events and derived content are
represented with dependent record types. Its main components are:

1. **An utterance event for each contribution.** The context records word
   forms, utterer, addressee and temporal/location information. These records
   accumulate alongside semantic composition. Someone physically uttering a
   word need not be the person taking responsibility for its content
   (§7.2, pp.34–38, (79)–(81)).
2. **Actions as reusable objects.** Context contains the actions used to
   construct content as well as the resulting content. The grammar can refer
   to, execute and re-execute those actions. This connects quotation to
   ellipsis and repair (§7.3.1, pp.44–47, (87)–(94)).
3. **The `run_g` operation.** Macro (95) processes a sequence under grammar
   `g` and makes its performance available as an utterance event `u_q` at a
   predicted node. It can process upcoming material; it is not restricted to
   replaying an already completed utterance (§7.3.1, pp.48–49).
4. **A separate echoed/reported event `u`.** For echoic quotation, this event
   can supply contextual parameters for the demonstrated event `u_q`.
   The events are not interchangeable. A report can also require accommodation
   of a hypothetical or reconstructed event, rather than matching an actual
   recording ((98), pp.50, 53–54).
5. **LINK and constrained resolution in direct reports.** The `say` macro
   introduces an utterance-event metavariable and a LINKed structure. Running
   the quoted actions under the relevant context supplies its value. The
   reported speaker constrains the matrix subject ((117), pp.55–56).
6. **Context and evaluation parameters can change independently.** Indirect
   reports need not use the reportee's indexical context. Word-by-word changes
   account for jointly completed reports, mixed quotation and free indirect
   discourse (§7.3.2, pp.58–61; §7.3.3, pp.62–65).

The paper does not require a fresh, unrelated construction for each quotation
subtype. It combines these mechanisms. Quotation marks are useful cues, not a
necessary condition of the entire account. Nor is every quotation forced into
a complete propositional complement: (95) applies at different predicted
types, and examples include single words and fragments.

The LINK route is also not universal. For a just-uttered contribution later
treated as a report, the `say` alternative in (126) can resolve from context
without an independent demonstration on a new LINK (pp.57–58). Retain that
distinction when extending beyond the first fragment.

## A concrete derivation to implement

Source example (116), p.55: **John said “I was loud”.**

1. Construct the matrix subject and predicted predicate with ordinary DS
   actions. The direct-report alternative of `said` constrains the subject to
   the speaker of the reported event `u`.
2. Introduce the event-valued object requirement and its metavariable. Build
   the LINK on which the demonstration will be processed.
3. Execute the quoted lexical/computational actions under the selected grammar
   and the contextual parameters supplied by `u`. At `I`, use the reported
   speaker John; retain the identity of the actual reporter separately.
4. Accumulate the quoted content and its action/event record. Resolve the
   matrix placeholder through the LINK constraints when the requirements are
   met. A successful report does not assert that its embedded claim is true.
5. Retain the demonstrated content and actions in context for subsequent
   reference and ellipsis. Subsequent unquoted words again use the appropriate
   current context, without reinterpreting already processed indexicals.

This is a source-based execution outline, not executable code copied from the
paper. Footnote 31 explicitly says the printed node names and action sequences
are schematic. The app will need concrete addresses, requirements, context
selection and failure behaviour. The source example additionally requires tense
and adjectival predication; a first authored implementation control can use
**John said “I walk”** while marking tense as outside that fragment.

## Code already present and gaps

| Area | Existing implementation | Quotation work required |
| --- | --- | --- |
| Actual participants | `dylan/context/context.py` reads the speaker/addressee of the current word; `dialogue_workbench.py` supplies dyadic turns. | Distinguish actual utterer/addressee from the contextual values used inside a report. Nick in (113) is a reported addressee, not necessarily a third actual dialogue participant. |
| Indexicals and reflexives | `semantic_effects.py` and `native_dialogue.py` use current participants. | A quotation-aware context lookup, with source/event provenance and restoration; retain local reflexive binding checks. |
| Trees and histories | DS LINK operations, DAG alternatives, tree copies, repair history and action traces exist. | A typed demonstration object and a `run` operation that consumes/actions through the parser and participates in rollback. UI trace playback alone is not semantic `run`. |
| Word forms | `UtteredWord` lowercases its word; paragraph mode retains sentence source spans. | Preserve exact quoted forms and token spans alongside normalized lookup forms. Quote-internal punctuation must not prematurely end the outer report. |
| Semantics | TTR record operations and native Classical/Constructive compilers exist. | Quotation-specific event, context and content operations for each enabled backend. Existing `es` in the conditional beta supplies no reported-event model by itself. |

The inspected action factory and shipped grammar files contain no quotation
`run_g` mechanism or demonstration/reported-event pair. Some inherited context
and action facilities may be reusable; having them does not establish the
source's quotation coverage.

## First beta and acceptance cases

Start with explicit, balanced direct quotation after a reporting verb, a small
reviewed lexicon and declared report context. Use the source's DS-TTR record
account as the reference for semantics. Enable a backend only once its own
composition and context rules pass the checks; native translations must be
described as adaptations. A boundary stack can help implement the first marked
fragment, but the semantic interface must allow context changes at individual
words and later quotation without explicit marks.

| Case | Origin | Required observation |
| --- | --- | --- |
| John said “I walk”. | Authored simplification of (116). | `I` resolves to John; actual reporter remains recorded; matrix takes an utterance event with content and action history. |
| A: John said “I walk”. / A: I run. | Authored restoration control; second contribution starts a new proposition. | The second `I` denotes A, not John. |
| A: John said “I / B: walk”. | Authored shared-quote control. | B continues the pending quote. The already resolved subject remains John; actual word contributions show A then B. |
| A: Will you say to Nick… / B: “I hate you”? Yes, why? | Source (113), p.54. | In the quoted content B hates Nick. Future, reporting-to and follow-up questions are later coverage, not implied by the simplified beta. |
| A: Did you say to Nick that you… / B: injured myself? Yes, my doctor says so. | Source (132), p.61. | B injures B; the indirect-report path and per-word participant values must interact correctly. |
| “John arrives” is grammatical. | Source (96), p.48. | Pure citation supplies an utterance object; it does not assert that John arrives. Later extension. |

Further controls: an unfinished quote retains pending requirements; a failed
quote branch leaks neither context nor bindings; changing a quote's analysis
through backtracking reproduces the same event identities on replay; reported
content is not exported as an independently asserted fact. Keep exact surface
forms in traces/exports. Source cases (118)–(120), pp.56–57, then test access to
quoted material by pronouns and ellipsis. Full VP ellipsis is additional work.

Each parser branch must carry its own quotation state. Mutating the global
current speaker is insufficient, because failed alternatives and replay would
then change the interpretation of other words. Snapshot the reported context,
grammar identity, action references, pending boundaries and fresh event IDs with
the branch. `run` must operate on DS action objects, not evaluate source strings
as Python. Count its work toward the ordinary parser search limits.

In the browser, show the actual speaker and interpreted indexical values at
each quoted word, the matrix/quoted LINK, both event identities, and expandable
quoted actions. The final report and its embedded content should both be
inspectable, with their different roles stated explicitly.

## Integration with the main grammar and situation structure

Yes: conditionals, temporal clauses and quotation can become features of the
main grammar through shared situation/context machinery and construction-
specific lexical actions. Their different dependencies must be preserved: the
conditional beta shares a restricted situation term; the thesis's temporal
sketch relates subordinate situations to reference time; quotation introduces
utterance events and potentially shifts context and evaluation parameters.

There are two related but distinct source claims:

- Gregoromichelaki (2011), §8.4.1 fn.6, mentions introducing situation arguments
  only when needed as an alternative to that chapter's uniform situation tree.
- The quotation manuscript, §7.2 p.34, includes world/time/situation parameters
  in content, independently shiftable across predicates. This does not require
  drawing a complete separate situation subtree at every stage. Its
  CONTEXT/CONTENT display division is expressly expository (fn.16, p.35).

Recommended implementation direction: retain evaluation information in the
semantic representation and build explicit situation structure when the
construction needs it. Offer a compact display of that structure with an
expansion control. **Do not claim that the current ordinary grammar already
contains hidden situation arguments:** its predicates and the conditional
beta's situation-sensitive predicates still have different signatures.

Integration therefore needs an explicit, tested rule connecting an ordinary
predicate to its situation-sensitive use, preserving subject/object identities
and quantifier scope. Merely adding unused `es` nodes, or hiding a new argument
without defining its composition, would not do this. The wording for the
implemented design can then be: “Situation structure is introduced when the
construction requires it; the compact tree view can hide its internal detail.”

Keep beta isolation during that work. Merge into the main grammars after tests
cover interactions with quantification, negation, embedded clauses, Greek clitic
conditions and dialogue context, separately for each semantic backend.
