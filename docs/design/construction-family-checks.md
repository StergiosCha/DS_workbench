# Construction families and proactive regression checks

The failure of `George is a great person` exposed a missing adjective family.
WordNet could offer *great* as a predicate or even as a noun, but the maintained
lexical templates did not express *great relative to the following noun*. Adding
a proper-name entry could not solve that construction gap.

## Noun-relative adjectives

`subsective-adjective` now preserves a noun restrictor and predicates a property
relative to it. Thus a *good doctor* remains a doctor, without automatically
asserting that the referent is good in an unrestricted sense. Singular,
distributive plural and context-marked plural templates share this interpretation.
They apply inside copular complements, subjects, objects and relative clauses;
they are not special entries for *George* or *Mitsotakis*.

Constructive composition uses a refined noun type with a predicate taking the
restrictor and an individual. Classical composition conjoins the noun property
with a predicate taking that property and an individual. The compilers and
signatures remain distinct. `scripts/build_attributive_extensions.py` maintains
the programs; `lexical_expansion.py` checks the backend-specific signatures.

The WordNet mapper supplies this additional frame for a curated set of adjectives,
including *great*, *good* and *skilled*. The ordinary lexical LLM can propose it
for further appropriate words. These remain lexical hypotheses: a WordNet sense
can be irrelevant, and choosing a frame does not settle polysemy. Degree scales,
comparison classes and entailment reasoning are not implemented. *Former*,
*alleged* and *fake* must not use this subsective template. Greek and TTR do not
inherit these English programs.

## Automatic matrix

`scripts/audit_construction_families.py` checks combinations of constructions,
names and vocabulary against the actual pinned WordNet index, with models off.
CI runs it on every push to main/master and every pull request. A failed or
inconclusive maintained expectation fails the job; the JSON artifact retains
every outcome, including exploratory failures. The existing bilingual corpus
floors and semantic tests remain separate checks.

The 2026-10-16 authored matrix has 162 cases across both native English backends:

| Family | Cases | Complete |
| --- | ---: | ---: |
| Copular noun phrases | 18 | 18 |
| Noun-relative adjectives | 36 | 36 |
| Bare predicative adjectives | 18 | 18 |
| Modified quantifiers | 8 | 8 |
| Objects and PPs | 24 | 24 |
| Coordination | 6 | 6 |
| Finite clauses | 24 | 24 |
| Relative clauses | 8 | 8 |
| Negative contrasts | 8 | 0 |
| Exploratory gaps and ambiguity probes | 12 | 2 |

All 150 maintained expectations matched. The two exploratory completions use
the nominal reading of *good* in `John is a good`; they are not evidence for a
missing-head adjective construction. Ten remaining failures cover five patterns
in each backend: *a very good doctor*, perfect copulas, passives, *former doctor*
and possessive relatives with *whose*. These form a concrete next-family backlog.
They remain exploratory, not skipped or relabelled as successful.

The matrix is a development check, not an unseen-text accuracy estimate or proof
of the intended meaning of every completed sentence. Separate semantic tests
check noun restriction, modifiers, scope interactions, malformed contrasts and
Constructive Coq compilation. Live browser checks of the reported sentences
separately verify AI switches and actual request counts.

For each next family: document the analysis and exclusions, add combinations and
negative contrasts before implementation, implement native semantic composition,
check exact meanings and full traces, then move supported expectations into the
CI floor. Use experimental packs to explore missing rules; only reviewed changes
become maintained grammar coverage.
