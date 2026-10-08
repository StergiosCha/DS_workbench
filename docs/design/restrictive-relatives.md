# Restrictive relatives in the native English grammars

This M4 increment adds subject and direct-object relatives introduced by `who`,
`which` or `that` to `2026-english-classical` and `2026-english-mltt`. The existing
complementizer reading of `that` remains. The two systems share tree actions;
their nominal structures and meanings remain distinct.

## Source and scope

Chatzikyriakidis's thesis, physical PDF pp.74–80, (2.79)–(2.92), provides the
LINK/copy/MERGE account. In particular, p.80 distinguishes the lower variable
entity as the origin of a restrictive LINK from the upper bound entity used
for nonrestrictives. The worked nonrestrictive clausal conjunction in (2.90)
is not used as the restrictive meaning. The 2015 English TTR `pron_whrel`
template supplies the precedent for building an unfixed head copy and the
relative clause's subject/predicate requirements in a lexical action.

The constructive CN refinement follows the explicit M4 design in
`wide-coverage-plan.md`. The English fixtures are authored regression examples,
not quotations or independently collected grammaticality judgments. Their
negative controls include both malformed input and valid English outside the
fragment; the workbench leaves those judgments unassessed.

## Actions and tree structure

`semantic-relative` expands into recorded `put`, `make` and `go` operations.
It requires a complete CN directly below an unfinished determiner phrase, so
prenominal adjectives must compose first. It parks `?RESTRICT` on that CN,
creates a LINK root with `?Ty(t/Prop)` and `?REL-CLOSED`, and creates a terminal
unfixed daughter with `?Ex.Tn(x)` and `REL-GAP`. The latter contains a copy of
the head variable. It then builds a predicate daughter and subject daughter,
leaving the pointer at the subject requirement.

For a matrix subject DP, the relative root is `0000L` in classical mode and
`000L` in constructive mode. The classical DP keeps all five nominal nodes:
the upper `e`, determiner `cn → e`, CN, lower variable `e`, and restrictor
`e → cn`. Its LINK leaves the lower entity. The constructive LINK leaves the
CN and its copied variable has that CN as its domain.

`merge-relative` uses the existing atomic MERGE and address-subsumption check.
It can move the copy into the relative's subject (`L0`) or direct object
(`L10`). It cannot cross a LINK or enter an embedded complement. When the
clause has composed, `semantic-restrict` requires all pending requirements
except its own closure marker to be gone and exactly one gap marker at one
of those two positions. It closes local witnesses, refines the host CN and
returns the pointer there. Only then can the determiner combine.

These operations appear individually in playback, including the disappearance
of `L*` at MERGE, the fixed destination, and the inverse-LINK return. The
workbench adds subject and object relative examples in both semantic modes.
The browser check verifies separate subject/predicate branches and mobile
page width as well as pointer and operation behavior.

## Meanings

For `a man who mary knows walks.`:

* Classical: `walk(ε x0:e. (man(x0) ∧ know(mary, x0)))`.
* Constructive: `Σ x:(Σ r000:man. know(mary, r000)). walk(π₁(x))`.

Classical restriction conjoins the relative proposition with the original CN
predicate before epsilon/tau binding. Constructive restriction creates
`Σ r:A. relative(r)` before determiner composition. The head copy is a bound
variable, never a newly declared lexical constant or existential witness.
Indefinites within the relative close there, including under the existing
local narrow/wide scope policy.

Function coercion now adapts a predicate to a refined domain by inserting
the appropriate first projection. Structural arrow subtyping alone was
insufficient: it allowed a universal over a Sigma domain to pass a pair to
a predicate of the underlying entity. The fix also covers adjective-only
universal subjects. Coq checks exercise both cases.

## Supported combinations and limits

Tests cover relatives inside subject and object DPs, subject/object gaps,
adjectives, subject/object universals, local negation, an internal indefinite,
an embedded relative-bearing DP, nested relatives on different DPs, and a
second speaker completing a relative. Classical exact meanings and the five
nominal nodes are checked; constructive positive meanings compile in Coq.

Not covered: nonrestrictives, relative omission, prepositional or indirect
object gaps, long-distance extraction, stacked relatives on one CN, animacy
selection among `who/which/that`, or a full island theory. For example,
`a man who john thinks mary knows walks` is an unsupported extraction, not
evidence of ungrammaticality. Greek `pu` and dialect-specific relative/clitic
interactions remain M5 work.

## Corpus

`scripts/build_english_corpus.py` harvests the explicit positive-meaning table
and gap-control table from `tests/test_relatives.py`. Positive expectations
record the regression specification; rejected controls keep `not_stated`
judgments even when their expected parser outcome is false. Other harvested
probes also retain `not_stated`. Known-word failure, lexicon gaps and semantic
type mismatches stay separate. The builder also disambiguates IDs when two
distinct fixture literals occur on one source line.
