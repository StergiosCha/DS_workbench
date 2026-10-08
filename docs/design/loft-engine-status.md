# Thesis trigger layer — implementation and resume point

Updated 2026-09-25 on `constructive-ds`, continuing WIP `777bf69`.
Engine work was done inline, without subagents.

## Implemented scope

| Thesis operation | Engine syntax and behavior |
| --- | --- |
| Functor-spine box | `[\/1+]?Ty(x)` checks every existing node reached by one or more 1-edges; true on an empty domain. |
| Imperative box | `[\/+]?Ex.Tn(x)` checks every non-LINK/context descendant for an outstanding address requirement. |
| Existential closure | `<\/1+>`, `<\/0+>`, `<\/+>` and their upward counterparts require at least one step, with existing intermediate nodes. |
| Trigger connectives | `¬`, grouped `&`, and inclusive `|` / `||`, including nested modalities. |
| Type wildcard | Lowercase `Ty(x)` / `?Ty(x)` queries any type / type requirement; uppercase `X` remains a binding rule metavariable. |
| Address labels | `Ex.Tn(x)` tests fixedness; `Tn(a)` captures an address; `Tn(0)` checks a concrete address. |
| Features | `Mood(Imp)` and `[+NEG]` / `+NEG`. |
| Modality variables | `<Z>` searches for a witness and binds a literal path usable by `go(Z)`; failed candidates and negation restore prior bindings. |
| Locally unfixed plus | Literal `P` edge: `make(\/P)`, `go(\/P)`. Address `0P` can resolve to `010`, `0110`, etc., but not subject `00` or a LINK address. Repeating a build at the same address reuses its node. |
| PCC collision | `Fo(U_Sp')` and `Fo(V_Hr')` at the same node cause `put` to fail. Compatible or unrestricted placeholders preserve the established restriction. |

`*`, `U`, and `P` remain literal unfixed address edges in modalities. Plus
closures are relations used in triggers, not paths for `make` or `go`; those
actions reject closure navigation. The compact `P` representation encodes the
thesis's locally unfixed `<up0><up1+>` address class. Grammars should use that
representation when creating the unresolved node, rather than create a literal
`1+` address. Fixed resolutions can be queried as `</\0></\1+>Tn(a)`.

`put` instantiates bound labels before storing them, so a later rule's metavariable
reset cannot erase a captured address. An unbound box metavariable (`[Z]`) raises
an explicit error; bind its relation first. Unsupported trigger labels now warn
once per label specification when evaluated, rather than failing silently.

Activating the existing `anticipationL` disjunction exposed a completion cycle:
parent → completed LINK → parent. Completion now tries each completion action
once per unchanged tree state, allowing the other rules to run. The existing
`a man knows you` parser and derivation tests cover this regression.

## Verification

`tests/test_loft_engine.py` covers partial-tree modalities, empty domains,
fixedness, features, nested connectives, witness binding, rollback, navigation,
and rule-level backtracking.

`tests/test_clitic_restrictions.py` covers same-address PCC failures, distinct
address types, retained restrictions, and captured addresses. Minimal lexical
rule projections additionally verify indicative DAT–ACC versus rejected ACC–DAT,
imperative proclisis blocking after a fixed accusative, both SMG imperative
orders, and rejected GSG imperative ACC–DAT. These are engine checks, not the
finished Greek grammar or a semantic analysis of full utterances.

Final verification: **328 passed, 3 skipped, 1 pre-existing failure** in 35.36 s.
Ruff passed for all tests and changed Python modules.

Run with `.venv/bin/python -m pytest -q --timeout=60` and
`.venv/bin/ruff check tests`. The pre-change baseline was 283 passing, 3 skipped,
and one failing PDF smoke test: local LaTeX lacks `pst-tree.sty`. The same known
test can be excluded with `-k 'not compile_tex_smoke_if_latexmk_available'`.

## Next work

Continue with the MLTT semantics layer using `maps/semantics-flow.md` and
`constructive-ds-design.md`, then the English and SMG grammars and full regression
corpora. This change does not implement the entire LOFT language, a general
substitution-presupposition solver, or the remaining thesis grammar machinery.
Restrictions here are literal symbolic presuppositions; the later semantics
layer must resolve them against discourse referents. Node creation still follows
the existing engine's label policy, so lexical rules must explicitly project
their type/address requirements.

This repository note supersedes the older external memory's mid-edit resume
point. Keep subsequent engine work inline with visible checkpoints.
