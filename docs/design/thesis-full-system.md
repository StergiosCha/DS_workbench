# The full DS system (Chatzikyriakidis 2010, PhD thesis, Ch. 2) — implementation spec

Target: implement the COMPLETE formal system of the thesis, with the constructive (MLTT)
semantics of Chatzikyriakidis (2025) as the semantic top (see constructive-ds-design.md).
Classical DS retains epsilon/tau (thesis §2.2.1). The separate constructive
backend uses Σ/Π. Everything else in Ch. 2 is in scope. ASCII notation used below: <d0> = down-0 modality, <u1> = up-1,
<d*> = down-star, <u*> = up-star, <d+>/<u+> = Kleene plus, [d]/[u...] = universal (box)
versions, <L>/<L-1> = LINK and inverse.

## 1. LOFT layer (§2.1.1, table 2.3)

Operators: down, down0, down1, up, up0, up1, each in existential <...> and universal [...]
versions; Kleene star and plus closures of down/up; LINK L and L-1. Full table:
<d>X <d0>X <d1>X <d*>X <d+>X [d]X [d0]X [d1]X [d*]X [d+]X and the up-mirror set.
Semantics: <.> = exists a node along the relation where X holds; [.] = X holds at ALL nodes
along the relation (vacuously true if none — [u]X true at root). <d+> = <d><d*>.
EXTERNAL modalities (§2.1.1, (2.5)): `d* X` without brackets — underspecified description
of a FIXED tree (true when a fixed chain of daughter steps reaches an X node). Internal
<d*>X is falsified by fixed-only relations when the intent is underspecification of an
underspecified relation; external collapses with internal for fully specified modalities.
Implementation: evaluation of every operator combination against a tree, used by rule
triggers, requirements ([d]⊥ bottom restriction!), and MERGE address entailment.

## 2. Decorations (§2.1.2)

Fo(.), Ty(.), Tn(.) obligatory on every complete node; Tn values are LOFT addresses or
arbitrary constants Tn(a) (unique among fixed nodes). Additional feature decorations
(diacritics, open set): Mood(x), [NEG+], Indef(+), Case features, person(x) etc. —
representable as put-able labels. Requirements ?D for ANY decoration D (?Ty(t), ?Fo(a),
?Tn(010), ?<u0>Ty(t) case filter, ?∃x.Fo(x), ?∃x.Tn(x), ?<D>Fo(a) for D∈{d0,d1,d*,L}).
Requirements are the only non-persistent decorations; a well-formed final tree has none
outstanding anywhere (including LINKed trees).

## 3. Pointer (§2.1.4); CONTROL features (§2.1.5)

Pointer ◇ marks the unique node under development; all updates happen at the pointer.
CONTROL features: statements in lexical IF-triggers that describe the current partial tree
but are NOT put on the tree — e.g. negative statements <d*>Ty(e)⊥ ("no type-e node below"),
[d]⊥ used as trigger, Speaker/Addressee conditions. Triggers must therefore support
arbitrary DU statements incl. negation, not only node-local labels.

## 4. Metavariables & SUBSTITUTION (§2.1.6)

Fo(U), Ty(V) metavariables with optional presupposition restrictions (Fo(U_male)), always
paired with ?∃x.Fo(x)/?∃x.Ty(x). Update either lexically or by SUBSTITUTION from context,
subject to a locality condition: the substituent must not label any node in the local
domain (anti-locality for pronouns/pro-drop subjects). Person restrictions on U encoded
as presuppositions (used heavily by clitics).

## 5. Lexical entries (§2.1.7)

IF/THEN/ELSE with arbitrary nesting and disjunctive IF parts (φ | ψ). Actions:
make(<di>), go(modality), put(...decorations...), freshput(x, Fo(x)) (fresh variable),
gofirst(?Ty(t)) (move pointer to first/most-local node matching a description — the thesis
uses gofirst(?Ty(t)) at the end of verb entries), abort. Entries are templates over
parameters (concept PRED, tense, person, case).
Examples to reproduce as templates (MLTT-typed in our grammars):
- (2.10) English proper noun: IF ?Ty(e) THEN put(Ty(e), Fo(bill), [d]⊥) ELSE abort.
- (2.11) accusative-case NP: adds case filter ?<u0>Ty(e->t) (object position);
  (2.52) nominative NP: ?<u0>Ty(t) (subject position). Case = output filter on position.
- (2.12) SMG monotransitive verb (pro-drop, trigger ?Ty(t)): builds the FULL propositional
  template: predicate spine, object node with ?Ty(e), subject node with Ty(e), Fo(U_x),
  ?∃x.Fo(x), verb formula with [d]⊥ on the predicate-bottom node; ends gofirst(?Ty(t)).
  English verbs instead trigger on ?Ty(e->t) (fn. 31) and do not build the subject.

## 6. Computational rules (§2.1.8) — the closed universal set

- (2.19) INTRODUCTION (general, over metavariables X, Y):
  {...{?Ty(Y)...◇}} => adds ?<d0>Ty(X), ?<d1>Ty(X->Y) at the pointed node.
- (2.21) PREDICTION (general): builds both daughters decorated with the subrequirements,
  pointer to the 0-daughter. Restricted subject/predicate instances (2.23)/(2.24) are the
  Cann et al. 2005 versions (t => e, e->t). NOTE (thesis p.41): newest DS abandons
  Intro/Pred; SMG parsing does not use them (verbs project templates; subjects use
  *ADJUNCTION or LINK). Implement the general rule, include the restricted instance in the
  English grammar only.
- (2.26) COMPLETION: pointer at daughter with Ty(X) and no outstanding ?: move to mother
  via <ui>, i ∈ {0,1,*}, record <di>Ty(X) at mother. REVISED (2.88): mu ∈ {u0,u1,u*,L-1}
  — completion also crosses LINK boundaries back.
- (2.28) ANTICIPATION: pointer from mother to any daughter with outstanding requirements.
- (2.31) THINNING: {..., X, ?X, ◇} => remove ?X.
- (2.34) ELIMINATION: pointer node with <d0>(Fo(a), Ty(X)) and <d1>(Fo(b), Ty(X->Y)),
  no outstanding daughter requirements: put Fo(b(a)), Ty(Y). In the MLTT top, the
  application direction is TYPE-DRIVEN (GQ subjects: 0-daughter can be the functor) and
  typing uses subtyping + Σ-coercion (see constructive-ds-design.md §1).
- (2.37) *ADJUNCTION: {Tn(n), ?Ty(t), ◇} => new unfixed node <u*>Tn(n), ?Ty(e),
  ?∃x.Tn(x), ◇. (Trigger: bare ?Ty(t) node — thesis applies it with just Tn(n),?Ty(t).)
- (2.44) LOCAL *ADJUNCTION: {Tn(a), ?Ty(t), ◇} => locally unfixed node
  <u0><u1*>Tn(a), ?Ty(e), ?∃x.Tn(x), ◇ — fixing site restricted to the local
  argument domain (one 0-step then 1-spine). In the dialects, this is lexically encoded in
  clitic entries rather than a general rule (parametric).
- (2.46) LATE *ADJUNCTION: pointer at a TYPE-COMPLETE node {Tn(a), Ty(X)} within a
  ?Ty(t) tree: project unfixed daughter <u*>Tn(a), ?Ty(X), ?∃x.Tn(x) — used for VSO
  subjects (parse on unfixed node below the already-decorated metavariable subject node),
  clitic doubling, extraposition.
- (2.41) MERGE: DU ⊔ DU' where ◇ ∈ DU', union consistent, address entailment
  (underspecified <u*>Tn(a)/?∃x.Tn(x) updated by fixed address; unfixed loses its
  address requirement). Conflicting Fo values block MERGE.
- (2.79) LINK ADJUNCTION: {Tn(a), Fo(α), Ty(e), ◇} => LINKed node <L-1>Tn(a), ?Ty(t),
  ?<d*>Fo(α), ◇ (relative clauses; the copy requirement drives the relativizer).
- (2.83) relativizer (e.g. SMG pu): IF ?Ty(e), ?∃x.Tn(x), <u*><L-1>Fo(x) THEN
  put(Fo(x), Ty(e), [d]⊥) — copies the head formula onto the unfixed node inside the
  LINKed tree.
- (2.90) LINK EVALUATION (non-restrictives): main node Tn(a), Fo(a), Ty(t) with LINKed
  <L-1>MOD(Tn(a)), Fo(b), Ty(t): main Fo := a ∧ b. (MLTT top: conjunction = Σ/∧ of
  Props; restrictives evaluated at the CN level per the 2025 paper's LINKed-adjective rule.)
- (2.93) TOPIC STRUCTURE INTRODUCTION: {Tn(0), ?Ty(t), ◇} => <L>Tn(0), ?Ty(e), ◇
  (HTLD).
- (2.94) TOPIC STRUCTURE REQUIREMENT: after the dislocated Fo(a), Ty(e) is parsed on the
  <L> node: pointer to ?Ty(t) node, add ?<D>Fo(a), D ∈ {d0, d1, d*, L} (resumption/copy
  requirement; in pro-drop SMG satisfied by metavariable substitution).
- (2.98) coordination 'and' (lexical): IF Ty(X) THEN make(<L>); go(<L>); put(?Ty(X)) —
  works for e, t, e->t coordination. LINK evaluation conjoins.
- Tree-growth constraint (p. 56, (2.48)-(2.49)): the tree logic does NOT permit two
  unfixed nodes with the SAME underspecified modality type simultaneously — by treenode
  identity they collapse into one node (their DUs union; incompatible Fo values then crash
  the parse). Unfixed (u*) vs locally-unfixed (u0 u1*) are DIFFERENT types and may
  coexist. Implement collapse-on-second-introduction (not a ban): this is the PCC engine
  (ch. 6): two 3rd-person clitics both on locally-unfixed nodes collapse and crash;
  1st/2nd person clitics build fixed nodes and escape it.

## 7. Tense/aspect (§2.2.2.4) — MLTT adaptation

Thesis/Cann-forthcoming: situation argument node Ty(e_s) with complex internal structure
(cn_s spine), reference-time metavariable R, past: s_i ⊆ R ∧ R < s_now, closed by ε.
MLTT top: situation/time as CN-universe types (Situation ≤ object); verbs optionally
subcategorize a situation argument; tense = predicates over situations (past(s) ≡ s < now
as an axiomatized Prop); the ε-closure becomes Σs:Situation.(...). Keep this layer optional
per-grammar (the 2025 paper's event-restrictor LINK style is the default for the English
grammar; the full e_s spine is a documented extension).

## 8. Parsing strategies (§2.3)

Subjects parseable via *ADJUNCTION, LINK (topic), or fixed positions — the parser's
context DAG must expose all licensed strategies as alternative paths (n-best), since
dialect variation and diachrony live in exactly this ambiguity.

## 9. Grammars to ship

1. `2026-english-mltt` — English with the constructive top: paper entries + Ch.2 English
   entries ((2.10), Intro/Pred restricted, *ADJUNCTION for left dislocation, LINK
   relatives, HTLD, coordination, adjectives, adverbs, every/a as Π/Σ).
2. `2026-smg-mltt` — Standard Modern Greek demo: pro-drop verb templates (2.12),
   case-filter NPs (2.11)/(2.52), *ADJUNCTION SVO/OVS, LATE *ADJUNCTION VSO,
   pu-relatives, HTLD with TOPIC rules, clitics per thesis ch. 3.4 (entries from the
   extraction agent), PCC via the tree-growth constraint (ch. 6.2), MLTT semantics
   throughout (concepts as CN-typed predicates).
Test corpora: thesis examples (2.50)-(2.69) SVO/VSO, (2.80) pu-relative, (2.95)-(2.97)
HTLD, clitic examples from ch. 3; paper examples (12)-(43) for English.
