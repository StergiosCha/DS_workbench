# Recursive finite clause complements

Both native English grammars now parse finite complements of `thinks` and `says`,
including nested clauses and omission of `that`:

```text
john thinks that mary walks.
john thinks mary walks.
john says that mary thinks that bill shouts.
john thinks that a man walks.
```

The shipped entries also include `think`, `thought` and `said`. This uses ordinary
DS action programs; no LLM constructs the tree or interprets its completed output.
The model-assisted lexicon can instantiate the new `clausal(PRED,SUBJ)` template
for another finite verb, such as `believes`, subject to the existing validator.

## Tree growth and licensing

At the predicate position, the clausal verb makes a function daughter and a clause
argument daughter. The simple proper-name example has seven nodes in both modes:

```text
0: t / Prop
├── 00: john
└── 01: predicate of john
    ├── 010: embedded clause
    │   ├── 0100: mary
    │   └── 0101: walk
    └── 011: λc.λx.think(x,c)
```

The clause daughter initially requires `t` / `Prop`, `?+COMP`, and `?+CLOSED`.
It is marked `+CLAUSE`. The ordinary `intro-pred` rule is blocked while `?+COMP`
remains. The lexical entry for `that` consumes this requirement and marks
`+OVERT-COMP`; the optional computational `zero-complementizer` rule consumes it
and marks `+ZERO-COMP`. Neither option manufactures a subject or predicate.
`that` has no entry at a nominal position or unselected root.

The same clause-building rules then operate inside this daughter. A further
clausal verb starts another complement, so recursion is not encoded as a list of
sentence patterns. Each additional embedding with proper names adds four nodes.
Lexical templates continue to determine valency: an intransitive `walks` does not
acquire a clausal argument just because `that` follows it.

The new `close-complement` rule executes only after the clause has a propositional
formula and its descendants are complete. The remaining `?+CLOSED` prevents the
clause from being used prematurely. Its semantic operation replaces the formula
and type as needed, discharges the closure requirement, and marks `+CLOSED` through
the traced delete/put effects. Normal completion and beta reduction then combine
the clause with its embedding predicate. All make, go, put and delete effects
remain visible in the workbench.

## Separate semantics

Classical complements remain type `t`, consumed by a lexical function of type
`t → e → t`. Classical embedded DPs retain the full `cn` structure and epsilon/tau
terms; they are not translated into dependent types.

In constructive mode, closing the embedded clause binds its own indefinite
witnesses before application to the embedding verb:

```text
john thinks that a man walks.
  think(john, Σ x:man. walk(x))

a man thinks that a dog walks.
  Σ x:man. think(x, Σ y:dog. walk(y))
```

The second display alpha-renames the inner binder for readability. The renderer
may reuse `x` in the disjoint nested scope. Substitution remains capture-avoiding.

A closed content can be a proposition or a dependent Sigma proof type. Therefore
constructive complement arguments use the semantic universe **Content**, exported
as Coq `Type`, rather than pretending every Sigma type belongs to Coq `Prop`.
The clausal lexical function has DS type `Content → human → Prop`; its semantic
constant is declared `think : human → Type → Prop`. The clause boundary promotes
the locally closed content into this universe. `Content` does not satisfy nominal
object slots and is not a subtype of `object`.

The existing scope setting operates independently inside each clause:

```text
john thinks that every doctor examined a patient.
  narrow: think(john, Π d:doctor. Σ p:patient. examine(d,p))
  wide:   think(john, Σ p:patient. Π d:doctor. examine(d,p))
```

Both readings stay inside `think`; this implementation does not derive de re
scope across the complement boundary. Coq tests compile these content arguments,
matrix and embedded indefinites, and deeper nesting. Compilation checks the
exported terms' types, not the truth of a report.

`think` and `say` are opaque predicates over the represented content. Possible
worlds, factivity, quotation and a full intensional attitude semantics are not
implemented. Postfix `quickly` still modifies the matrix VP through the existing
LINK operation; alternative attachment inside a finished complement is outside
this fragment. Tense and agreement remain unanalysed, as in the earlier grammar.

## Frontend, dialogue and failures

Example chips provide a single and a nested complement. Dashed nodes marked
**CLAUSE** expose the actual boundary decorations. Selecting one explains whether
closure has happened; constructive Content nodes explain their proof-type domain.
The action trace exposes complementizer consumption and local closure.

A second speaker may supply a required complement in the same context:

```text
A: john thinks
B: that mary walks.
```

`john thinks`, `john thinks that` and `john thinks that mary` remain partial trees.
Adding a full stop cannot complete their open requirements. Unknown embedded
vocabulary remains a lexical gap; an embedded nominal type conflict such as
`john thinks that a stone shouts` remains a semantic type failure. No new
grammaticality judgments are inferred from rejected parses.

The model's new `clausal` analysis supplies only the predicate symbol and subject
sort. The template supplies the Content argument, clause projection and closure
requirements. The validator adds the matching two-argument semantic declaration
and reserves the template's binder `c`. Existing lexical entries cannot be
overwritten to acquire a new frame. Greek and TTR grammars are unchanged.

The live Flash check initially exposed a synonym substitution: `believes` was
given the lemma and predicate `think`. That produced a complete but lexically
incorrect result. The proposal contract now explicitly preserves the verb lemma,
uses that lemma (with an optional sense/frame suffix) for its symbol, and checks
regular finite `-s` forms. The old cached proposal is invalidated by the contract
version change. This is a limited lexical identity check, not a full morphological
analyser or a proof that the model has selected the right sense.

Regression tests cover recursion, optional complementizers, real node counts and
pointer transitions, local witness closure, classical DPs, Coq typing, missing
complements, inappropriate complementizer positions, semantic failures, vocabulary
gaps, model template instantiation and shared dialogue completion. Browser checks
include the clause inspector and individual closure instructions. With
`--live-lexical`, they also exercise Flash's `believes` proposal through the UI.

Validation on 25 September 2026: 545 tests passed, three skipped, and the existing
environment-dependent LaTeX smoke test deselected. The live browser run passed
with zero console errors, including Flash-generated `purrs` and `believes` entries,
cache reuse, both semantic modes, clause markers and closure instructions.
