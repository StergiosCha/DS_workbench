# PP constructions and incremental lexical revision

## Native PP checkpoint

Both native English grammars now support postverbal `in`, `at` and companion
`with` PPs, and the selected `on` complement of `relies`. Examples:

- `john reads a book in a library.`
- `john walks in a park with mary.`
- `john relies on mary.` / `john does not rely on mary.`
- `john thinks mary walks in a park.` (matrix and embedded attachment)

The preposition creates a LINK modifier tree with its own DP complement. Its
meaning is composed by the same typed application as ordinary arguments. Classical
DPs retain `cn` and their two additional nodes, with epsilon/tau terms; constructive
DPs retain dependent witnesses and their Coq exports. Repeated PPs/adverbs extend
a completed LINK chain. Recomposition now reopens negation as well as complement
closure, so adding a modifier cannot erase an earlier `not`.

`in_location(place, proposition)`, `at_location(place, proposition)` and
`with_companion(person, proposition)` are opaque propositional modifiers. This
fragment has no event ontology, spatial inference, instrumental `with`, NP PP
attachment or general preposition polysemy. Location complements have the broad
object type; companion `with` requires human in MLTT. Classical entity typing does
not enforce that nominal restriction. Quantifiers in PP complements compose, but
no exhaustive scope calculus is claimed. The definite article `the` remains outside
this fragment; the examples use `a` rather than treating definites as indefinites.

The selected `prepositional-on` verb template has an ordinary argument DP carrying
an `ON-COMPLEMENT` requirement; it cannot complete without `on`. The verb keeps its
own predicate. Optional modifiers cannot discharge that argument requirement or
the existing give-family `to` requirement. Lexical proposals may instantiate this
new verb template only when their supplied analysis specifies it. Unspecific
WordNet PP frames are not automatically mapped to `on`.

The added native words (`reads`, `library`, `park`, `relies`/`rely` and the relevant
prepositions) are English demonstration entries. Their tests establish implemented
behavior, not independent corpus judgments. Greek grammar files are unchanged.

## Incremental lexical revision

In `lexical_mode: "jev"`, the new `incremental_v1` question asks only about sense.
The older frame classifier did not improve the development benchmark, so frames
are now left to DS continuation and backtracking. The historical `lexical_v1`
questions and 32-probe measurement remain unchanged and reproducible.

At lookup, Jev sees only the prefix preceding the word and the current tree. At a
later content-word boundary in sentence mode, it may reconsider one earlier
expanded word against the input observed so far. The state includes the target
index, observed prefix, provisional tree and validated candidate inventory. It
contains no later input or reference labels. There are at most three
reconsiderations per target and eight fresh Jev requests per parse in total.
Function words still trigger ordinary DS search without another sense request.

A changed preference is tried through actual DS execution. The probe starts at
the target word boundary, including any separate completion edges that precede
its lexical alternatives. It temporarily restricts the probe to the preferred
sense and replays the observed suffix. It cannot backtrack past that boundary.
The tree must pass semantic application checks; a prefix that could already
complete may not be replaced by one that cannot complete. The probe examines at
most 24 continuations, with at most 512 nodes searched at the word boundary and
the ordinary parser caps still applying.

The retained DAG inventory is never pruned. Temporary restrictions and edge flags
are restored, and a failed probe restores the primary cursor and meta bindings.
Its work is counted. Optional probe limits are reported as reconsideration limits;
they do not invalidate an otherwise valid primary derivation. A successful probe
becomes the active path and remains eligible for ordinary alternative enumeration.

The existing action trace records the rollback and replay. **Watch this revision**
returns to the corresponding primary trace step. The lexical panel distinguishes
changes required by **DS continuation** from a **Jev preference validated by DS**,
and shows unsuccessful/uncertain reconsiderations separately. The input history
and earlier tree states remain visible. Dialogue and repaired/control transcripts
retain their existing behavior; this reconsideration mechanism currently applies
only where the active path matches the complete observed sentence prefix.

## Executable development probes and validation

`data/lexical-revision/probes.json` contains four sentence probes run in each
semantic mode. Their WordNet reference labels were written before the run and are
**drafts awaiting independent review**. They never enter model inputs. These are
integration observations, not an independent lexical accuracy benchmark.

The first run made 20 fresh Jev requests. It exposed a completion-edge traversal
bug; after fixing that bug, all eight probes replayed the same cached answers with
zero fresh requests. Both lend surface orders then revised from bestow-quality to
the loan sense `lend_vhho02324182` after the arguments arrived, in both modes. The
classical crane example also revised to the bird sense after `walks`. All eight
parses completed; the four constructive exports passed Coq. On the intentionally
underdetermined bank example, Jev retained the river-bank sense rather than
abstaining. Successful parsing does not establish accurate disambiguation.

Final observations are in `data/lexical-revision/observations.json`; complete local
traces are in ignored `build/lexical-revision/live/`. The earlier failed traversal
observations were retained locally in `build/lexical-revision/before-completion-fix.json`.
Run `scripts/check_incremental_revision.py --live` explicitly to repeat integration
checks; existing local cache entries avoid new model calls. The new browser check
is `scripts/check_pp_revision_browser.py`.

Final full suite: **1187 passed, 3 skipped, 1 deselected**, 139.90 s. The exclusion
is the existing TTR LaTeX smoke check. All 810 existing corpus runs passed their
146 coverage-group floors; no corpus or coverage lock was changed. Focused tests
cover selected versus modifier PPs, quantified complements, missing arguments,
matrix/embedded attachment, classical DP nodes, Coq, negation preservation,
successful and rejected revisions, split completion edges, prefix isolation,
alternative preservation, and complete-prefix protection.
