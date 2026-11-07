# Classical choice terms and scope

Correction, 6 November 2026.

The English `all-plural` and `all-contextual` programs now reuse the `universal`
tau template, with type `cn -> e`. They keep their existing plural and context
gates, including the `in_context` restriction in `all the`. The generator no
longer replaces this template with a generalized quantifier. Classical `e`
requirements no longer accept generalized quantifiers, and continuation lifting
in the shared semantic module is confined to the Constructive backend.

## Resolving scope with choice terms

The earlier `examine(tau x.doctor(x), epsilon y.patient(y))` left the two
restrictions independent. Merely replacing the old `all` entry with the same
nominal tau expression would not fix that dependency.

For a universal and accompanying indefinites, `choice_scope.close_choices`
constructs scope during typed DS elimination, when the result has type `t`.
Nominal nodes still have type `e`. It uses the Hilbert identities:

- For `H(x) = R(x) -> B(x)`, universal closure is `H(tau x.H(x))`.
- For `H(x) = R(x) & B(x)`, existential closure is `H(epsilon x.H(x))`.

Tau is understood by its counterexample property: if `H` fails anywhere, it
fails at the tau-selected individual. Epsilon chooses a satisfying individual
when one exists. No `forall` constructor or type-raised lexical quantifier is
introduced by this operation. Its output contains choice terms, implication,
conjunction and the lexical predicates.

For the narrow reading of *every doctor examined a patient*, abbreviate:

```
p(d) = epsilon y:e. (patient(y) & examine(d,y))
Q(d) = patient(p(d)) & examine(d,p(d))
D    = tau d:e. (doctor(d) -> Q(d))
meaning = doctor(D) -> Q(D)
```

The restriction of the patient choice explicitly contains `d`. For the wide
reading, construct the doctor clause with a free patient parameter first, then
close the patient outside it:

```
D(p) = tau d:e. (doctor(d) -> examine(d,p))
Q(p) = doctor(D(p)) -> examine(D(p),p)
P    = epsilon p:e. (patient(p) & Q(p))
meaning = patient(P) & Q(P)
```

The two UI scope settings select these orders. Among quantifiers of the same
kind, structural argument order is retained. This is a bounded scope policy,
not a general implementation of all DS scope constraints or discourse choices.
Epsilon-only clauses retain the pre-existing nominal-choice interpretation;
this correction does not turn them into a uniform truth-conditional existential
calculus. Definites remain iota terms with the existing contextual assumptions.

## Boundaries and replay

An internal `choice_scope` annotation records a closed clause. It has no
additional logical meaning and prints as its contained formula. The annotation
is included in constructor serialization so a round trip retains the boundary.
An embedding clause cannot collect its choices again or move them into a
different scope. Lambda-bound terms and nominal restrictors also delimit
collection. Capture-avoiding substitution still reaches free parameters inside
a closed clause, as required for relative clauses.

Recomposing a clause from its daughters (for example, after a VP LINK modifier)
recomputes its choice expression. Closing an already closed result is
idempotent. The expanded formulas can be long; expansions above 20,000 AST
nodes fail composition rather than exhausting the worker. No TTR translation,
model call or final-output string replacement is involved.

## Verification

`tests/test_classical_choice_scope.py` evaluates the actual parser outputs
using an independent finite-model evaluator for Hilbert terms. It checks both
scope readings across all 16 examination relations between two doctors and
two patients, several empty/nonempty restrictors, and two choice-function
orders: 576 truth-value comparisons. The expected readings are computed with
Python `all`/`any`, not by the choice compiler. These tests include the case
where each doctor examined a different patient and there is no shared patient.

Further checks cover the doctor parameter in the inner epsilon restriction,
capture avoidance, clause boundaries, closure idempotence, root-tree/result
agreement, serialization, plural gates, and regeneration of the lexical rules.
The existing Constructive scope and Coq checks remain separate.

The experimental adapter still compares its unchanged example states and
action traces against `data/experiments/references-v1.json`. The new grammar
fingerprint is recorded separately in `grammar-revisions.json`; the historical
fixture is not rewritten. Adapter outputs continue to record the actual grammar
fingerprint. The experimental adapter and its frozen study protocol are unchanged.
