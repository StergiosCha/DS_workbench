# Reusable clause constructions and model selection — 4 October 2026

The previous assistance contract permitted content-word hypotheses only. That
made unfamiliar conjunctions a dead end even if they expressed a relation the
engine already knew how to compose. The interface now separates **surface
lexicalization**, **relation interpretation**, and **DS tree growth**.

`clause_inventory.py` declares twelve relations, their descriptions, and the
reviewed readings of English and Standard Greek connectives. One parameterized
finite-clause program supplies both postposed LINK growth and preposed content
arguments (with an explicit comma). It uses the same local content closure and
backend-specific type checks as causal clauses. The historical `CAUSAL-*`
markers remain internal implementation names; they now support the family.

The grammar builder adds common connectives without requiring AI: when,
whenever, before, after, until, if, unless, although, though, whereas, and
ambiguous while/since/as/once; Greek includes όταν, όποτε, αν/εάν, παρότι,
μολονότι, ωσότου/ώσπου, and ambiguous ενώ/αφού. Causal entries remain supported.
These are finite-clause uses, not every use of the same surface word.

In Open text mode, the selected chat model can return a structured hypothesis:

```json
{"constructions": [{"surface": "provided", "relation": "condition",
                    "evidence": "Introduces a finite condition here."}]}
```

The compiler accepts requested, single-token surfaces and relation IDs from the
inventory. Known connectives are further restricted to their declared readings.
It validates the entire batch and instantiates loaded lexical templates; it
accepts no executable model text, new type signatures, formulas or replacement
sentences. Content-word requests can also return a constructions array. This
matters for unfamiliar conjunctions: they no longer exhaust the vocabulary
retry budget by being forced into noun/verb schemas. Optional source citations
still concern content-word entries; construction explanations are model
hypotheses, not source-verified claims.

Ambiguous known connectives receive a construction request before parsing.
On a failure, a candidate connective can receive a targeted construction
request with the actual failed prefix. A preference reorders existing programs
or adds a new lexicalization; all original alternatives remain available.
DS builds, composes, backtracks and determines completion. Search may therefore
use a different relation from the proposal. The UI and JSON separately expose
the proposed relation and the lexical construction on the actual DS path.
No uncertainty score or semantic-correctness guarantee is invented.

Known-word preferences reset between paragraph sentences. New lexicalizations
remain request-local hypotheses, like other lexical additions. They are
labelled reused when their proposal context differs from the current sentence.
A sentence repeating an ambiguous surface does not receive a single global
reading preference: occurrence-specific ranking remains pending. Three model
requests total are shared with vocabulary assistance; construction requests
have a 16-second ceiling inside the existing 48-second helper budget. Provider
outages leave the reviewed grammar available. There is no persistent training.

The relations are intentionally explicit but semantically coarse. They take
`(main, subordinate)` contents; temporal precedence and conditional/concessive
relations are never collapsed to `because` or conjunction. Classical closes
its own proposition/choice contents. Constructive closes local Σ/Π contents
and exports relations with `Type -> Type -> Prop`. These are opaque predicates,
not an implemented event/time calculus, counterfactual semantics, or a claim
that natural-language conditionals are material implication. A well-typed
analysis can still have the wrong relation or attachment. TTR has no compiler
for this interface and is explicitly excluded.

Nested-clause testing found an earlier loss-of-meaning path: a late adverb
could revisit an embedded VP inside an already captured main content and erase
an outer clause relation. Capturing a main content, or crossing a fronted
clause's comma, now seals its embedded clause contents against that backward
modification. Meaning-preservation tests cover every returned reading in the
reported case, not merely the first successful tree.

Validation includes all relation families in both native backends, Greek
counterparts, front/back placement, nested relations, negation, modifiers,
quantifier closure and Coq export. Missing clauses, nominal/gerund complements,
interrogative when and unsupported rules remain failures. Provider fixtures
test new lexicalizations, contextual choices, atomic rejection, outages and
paragraph preference reset. Real OpenRouter checks parse previously unsupported
`provided` and `καθότι` through actual model proposals in both backends. A
deliberately ambiguous `since` example records the preference without claiming
it is the uniquely correct reading. Browser checks cover visible proposals,
actual choices, export, key privacy and mobile layout.

This is a reusable construction interface for one important family, not an
arbitrary grammar synthesizer. Multiword markers, nonfinite clauses, richer
auxiliaries/passives, unrestricted attachment and full semantic inference need
additional reviewed primitives. The LLM can recognize, select and lexicalize
available constructions; it cannot establish the correctness of a new DS
theory by returning a tree. Existing held-out coverage measurements remain the
baseline; hand-written examples are regression evidence, not language accuracy.
