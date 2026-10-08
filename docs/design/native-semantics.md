# Native classical and constructive DS

The workbench has separate native backends, selected by bundled grammar:

| Grammar | Axiom | Node meanings |
| --- | --- | --- |
| `2026-english-classical` | `?Ty(t)` | lambda terms, ε indefinites, τ universals |
| `2026-english-mltt` | `?Ty(Prop)` | nominal types, dependent Σ/Π, witnesses and projections |
| `2015-english-ttr` and existing TTR grammars | `?Ty(t)` | existing record semantics |

The classical mode follows the user's 2026-09-25 decision to retain a separate
λ/ε/τ system. The prohibition of choice terms in the constructive specification
continues to apply to constructive mode.

## Composition

These grammars use the existing lexical/computational action loader, IF triggers,
make/go/put effects, trees and word-level context DAG. They do not translate TTR
output. `Ty(mltt:...)` and `Fo(mltt:...)` select native types and formulas while
loading lexical entries; `classical:` selects the other native backend. Prefixes
are grammar syntax and are omitted from mathematical displays.

`semantics.json` supplies the axiom, nominal hierarchy, constant types and
predicate signatures. The parser carries this profile into each cloned tree.
Native semantics dispatches before TTR underspecification or record merging.
The shared `Formula` result interface accepts all three semantic families.

An immutable term AST implements capture-avoiding substitution and beta
normalization. Constructive formulas reject ε and τ constructors. Typed
elimination chooses the functor by type, including a generalized quantifier on
daughter 0. Predicate-slot satisfaction is distinct from function subtyping;
application checks contravariant function domains and declared nominal inclusions.

An indefinite first constructs `Σ x:A.⊤`. Its NP contributes a fresh witness
whose name is derived from the node address. Elimination inserts first projections
when applying a nominal predicate to that witness. Root interpretation closes
free witnesses; the UI retains both the raw term and its simplified presentation.
For example:

```
a man walks.
  classical:    walk(ε x0:e. man(x0))
  constructive: Σ p00:(Σ x:man.⊤). walk(π₁(p00))
  simplified:   Σ x:man. walk(x)
```

Classical determiner phrases retain the DS common-noun structure. The type `cn`
is a restrictor type, distinct from both `e → t` and constructive `CN`:

```
e: ε x0:e. man(x0)
├── cn: (x0, man(x0))
│   ├── e: x0
│   └── e → cn: λx:e.(x, man(x))
└── cn → e: λP:cn.ε(P)
```

The determiner builds this structure with make/go/put and allocates the variable
with freshput. The noun supplies an `e → cn` function returning a restrictor
pair; elimination first builds that pair, then applies the determiner to close
its variable with ε or τ. Adjectives modify the predicate while preserving the
restrictor head. Two DPs allocate distinct variables (`x0`, `x1`). Proper names
remain single entity nodes. Thus `a man walks` has seven nodes, while its
constructive counterpart retains the universe-based `CN` analysis.

Source checks for this structure: local `TEX/SOAS_DSmod.tex`, lines 309–317
(explicit `cn`, `e → cn`, `cn → e` decorations), and
`TEX/FADLslides14_ste.tex`, lines 3364–3373 (the variable/predicate daughters
under the restrictor of “a student”). These source diagrams motivated the
correction to the initial flattened classical entries.

A postfix `quickly` action attaches a LINK tree to the VP, instantiates the
modifier domain from the predicate's actual type, reduces it and recomputes the
root. LINK creation and integration expand into the engine’s make/go/put/delete
effects. Those operations, traversal and reduction are individually visible
in the operation trace. Typed thinning also executes delete on the satisfied
requirement.

## Scope and export

Finite complement clauses now have explicit local closure. `thinks` and `says`
project nested clause requirements, with optional `that`. Classical complements
remain `t`; constructive closed proof types use `Content`, exported as Coq `Type`.
Indefinite witnesses close inside their complement before the embedding predicate
combines with it. See [clause embedding](clause-embedding.md) for the programs,
recursive examples and the limits of the opaque attitude predicates.

For `every doctor examined a patient.`, the workbench's explicit scope control
places existential witness closure inside or outside the leading Π:

```
Π d:doctor. Σ p:patient. examine(d,p)
Σ p:patient. Π d:doctor. examine(d,p)
```

These are semantic closure settings over the same DS tree, not two independently
searched syntactic paths. The scope control currently covers this supported
subject-universal/object-indefinite configuration.

Coq export emits the raw native term, constants, predicate signatures and nominal
inclusions. Nominal inclusions are represented by record coercions. Export
currently requires an acyclic, single-parent hierarchy (as in the bundled grammar).
Compilation verifies the meaning's type; it does not prove the sentence true.
The six displayed constructive examples and the alternative scope reading are
compiled in the tests when `coqc` is installed.

```python
from dynamicsyntax import parse

result = parse("a man walks.", "2026-english-mltt", trace=True)
print(result.semantics)
print(result.semantics.simplified())
coq_source = result.to_coq()
```

## Coverage

Both native modes cover the displayed English fragment: proper names,
indefinites, subject universals, intransitive/transitive verbs, attributive
adjectives, the postfix VP modifier and recursive finite complements. Constructive mode rejects nominal type
mismatches such as `a stone shouts`. Classical `e/t` types intentionally do not
impose that nominal restriction.

This is not yet the full thesis grammar. Object universals, relatives,
coordination, questions, Greek clitics/PCC derivations, and proof-term synthesis
are not supplied by the new native lexical resources. Existing TTR questions
remain available in DS-TTR mode. The generic engine's unfixed-node and trigger
support remains available for further grammar development.

## September 2026 semantic extensions

Native grammars now declare adverbs as `adverb(PRED)` with `semantic-adverb(PRED)` and a `modifiers` entry in `semantics.json`. Both classical and constructive grammars offer matrix and embedded-complement attachment. LINK evaluation reopens the affected ancestors and closes complement witnesses locally again. The action trace includes the pointer movement, node creation and label replacement.

Constructive object universals use argument raising: a quantified object consumes a continuation formed from the transitive predicate while its subject slot remains open. Nominal coercions still check the restrictor, including projections out of refined Σ types. Narrow and wide witness closure remain explicit options.

`Expr.to_tex()` exports the native calculus directly. Semantic-only LaTeX documents do not load the TTR tree styles. Both native backends have compiling document tests; the pre-existing legacy TTR LaTeX smoke failure is separate.

`semantic-negate` negates a typed proposition. Narrow scope closes pending witnesses inside negation; wide scope retains them for outer closure. Coq uses `~ P` for propositions and `A -> False` for refutation of a dependent witness type `A`. The latter distinction is necessary because Coq's `~` accepts `Prop`, whereas constructive Σ witness types inhabit `Type`. Coq export defaults to declarations reachable from the meaning, including the nominal ancestor chain; `SemanticFormula.to_coq(minimal=False)` emits the whole configured theory.


SUBSTITUTION now resolves restricted formula metavariables at fixed nodes against typed `Context.referents`. Speaker/hearer restrictions select their declared roles; third-person candidates use the active dialogue path before grammar defaults. Local-clause referents are excluded. Repaired-away names disappear because the candidate inventory is derived from the active DAG path. A missing compatible referent leaves the requirement open and records `missing_context`; it never supplies an arbitrary model-generated value. New referent declarations are copied into the resulting tree's semantic theory without mutating sibling branches. The maintained Greek cluster templates are the next consumers of this operation.
