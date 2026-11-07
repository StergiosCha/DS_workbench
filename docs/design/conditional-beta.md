# Conditional grammar beta — 7 November 2026

Select **Try Classical conditionals · Beta** in the app, or select Classical
and **English · conditionals (Beta)**. This is an opt-in grammar; the ordinary
English, Greek and TTR grammars remain available.

```
If John cries, Mary laughs.
Mary laughs if John cries.
If John likes Mary, Bill greets Sue.
```

The first example is from Gregoromichelaki's chapter; the other two are authored
checks. A comma, `then`, `, then`, or no boundary can separate an initial
antecedent from its consequent. Names: John, Mary, Bill, Sue, George. Intransitive
verbs: cries, laughs, walks, runs, shouts, arrives, leaves. Transitive verbs:
likes, knows, greets. Morphological agreement and tense are not modelled.

## Source and execution

Gregoromichelaki (2011), *Conditionals in Dynamic Syntax*, chapter 8 of
*The Dynamics of Lexical Interfaces*. The inspected local author copy is
`Downloads/Conditionals.pdf`, 41 pages, dated 27 May 2010, printed pp.231–271.
Relevant sections: §§8.4.1–8.4.3, especially (8.61), (8.68), (8.73)–(8.78).
The chapter's prose was inspected through §8.5; the rule on p.254 and the tree
on p.252 were also visually inspected. The original 2006 thesis has not been
obtained. Publication metadata and draft pagination are kept separate.

1. Introduction builds a situation argument of type `es` and a sister of type
   `es → t`. Subject/verb composition develops the latter.
2. `if`, at `?Ty(es)`, grows a LINK to another `?Ty(es)` node. Below it are the
   `cns → es` binder, a `t → cns` restrictor constructor, and the antecedent
   proposition with its own fixed free situation variable.
3. Ordinary lexical actions and beta reduction construct the antecedent. The
   inherited `cn(s,P(s))` pair representation is given the sorted type `cns` in
   this grammar. The binder is compiled as `λP:cns. τu:es.predication(P,u)`;
   it produces a situation term, not an individual term or a binary connective.
4. LINK evaluation copies the completed τ term into the main situation slot.
   A pending `SITUATION-SHARED` check is replaced with a concrete `SharedFo`
   requirement, discharged by ordinary thinning against the retained LINK.
5. The consequent applies to this term. Existing Classical choice evaluation
   runs during DS elimination, yielding the chapter's restricted conditional
   pattern `P(α) ⇒ Q(α)`, where `α = τs:es.(P(s) ⇒ Q(s))`.

All make/go/put/delete effects, intermediate requirements and typed applications
are recorded in the normal playback. Nothing is translated from a completed
TTR tree. No LLM is used. The API rejects model, personal-rule, paragraph and
dialogue options for this beta; the browser disables the corresponding modes.

## Deliberate bounds and adaptations

This implements a **fixed situation-position fragment**, not every parsing
strategy in the chapter. For postposed `if`, prediction leaves the matrix
situation slot pending and returns there after constructing `es → t`. This
avoids inventing a contextual situation before reading `if`. It does **not**
implement the chapter's Late-*Adjunction and local MERGE route in §8.4.4.1.
General unfixed attachment, embedded readings, topic and recapitulation routes,
quantified NPs and cross-clause pronoun dependencies remain pending.

The source's contextual restriction `R` is represented here by an **assumed,
fixed, nonempty domain of relevant situations**, stated in the interface and
exports. No contextual restriction is inferred or silently claimed resolved.
This beta excludes tense/aspect, modal worlds, counterfactuals, temporal and
causal clauses, and speech-act conditionals. It does not require either clause
to be separately true. Ordinary statements without an `if` leave an unresolved
situation requirement in this particular grammar.

The printed lexical entry (8.73), line (7), creates the restrictor functor
daughter but does not print the move into it; the implementation includes that
move as required by the pictured tree and the explanatory text. Fresh variable
allocation scans the current tree and semantic profile. The underlying binder
uses the existing capture-avoiding substitution and normalization.

The source and this beta use Classical ε/τ semantics. A Constructive adaptation
must separately define situation witnesses and dependent conditional types;
a TTR adaptation must separately supply its record/context operations. Their
availability elsewhere in the app does not establish beta parity.

## Temporal clauses in Chatzikyriakidis (2010)

The user's thesis supplies relevant **structure, lexical timing and contrasts**:

- **§2.2.2.4, pp.83–85, (2.99):** a complex situation argument with a fresh
  event/situation, reference time `R`, and an ε binder. In the past example,
  the restriction includes `s ⊆ R` and `R < s_now`. The main predicate and
  situation structure combine by ordinary function application.
- **§4.2.1, p.166, (4.9)–(4.12):** Cypriot `molis` (as soon as), temporal
  `pu` (when), `aman` (if/when) and conditional `an` occur with proclisis.
  Preserve the source variety and order contrasts when adding test cases.
- **§4.2.2, pp.170–171, (4.29)–(4.30):** strictly temporal `eno` takes
  proclisis in the reported examples; contrastive `eno` takes enclisis.
  Selecting a temporal versus contrastive relation can therefore affect
  permissible tree growth and clitic order, not merely the printed predicate.
- **§4.6.2, pp.187–196, (4.49)–(4.55):** the subordinator introduces
  `?Ty(es)` and leaves the pointer at the subordinate `?Ty(t)`; the verb
  supplies the situation type and tense/aspect structure. LINK begins at the
  lower reference-time position. Evaluation relates the antecedent situation
  to consequent reference time `R` instead of equating the two highest
  situation terms. The thesis explicitly describes the unification as a
  sketch needing further checking (p.193), and extends the pending-situation
  assumption to conditional, temporal and causal subordinators (p.194).
- **§3.4.3.2, pp.144–147, (3.117)–(3.118):** the SMG perfect auxiliary
  supplies reference-time/situation structure; overlap, state and `LOC`
  contributions preserve the perfect distinctions. It should not be replaced
  with an undifferentiated past marker.

This is a basis for the next temporal beta, not evidence that the present one
already implements those proposals. We must retain separate clause situation
terms, each verb's tense/aspect restriction, and an explicit relation to `R`.
The different meanings of `when`, `before`, `after` and `until` still need their
own justified lexical programs; the chapter's τ binder must not be assigned
to every temporal connective.

Two particularly useful next checks are the thesis's temporal/contrastive
`eno` clitic-order contrast and Gregoromichelaki's **(8.79)–(8.84), pp.258–259**:
`John left when Mary claimed that Bill left` permits a time associated with
Mary's claim or Bill's leaving; the corresponding `if` example lacks that low
construal. The latter difference depends on the fixed situation variable
inside `if` versus an unfixed strategy for temporal relatives.

## Validation

`tests/test_conditional_beta.py` checks LINK term identity, sorted application,
complete and incomplete clauses, both word orders, strict grammar loading,
operation/stream replay, API mode boundaries and isolation from the ordinary
grammar. An independent finite-model evaluator checks both orders in every
assignment of the two predicates over two situations, under both choice
enumeration orders: **64 output/model comparisons**.

`scripts/check_conditional_beta_browser.py` checks the actual beta button,
presets, source explanation, both orders, failure display, mobile layout and
return to the ordinary grammar. These are fragment tests, not open-text
coverage measurements.
