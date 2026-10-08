# Dialogue lab: shared trees and local repair

Choose **Dialogue** above the workbench grammar selectors. Editable turn rows
contain a speaker, words and a tree-boundary setting. A change of speaker
continues the current tree; **New tree** explicitly starts another proposition.
The same Classical/Constructive selectors apply. English presets demonstrate
shared completion, self-repair, correction by another speaker and two propositions.
The Question & answer preset adds a shared polar question and polarity answer.
The Greek grammars also have split-clause examples.

## Supported behavior

For `A: john likes` / `B: mary.`, A leaves `?Ty(e)` (classical) or `?Ty(object)`
(constructive) at `010`. B's lexical actions fill that slot. No second axiom is
introduced at the turn boundary. Word and operation frames retain the contributing
speaker and addressee. The resulting interpretation is `like(john, mary)`.

For `A: john likes mary.` / `B: sorry bill.`, the marker requests a local repair.
The parser backtracks across punctuation and computational completion to the
state before the nearest eligible lexical contribution. It then applies Bill's
ordinary lexical actions. It does not edit a completed formula string or run a
second grammar in the frontend. The prior branch remains in the context DAG, and
the final current-tree interpretation is `like(john, bill)`.

The transcript retains Mary (and its superseded punctuation), crossing them out
only once playback reaches the repair. The Repairs panel links to the original
word state, the rollback tree with its open requirement, and the replacement
word state. A rollback is explicitly a **context transition**, distinct from
`make/go/put` effects. Those effects still appear individually during replacement.

An explicit new tree adds an `AxiomEdge` to the context DAG instead of clearing
the DAG. Earlier trees and their completion snapshots remain inspectable. Ordinary
parse backtracking and local repair cannot cross this boundary. Word history
continues across it. The Earlier trees panel shows prior interpretations at the
relevant playback stage; Coq/formula export still concerns the current tree.

## Repair corrections in the engine

The existing repair path pushed the pending replacement onto the word stack
twice. The first traversal consumed one copy; the remaining copy made the parse
fail. It also bypassed successful-word history and floor bookkeeping. The repair
path now consumes the pending word once, records its actual speaker and addressee,
updates the floor and ends repair processing after a successful replacement.
Repair markers themselves are retained in word history.

This implementation repairs **the nearest eligible lexical contribution**. It
skips terminal punctuation and completion edges, stops at an axiom or a protected
lexical edge, and refuses an edge grounded for the repairer. It does not search
arbitrarily far back for a phrase or reinterpret earlier sentences. A zero repair
depth disables repair; positive settings currently permit this local strategy.
The marker `sorry` works for both the same speaker and a second speaker. Failed
replacements restore the previous post-word anchor and preserve its tree.

Grounding flags remain engine data; the lab does not infer understanding or
agreement from a speaker change. Existing grounding support should not be read
as a completed implementation of acknowledgement/acceptance/rejection acts.

## Native English questions and local reflexives

`A: Did you burn` / `B: myself?` / `A: No` now completes in both native
backends without lexical expansion or model calls. `did` grows a subject slot
and VP with a bare-verb requirement; the root carries `[+POLAR-QUESTION]`.
Question punctuation checks that the question is complete. Tense and full
auxiliary agreement are not represented.

`you` uses A's addressee B. At `myself`, the grammar requires the existing local
subject to denote the current word's speaker B. This remains true through
action replay, which restores each word's contributing speaker. A single speaker
saying `Did you burn myself?` fails that identity check. Third-person reflexives
use known person/gender/number features; unknown gender stays unspecified.

The lexical reflexive action contributes a typed local binding combinator in
the final object slot: `(OBJ → SUBJ → Prop) → BINDER → Prop` (e/t classically).
It consumes the verb on daughter 1 and produces `λ x. burn(x, x)`. The subject
then combines normally. Constructive nominal refinements use checked coercions
and witness projections; quantifier scope is preserved. The explicit
`[+REFLEXIVE]` label permits this direction of typed application, alongside
the existing quantifier rule. Both the action and semantic validator use the
same composition criterion. This is a restricted lexical treatment, not a
general implementation of reflexive binding in PPs or long-distance contexts.

Before Yes/No following a complete polar question, the API completes and saves
that tree, then adds an ordinary axiom boundary labelled **Answer tree**. An
explicit New tree works too. The answer action reads the immediate previous
tree through that `AxiomEdge` on the selected context path. It cannot skip over
a statement to retrieve an older question, or supply a missing argument to an
unfinished question. Yes copies the closed question content; No additionally
executes native semantic negation. The question is retained as earlier context,
not conjoined with its negative answer. Repairing `No sorry Yes` revises only
the answer and preserves the question.

Snapshots expose `speech_act` (query content or answer polarity) and
`reflexive_bindings` (local subject address, formula and word speaker). The UI
labels question content separately from answers. These are content
interpretations, not truth or grounding judgments. The generated Coq export
describes the current answer proposition; it is not evidence that the answer
is true. The grammar generator is `scripts/build_dialogue_extensions.py`,
called by the native English everyday generator.

## Diagnostics and scope

Parser-control tokens such as `sorry` are identified as controls in the coverage
report, so their absence from the grammar's lexical file is not reported as an
unknown word. A final repair marker without a replacement leaves the dialogue
incomplete, even if the preceding proposition was complete.

* `sorry bill.` at an initial axiom reports **missing repair context**.
* An incompatible known replacement reports **local repair unavailable**.
* An unknown replacement remains a **lexicon gap**.
* A new proposition attempted against a completed tree without a boundary reports
  a **tree-boundary** issue and explains the available controls.
* Accepted prefixes and incomplete earlier trees keep the overall result partial.

None of these failures automatically supplies a grammaticality judgment.
Beyond the restricted English polar answers above, general question–answer
ellipsis, wh-questions, clarification acts, group speaker reference and grounding
judgments remain unimplemented. Greek split clauses exercise shared tree
growth; the Greek grammar's `speaker/hearer/pro/him/theme` formulas remain its
fixed semantic demo context. They are not dynamically resolved to the turn names.

## API and state lifetime

Both existing parse endpoints accept either a `sentence` or a `dialogue`, with
the same bundled grammar and scope fields:

```json
{
  "grammar": "2026-english-classical",
  "dialogue": [
    {"speaker": "A", "text": "john likes mary."},
    {"speaker": "B", "text": "sorry bill.", "boundary": "continue"}
  ]
}
```

Limits: one or two named speakers, 1–12 nonempty turns, 500 characters per turn,
1200 characters and 80 tokens overall. Boundary values are `continue` (default)
and `new_tree`. Turns are processed in a **single parser context per request**.
Rebuilding or adding a turn submits the transcript again to an isolated worker;
there is no shared mutable server session across clients.

Results retain the standard three trace channels and add `dialogue`,
`token_metadata`, `repairs`, `context_trees` and `pending_repair`. Dialogue frames
carry `speaker`, `addressee`, `turn_index`, `clause_index`, `active_words` and
`context_count`. Repairs identify replaced token indices, replacement index,
rollback tuple and pointer transition. The `repair` frame is serialized from the
actual common-prefix tree of the old and repaired DAG paths. Earlier word
snapshots remain the history of what was parsed, including the superseded path.

The stream has the same start/frame/result contract; the final result supplies
the complete repair and earlier-tree indexes. Submitted text is never rewritten
to hide repaired words. A failed token stops processing the remaining transcript.

## Verification

`tests/test_dialogue_repair.py` verifies self/other correction in both native
backends, punctuation/completion traversal, speaker history, retained old branches,
grounding/axiom/disabled-repair boundaries and failure recovery.
`tests/test_dialogue_workbench.py` verifies presets, actual open-object continuation,
repair snapshots and active token indices, retained earlier meanings, distinct
context diagnostics, bounds and streamed/final trace agreement.
`tests/test_native_dialogue_questions.py` checks shared reflexive binding,
polarity, scope, local clause restrictions, mismatching features, missing answer
context, preserved question trees and answer repair. Constructive answer exports
are compiled with Coq when installed. `scripts/check_dialogue_browser.py` runs
the exact reported dialogue through both backends and checks the visible question,
answer, binding explanation, mismatch failure and mobile layout without an LLM.

`scripts/check_workbench_browser.py` exercises the editor, shared turns, before /
rollback / replacement inspection, crossed-out contributions, classical/constructive
switching, earlier-tree inspection, missing-context reporting, Greek shared clauses
and mobile layout in addition to its existing sentence and Greek lab checks.
