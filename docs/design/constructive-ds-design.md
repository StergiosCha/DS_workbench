# DS-MLTT: Constructive Dynamic Syntax backend — design brief

Source of truth: Chatzikyriakidis (2025), "Constructive Dynamic Syntax", *Languages* 10(11):269
(examples (8)–(43); page refs below are to the article). Goal: keep the DS ACTION calculus
intact and substitute MTT-semantics (Luo-style Martin-Löf type theory) for the TTR/Montagovian
semantics. The epsilon calculus (epsilon/tau/iota terms) disappears entirely — Σ replaces the
existential/choice role of ε, Π replaces τ.

## 1. Type system (new module, `src/dylan/formula/mltt/`)

Types:
- `Prop` — replaces `t` as the propositional goal type. Initial tree axiom: `?Ty(Prop)`.
- `CN` — a UNIVERSE: the type of (names of) common-noun types (paper §3.2.2, (5)–(6)).
- Base CN types: `man`, `human`, `dog`, `doctor`, `patient`, ... (from the grammar's lexicon
  CLASS/type columns). Every base CN type is a subtype of `object` (top of the CN universe).
- `object` — top type of the CN universe; the DS type `e` is replaced by `object` (paper §4.1–4.2,
  trees (12), (31)).
- Arrows `A → B`; dependent `Π x:A. B` (polymorphic over CN when A = CN, e.g. (5a,b));
  `Σ x:A. B`; `⊤` (truth placeholder); (optional, doc only: disjoint unions `A + B`, fn. 3).

Subtyping / coercion (paper §3.1 "Coercive Subtyping", fn. 4):
- declared chains, e.g. `man ≤ human ≤ object` — from a `subtyping.txt` grammar file
  (fall back: every base CN type ≤ object).
- Σ-coercion: `Σ x:A. B ≤ A` via first projection π₁ — applying `f : A → Prop` to
  `p : Σ x:A.B` yields `f(π₁ p)` (paper (12): `Fo(walk(π₁ p))`; fn. 4 acknowledges this is the
  convenient reading). The coercion INSERTS π₁ into the formula during application.

Requirement satisfaction (`?Ty(T)` matching `Ty(S)`):
- reflexive; via declared subtyping; via Σ-coercion;
- polymorphic-instance: `?Ty(Π A:CN. A → Prop)` (verb slot, entry (11)) is satisfied by any
  `Ty(A₀ → Prop)` with `A₀` in the CN universe. Equivalently the shorthand `?Ty(object → Prop)`
  used in tree (31): a predicate node requirement accepts `A₀ → Prop` for any `A₀ ≤ object`.
  Implement one `satisfies(candidate, required)` predicate covering both spellings.

Application / β (used by elimination):
- `(Π x:A. B) @ a` and `(A → B) @ a` with argument type ≤ A (π₁-insertion when Σ-coerced);
  result type by substitution; formula by β-reduction of λ-terms.
- TYPE-DRIVEN elimination direction: in DS-MLTT the FUNCTOR can sit on the 0-daughter
  (quantified subjects: tree (16), GQ of type `(man→Prop)→Prop` applies to `walk`). Elimination
  must pick the daughter whose type applies to the other, not assume 1-daughter-is-functor.

Normalization for display (`simplify()`):
- `Σ x:A. ⊤` ≃ `A`; `π₁⟨a, b⟩ → a`; β-normal form. Keep the raw term too.
- Free Σ-witness closure at the root: `walk(π₁ p)` with `p : Σx:man.⊤` presents as
  `Σ p:(Σ x:man.⊤). walk(π₁ p)`, simplified `Σ x:man. walk(x)`.

## 2. Lexical entries (new bundled grammar `2026-english-mltt`)

Faithful to the paper's entries; templates parameterized like the TTR grammar:
- Proper name (8): `IF ?Ty(object) THEN put(Ty(human), Fo(bill))` — CLASS column supplies the
  base type (`Ty(CLASS)`).
- CN (10): `IF ?Ty(CN) THEN put(Ty(CN), Fo(man))` — the noun's Fo IS its type name in CN.
- Indefinite *a* (9): on `?Ty(object)`: make ⟨↓0⟩ `?Ty(CN)`, make ⟨↓1⟩
  `Ty(CN → object), Fo(λA:CN. Σx:A. ⊤)`.
- Universal *every* (15): on `?Ty(object)`: make the CN daughter and a functor daughter with
  `Ty(ΠA:CN. (A→Prop) → Prop)`, `Fo(λA:CN. λP:(A→Prop). Πx:A. P(x))`. After combining with the
  CN, the node is a GQ `Ty((man→Prop)→Prop)` that acts as FUNCTOR over the predicate (16).
- Verb (11): trigger the polymorphic predicate slot; `put(Ty(human → Prop), Fo(walk))`
  (transitive: `Ty(human → human → Prop)`, e.g. `examine`, tree (17)).
- Adjective, in-tree variant (30): on `?Ty(CN)`: make ⟨↓0⟩ `?Ty(CN)`, make ⟨↓1⟩
  `Ty(CN → CN), Fo(λP:CN. Σx:P. black(x))` → `Σx:dog. black(x) : CN` (32)–(33).
- Adjective, LINK variant (34)–(36): LINK from the ?Ty(CN) node; LINK-evaluation returns
  `Fo(Σy:dog.black(y))` into the CN node. (Second priority; needs LINK machinery.)
- VP adverb (37): on `?Ty(A → Prop)`: LINK node with
  `Ty(ΠA:CN.(A→Prop)→(A→Prop)), Fo(λA:CN. λP:A→Prop. λx:A. quickly(P(x)))`; implicit A at
  application; final `Fo(quickly(walk(john)))` (40). Veridical variant (41)–(43) optional/bonus.
- Computational actions: clone of the 2026-english-ttr set with `t ↦ Prop`, `e ↦ object`,
  elimination type-driven; plus re-enabled star-adjunction / link rules per the fixes track.

## 3. Scope (paper §4.2, trees (18)–(21))

Scope statements survive (they are NOT epsilon machinery): root `Scope(S_i, ...)` label;
an indefinite adds underspecified `U < p` with `?SC(p)`; resolution picks Σ/Π nesting:
- narrow (`U = universal`): `Scope(S_i < universal < p)` → `Πd:doctor. Σp:patient. examine(d,p)` (20)
- wide (`U = S_i`): `Scope(S_i < p < universal)` → `Σp:patient. Πd:doctor. examine(d,p)` (21)
Preferred realization: the two resolutions are alternative optional actions → two context-DAG
paths → both readings via `get_n_best_final_semantics`. Fallback: a `scope=` knob. Minimal
viable: linear-order default plus the ambiguity for one worked example (every doctor examined
a patient).

## 4. Integration points

- `get_final_semantics` becomes backend-agnostic (returns `Formula`; no TTRRecordType
  TypeError). `ParseResult.semantics` typed as Formula.
- `ParseResult.to_coq()` (module `src/dylan/formula/coq.py` or `mltt/coq.py`): emits a
  self-contained Coq file: `Parameter` base types + `Coercion` declarations for the subtyping
  chain, `Parameter` predicates (`walk : human -> Prop`), the final semantics as a
  `Definition` (Σ ↦ `{x : A & B}`/`exists` as appropriate, Π ↦ `forall`, ⊤ ↦ `True`),
  both raw and simplified forms. Optional `include_context=True`: §4.3's Γ_DS — a Coq
  inductive `DSAction` (25) plus the parse's action history as a `list DSAction` — sourced
  from the context DAG's action record (this is DyLan's existing action-replay data!).
- LaTeX: MLTT formulas render via a `to_tex` on the MLTT AST (Σ/Π/λ with proper spacing),
  reusing the latex pipeline.

## 5. Explicitly out of scope (this iteration)

- Coercive subtyping beyond declared chains + Σ-π₁ (no local coercions / meaning transfer).
- The ellipsis-rerun-as-context-operation formalization (§4.3) beyond exporting Γ_DS.
- Donkey anaphora (7), polydefinites, individual/stage-level distinction (sketched only).

## 6. Test targets (from the paper)

- `a man walks` → simplified `Σ x:man. walk(x)`; raw shows `walk(π₁ p)` shape. (12)
- `every man walks` → `Π x:man. walk(x)`. (16)
- `every doctor examined a patient` → narrow `Πd:doctor. Σp:patient. examine(d,p)`;
  wide reading available. (17), (20), (21)
- `a black dog walks` → `Σ z:(Σ y:dog. black(y)). walk(z)` simplified from the π₁ form. (33)
- `john walks quickly` → `quickly(walk(john))`. (40)
- `bill shouts` → `shout(bill)` with `bill : human`. (8)
- Ill-typed rejection: a verb typed `human → Prop` must not combine with a CN-incompatible
  subject if subtyping does not license it (many-sortedness payoff, §3.1 (1)).
- to_coq output compiles under `coqc` when available (skip-if-missing test).
