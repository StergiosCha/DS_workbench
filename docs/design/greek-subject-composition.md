# Overt Greek subjects and unfinished nominal composition

`ο μεγάλος άνθρωπος περπατάει` previously completed as `walk(pro)` in both native
backends. The same fault affected a model-supplied verb in
`ο μεγάλος άνθρωπος ήρθε`. Completion alone failed to reveal that the overt
subject's interpretation had been lost.

The Greek noun action combined the noun with its immediately preceding adjective
and returned to the clause. The unfixed DP still contained the determiner and
its noun restrictor, but had no formula of its own. The verb introduced a subject
placeholder `U_pro`. MERGE moved the DP's daughters into that subject node while
retaining the placeholder. SUBSTITUTION then resolved it to `pro`, blocking the
ELIMINATION which should have composed the DP.

MERGE now leaves a formula requirement when an incoming compositional subtree
has no formula yet. A destination placeholder cannot supply that formula; the
merged daughters must compose it. The destination's type remains a requirement.
An already resolved reference cannot be merged with the unfinished subtree until
there is a source formula with which to check compatibility. Conflict handling
remains atomic. This is a shared engine correction, not a new word entry.

The resulting Constructive interpretation is `walk(π₁(definite_00))`, where the
contextual assumption gives `definite_00` the refined type
`Σ x:person. big(x)`. Classical composition yields
`walk(ι x0:e. (person(x0) ∧ big(x0)))`. Greek clauses with no overt subject still
permit the existing `walk(pro)` analysis. Definite identification is assumed;
this fix does not supply discourse inference or the full semantics of size.

`tests/test_greek_subject_composition.py` checks argument identity and modifier
preservation across genders, subject positions, clitics, copulas, indefinite
subjects and stacked adjectives in both backends. It also checks the exact
reported sentence with a fixture model verb, Constructive Coq exports, genuine
implicit subjects, and agreement/PCC boundaries. The shared MERGE tests check
unfinished formulas, retained requirements and rejection without mutation.

## Polydefinites remain a separate coverage gap

The following user-supplied patterns currently stop at the second article in
both native Greek backends, including when a supported verb follows:

- `ο μεγάλος ο κόκκινος ο άνθρωπος περπατάει`
- `ο άνθρωπος ο μεγάλος περπατάει`

These are recorded coverage failures, not negative grammaticality judgments.
No polydefinite rule has been implemented, and no article is silently skipped.
The earlier [Constructive design](constructive-ds-design.md) also lists this
family outside its implemented scope. An extension needs a sourced DS analysis
of shared reference, repeated definiteness, adjective placement and agreement,
with tests for competing attachments and nonintersective readings. An ordinary
LLM vocabulary proposal cannot supply that construction. Experimental rules
could explore it, but a completed experimental tree alone would not validate
the analysis.
