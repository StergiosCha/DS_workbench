# DS Workbench

The local workbench presents the current Python parser through a small JSON API.
It needs no JavaScript build, CDN, or Pyodide installation. Start from the source
checkout with:

```sh
.venv/bin/python -m dylan.workbench_server --port 8769
```

Open http://127.0.0.1:8769. After reinstalling the package's entry points,
`ds-workbench --port 8769` is equivalent. This command requires the source
checkout's `workbench/` assets; those assets are not distributed in the library
wheel. The original static frontend and its command remain under `web/` and
`dylan.web_dev`.

## Interface

- Choose Classical DS, Constructive DS, or DS-TTR, then an installed grammar.
  Sentences are limited to 500 characters / 40 tokens.
- Choose Dialogue to enter speaker-labelled turns that share a developing tree.
  Local repair exposes the rollback and replacement, and explicit New tree
  boundaries preserve earlier trees. Dialogue input allows up to 12 turns,
  1200 characters and 80 tokens; see [dialogue scope and protocol](dialogue.md).
- The initial constructive example is parsed automatically. Playback starts at
  the axiom in Operations mode; frames arrive over an NDJSON response stream.
- Complete analyses defaults to the first result. Request up to three or eight
  to explore alternatives, then use Play analysis to unfold a selected tree
  from its axiom. Its words, rules, operations, meaning and Coq export follow
  that analysis. Dialogue currently retains one selected transcript derivation.
  Try `john thinks that mary walks quickly.` with three analyses: the adverb
  can attach to the matrix predicate or inside the complement in both modes.
- Words mode displays the axiom, recorded token boundaries, and an additional
  completion state when needed. Rules mode groups lexical/computational actions.
  Operations mode steps through their executed make/go/put/delete/merge/reduction
  effects. It shows IF checks, the selected branch, the active instruction,
  pointer before/after, and added/removed nodes and decorations.
- Play/Pause, speed (0.5×–4×), the slider, token buttons, and arrow keys navigate the trace.
  Home returns to the axiom; End shows the final state. Space toggles playback
  when focus is outside an input or button.
- Select a tree node to see full decorations, formula, and requirements. Green
  marks the pointer; pale green marks nodes changed since the previous frame.
  Unfixed edges are dotted, LINK/context edges dashed. Zoom and drag inspect
  larger trees; Fit restores the overview. Trees use compact diagonal branches,
  with 0 daughters to the left and 1 daughters to the right, including partial
  trees whose sibling has not yet been created.
- The selected backend supplies node formulas and the root interpretation.
  Native root formulas appear when the daughters can combine. Constructive
  meanings show raw and simplified terms; scope selection sets witness closure.
  Copy copies the raw formula; Export JSON downloads the result and all three traces.
  Constructive complete meanings also offer Coq export.
- The Greek lab compares small Standard, Cypriot and Pontic fragments in either
  native semantic mode. Build an example or its reverse order; history panels
  separate Koine/medieval evidence from the proposed DS explanation of change.
- Complete, accepted-but-incomplete, and rejected parses have distinct states.
  On a rejected word the trace stops, preserving the last accepted tree. The
  diagnostics distinguish missing vocabulary, construction gaps, sourced placement
  violations, semantic type mismatch and unexplained failure. Lexical coverage and
  independent grammaticality evidence are reported separately for successes too.

The interface displays the engine's output, including its current semantic
limitations. It does not assert that every accepted sentence has a linguistically
correct semantic analysis. The native English fragment is described in [native semantics](native-semantics.md).
The small Greek fragments, comparisons, historical sources and remaining thesis
coverage are described in [Greek clitics](greek-clitics.md).

## Trace semantics

Word frames serialize the parser state directly after each accepted token.
Action frames reuse `dynamicsyntax._parse._steps_from_edge`. That facility replays
actions and falls back to a grouped transition when individual replay fails.
Each word's action sequence ends with the recorded word state, which remains the
authoritative boundary. Individual operations are captured by an opt-in
observer at the engine's effect execution boundaries. Nested rules and lexical
macros expose their executed leaves. Failed branches discard their tentative
trace, and snapshots freeze labels/metavariables. Unreplayable transitions are
explicitly marked as grouped. This is not an alternative grammar interpreter. This is derivation replay, not a live atomic debugger or
a log of every rejected search branch.

Each snapshot includes all labels, outstanding requirements, pointer, address
fixedness, edges, completion status, backend, and semantic interpretation. Projection
runs on a cloned tree with pooled metavariable bindings saved/restored, so
inspection does not decorate the parser's tree. Partial TTR projections can contain
underspecified fields. Native incomplete roots report no root formula; their node
decorations remain inspectable. Nominal application errors are reported explicitly.

## API and execution

`GET /api/config` returns available bundled grammar IDs, examples, and limits.
It also includes dialogue presets and bounds.

Sentence requests accept `n_best` (integer 1 through 8, default 1) and
`reading_traces` (boolean, default false). After recording a complete primary
result, the worker enumerates further leaves by ordinary parser backtracking.
Each `readings` item contains a complete tree, semantics, Coq text when
constructive, action names, and structural strategy tags (`star-adjunction`,
`link`, or `fixed`). Trees with the same decorations, meaning and strategy are
deduplicated. These tags describe operations; they do not certify topic/focus
status or a linguistic judgment. General star adjunction and LINK can occur
together. The first analysis uses the primary trace; later analyses carry
their own `trace` when requested.

`reading_search` reports the requested/returned counts, candidates examined,
extra search statistics, lexical cuts and one stop reason: `reading_limit`,
`candidate_limit` (100 examined leaves), `search_limit`, or `exhausted`.
Exhaustion is relative to the available lexical entries and configured entry
limit. Failure or an incomplete primary returns no complete readings and
`no_complete_primary`; dialogue reports `dialogue` and rejects `n_best > 1`.
Alternative search never replaces the primary result, its traces or its
statistics. Its extra counters are reported separately. The worker's overall
30-second timeout still applies. Corpus rows with a sourced `variable` judgment
request up to eight readings; strategy diversity affects only their existing
agreement metric, never their source judgment.

`POST /api/parse` accepts:

```json
{"sentence": "every doctor examined a patient.", "grammar": "2026-english-mltt", "scope": "narrow"}
```

Alternatively supply `dialogue`, an array of `{speaker, text, boundary}` turns.
The parser shares a context across those turns; `boundary: "new_tree"` starts
a new tree without discarding the earlier DAG. The default is `continue`.

The result contains `tokens`, `ok`, `complete`, `failure`, `words`, `actions`,
`operations`, `diagnostics`, `elapsed_ms`, `trace_note`, `backend`, `scope`, and optional `coq` source. Diagnostics include parser status, per-token lexical coverage and independent
sourced judgments for identified Greek comparison cases (otherwise not assessed).
Each frame contains a label, token index, kind,
nodes, edges, pointer, semantics, semantic error, and requirement count.

`POST /api/parse/stream` accepts the same request and returns newline-delimited
JSON. A `start` event supplies the axiom and tokens, followed by `frame` events
with `words`, `actions` (rules), or `operations` channels, then a `result` event containing the complete
JSON result. Word states are recorded directly. Rule and operation frames
replay the selected derivation through the normal engine executor. The browser can pause while the
worker continues. Worker errors after streaming begins appear in the final event.

Dialogue results additionally carry speaker metadata, repair records and earlier
tree snapshots. The original transcript stays intact when material is repaired.
Parser controls, missing repair context and incompatible replacements are
distinguished from missing vocabulary; none implies a grammaticality judgment.

The server binds to loopback and serves its own assets. Grammar selection is
restricted to discovered bundled IDs. Two isolated Python subprocesses can run
concurrently, each with a 30-second timeout. Isolation is necessary because the
engine uses process-global metavariable pools. Results are stateless JSON; the
browser keeps playback state locally and nothing is persisted by the server.

Invalid requests return 400, parser errors 422, worker timeouts 408, and busy
responses 503. Unknown endpoints return 404. The server does not enable CORS and
rejects POST origins that do not match its address.

## Verification

```sh
.venv/bin/python -m pytest -q tests/test_workbench.py tests/test_native_semantics.py
.venv/bin/ruff check tests src/dylan/workbench_api.py src/dylan/workbench_server.py
node --check workbench/app.js
```

With Playwright and Chromium installed, run the browser check against the server:

```sh
python scripts/check_workbench_browser.py --url http://127.0.0.1:8769
python scripts/check_readings_browser.py --url http://127.0.0.1:8769
```

It exercises desktop/mobile layout, parsing, synchronized semantics, playback,
instruction highlighting, make/go/put separation, node and trace inspection,
clipboard, grammar switching, zoom, JSON export,
error states, and malformed/cross-origin requests. Screenshots default to
`/tmp/ds-workbench-browser/`.

The checks cover classical ε/τ preservation, constructive Σ/Π composition,
nominal rejection, capture avoidance, scope, real Coq compilation when available,
stream event fidelity and the existing TTR examples. The browser check verifies
that a single axiom visibly grows automatically and remains fixed when paused,
then exercises all three modes, scope, LINK, export and mobile navigation.
The known PDF smoke test requires the locally missing `pst-tree.sty` package.

The readings browser check uses the shipped two-attachment example and an
explicit temporary lexical ambiguity fixture. It verifies that changing an
analysis restarts its own tree at the axiom, that make/go remain separate,
that final meanings differ, and that Coq export follows the selected analysis.
Both native modes and mobile width are checked without live lexical calls.
