# Nominal PP coverage and lexical-proposal diagnostics

This change fixes the reported failure of “the man with a knife runs” in the
maintained English Classical and Constructive grammars. No model is needed
for that sentence, its indefinite/universal counterparts, or “a man with
glasses runs”.

## Grammar and interpretation

The new nominal-pp lexical entry is available for with, in, at, on and near.
It starts at a complete CN below an unfinished determiner phrase, creates a
LINK with a copy of the head referent and a binary nominal relation, and opens
a real DP requirement for the preposition's complement. The clause cannot
complete until that complement is supplied. A computational closure action
binds local witnesses, refines the CN and returns the pointer to it; the
original determiner and matrix predicate then compose normally.

For “a man with a knife runs”, the normalized meanings are:

    Classical:
    run(ε x0:e. (man(x0) ∧ with_nominal(x0, ε x1:e. knife(x1))))

    Constructive:
    Σ x:(Σ n000:man. Σ y:knife. with_nominal(n000, y)). run(π₁(x))

The constructive display is shown up to bound-variable renaming. With a
definite, the restriction belongs to the contextual referent's type; it need
not appear as a conjunct in the matrix formula. It remains in the tree,
context assumptions and declarations.

with_nominal is an explicit contextual association between the head and its
complement. It does not automatically mean ownership or use as an instrument.
The postverbal entry now uses with_accompaniment, accepting humans or objects
without relabelling a knife as human. It is a propositional modifier, not an
event-semantic analysis. The old human-only companion predicate remains
declared for compatibility but is no longer the maintained with entry.

Knife/eyewear and run have maintained entries. A separate bare-plural entry
for glasses supplies an existential eyewear referent; it is not a general
theory of plural cardinality, generics or bare nominals. The singular article
does not license “a glasses”. WordNet remains available for additional nouns
and verb frames without model calls.

Nominal attachment in object DPs adds an alternative to existing VP attachment.
Request multiple analyses to inspect both; the first parse can now differ.
No claim is made that the default search chooses the pragmatically intended
attachment. Subject/object DPs, prenominal adjectives, quantifiers, embedded
clauses and nested PPs on different heads are checked. Stacked restrictions
on the same head remain outside this fragment.

## Action-reader correction

The IF/THEN/ELSE reader previously searched for the substring “if” anywhere
inside an effect. Thus a perfectly ordinary formula containing knife or gift
could be misread as a nested conditional. It now recognizes instruction
keywords only in instruction position. Regression checks also cover genuine
nested THEN/ELSE branches and keyword-like formula names.

## Experimental lexical entries

The allowed action vocabulary includes semantic-nominal-pp for English's new
nominal construction. Other native grammars need its computational closure
rule before they can use this operation; the validator checks that resource.
semantic-pp retains its separate requirement for an existing predicate
type AND formula. A direct attempt to apply it to a CN is rejected before
execution. The supplied predicate signatures are checked.

For execution failures, a bounded, request-local observer records the
experimental entry, failed effect, pointer, actual/required types and formula.
These diagnostics go to the next model attempt, the visible result and JSON
export. They are observations of failed candidate branches, not additional
parsing rules or a claim that every failed alternative causes the final failure.
Normal derivation replay still discards unsuccessful branches.

The model receives representative lexical entries by template and an explicit
inventory of available templates/counts, using all entries rather than a top-N
cut. A long list of noun senses therefore cannot hide an available verb reading.
Samples are explicitly identified as samples.

## Checks and reproduction

Run from the research/fix worktree with an installed environment:

    python scripts/build_nominal_pp_extensions.py
    python -m pytest -q tests/test_nominal_pp.py tests/test_experimental_grammar.py \
      tests/test_effect_trace.py tests/test_prepositional_phrases.py tests/test_relatives.py

The tests check completed meanings, distinct head/complement witnesses,
remaining requirements on incomplete prefixes, both attachments, action
replay, failure feedback, request isolation and unchanged relative analyses.
Constructive positive exports are compiled when coqc is available. The
experimental fixtures now use unmaintained goggles rather than maintained
glasses, so they continue to test actual model-supplied lexical additions.

These are authored implementation regressions, not an independently annotated
coverage benchmark or a demonstration of model generalization. Deployment
verification and wider-suite outcomes are recorded separately.
