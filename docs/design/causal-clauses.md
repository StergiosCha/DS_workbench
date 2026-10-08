# Finite causal clauses and playback status — 4 October 2026

Reported failure: `George opened the door because he came later`.
`because` had no native grammar rule and `later` had no lexical entry. The LLM
cannot add a closed-class clause construction through an open-class vocabulary
template. The accompanying screenshot showed a separate UI problem: a complete
`lends` result alongside an early animation frame labelled PARTIAL TREE.

## Implemented construction

Native English Classical/Constructive now accept finite `because` clauses;
Standard Greek accepts `επειδή` and `διότι`. A reason may follow the matrix
clause, or precede it with an explicit comma. Both contents remain required.
Nested causes and native English finite-complement attachments can provide
multiple readings. These rules are independent of the vocabulary source.

`causal_effects.py` executes visible make/go/put/delete operations. A postposed
reason grows a LINK with a content argument and a function that closes over the
matrix content. A preposed reason is parsed into the first argument position
of a curried connective; comma opens a separate main-clause content subtree.
This is connective valency, not a new argument of the lexical verb. Causal
subtrees have explicit local closure requirements, using the native content
closure operation. The reason's modifiers must propagate before crossing the
comma; completed preposed reasons are then sealed against backward attachment.

`because(main, reason)` is an opaque, typed relation. No causal axioms or truth
inference are implemented. Each Constructive argument closes its own Σ/Π
witnesses and the Coq predicate accepts `Type -> Type -> Prop`. Classical uses
its own proposition contents and choice terms. The two are not TTR translations.

Recomputation preserves causal LINKs: their structural marker persists; an
update flag reopens propagation when a subordinate modifier changes the tree.
The original matrix VP is not reused as the meaning of the whole causal
construction. A matrix negation already captured in the connective is not
applied a second time after a reason modifier. Tests assert formulas and
alternative readings, not only complete flags.

Temporal lexical operators cover later/earlier/late/early/today/yesterday/
tomorrow/soon and αργότερα/νωρίτερα/αργά/νωρίς/σήμερα/χθες/αύριο/σύντομα.
They preserve a temporal contribution without resolving a reference time,
calendar anchor or full tense/aspect semantics. `later` is distinct from `late`.

The exact user example completes using the existing WordNet candidates for
opened/door/came, the new causal/temporal rules and existing pronoun resolution.
`he` is resolved to George by the most-recent-compatible-name heuristic, with
that contextual assumption displayed. Live Jev checks completed in both
backends with six requests each and no change from the baseline lexical choices.

## Interface and limits

The new banner reports final completion separately from the current animation
step. An early tree explicitly says the final derivation completed when that is
known. **Show final result** pauses playback and selects the last frame. Failed
inputs keep their failure status; paragraph banners refer to the selected sentence.

`tests/test_causal_clauses.py` covers the exact example, Greek counterparts,
initial/final reasons, modifiers, local quantifier scope, negation, nested
causes, alternative attachment, Coq export, traces and paragraphs. Negative
cases retain failures for missing contents and unsupported forms.
`scripts/check_causal_browser.py` verifies the actual browser, exports, mobile
layout and playback; `--live` additionally checks the exact example through
Jev comparison using the existing test credential without saving it.

`scripts/build_causal_extensions.py` maintains marked sections in the four
grammars, and the everyday grammar builder invokes it. Causal predicates,
operators and interpretation notes remain in each semantic profile.

Not supplied: TTR causal rules, nominal `because of`, nonfinite reasons,
arbitrary conjunction/causal/negative scope, full tense/event semantics, or
general discourse reference. Existing language coverage measurements remain
unchanged; these construction checks are not a new open-text accuracy estimate.

The [public verification record](../../data/coverage/causal-construction-2026-10-04.json)
retains the exact reported sentence, composed meanings, reference assumptions
and deployment identity. The complete regression run passed 1,733 tests;
the 59 causal tests also passed after the final backend guards.
