# Visible Jev comparison — 4 October 2026

The user can open **See Jev in action**, connect OpenRouter and try **Lend ·
temporary transfer**. The application performs two DS parses of `John lends a
book to Mary.` with exactly the same installed lexical inventory. Normal lexical
ordering is compared with the existing incremental Jev sense selector and its
DS-checked reconsideration. The general vocabulary model is independent of the
pinned `typesafe/jev-1.13-20260917` native Choice service.

The live native Classical and Constructive checks both showed a change from
`v02324478` (“bestow a quality on”) to `v02324182` (“give temporarily”). Jev first
answered uncertain at `John lends`, then preferred the loan sense after `a book`.
DS replay retained its current tree at that point because it found no compatible
continuation; the revision succeeded after the observed prefix included `to Mary`.
Both DS runs completed, using three fresh Jev calls per backend. This inspected
example demonstrates the distinction between structural completion and lexical
adequacy. It is not a general accuracy or backtracking claim. Live answers may
vary. The bank example has intentionally insufficient disambiguating context.

The [recorded public check](../../data/lexical-revision/jev-comparison-live-2026-10-04.json)
preserves both meanings, distributions, observed prefixes, replay outcomes and
deployment identity. On that later run Classical Jev still answered uncertain
after `a book`; both backends nevertheless accepted the loan-sense revision
after `to Mary`. This variation is shown by the interface, not replaced with
the earlier demonstration's probabilities.

Additional live local checks completed the crane and bank examples in both
backends. For crane, Classical changed from machine to bird, while Constructive
already selected bird without Jev. For bank, both retained riverbank; the context
does not independently establish that sense. Their results are included in the
recorded evidence as supplemental local checks, with no claim of improved
accuracy across the examples.

## Contract

- `compare_jev: true` requires `lexical_mode: "jev"`, `decision_mode: "off"`,
  `n_best: 1`, and a native English Classical or Constructive sentence.
- `jev_comparison.py` prepares the inventory once using Jev vocabulary mode.
  Missing-word lexical-model fallback proposals, if needed, are shared by both
  runs. The baseline does not make Jev calls. Merely switching from dictionary
  mode would be unfair: its bundled-extension-first lookup order differs from
  Jev mode's WordNet-first inventory preparation.
- Each fresh parser reconstructs trusted lexical source programs and copies
  metadata/profile; installed inventory hashes must match. Pooled metavariable
  bindings are reset between runs and the caller's bindings restored afterward.
  No request JSON field is used as a callable setup or lexical program.
- Both runs retain all installed programs. Existing entry/search limits still
  apply. Only Jev sense ordering and DS-checked revision differ. General tree
  search gates remain off. The existing .50 preference threshold, uncertain
  option, eight-fresh-call limit and replay bounds remain unchanged.
- The baseline is executed with a four-second allowance and without the full
  animation trace. The comparison budget is 50 seconds from preparation start;
  worker limit remains 55 seconds. Timings therefore are not directly comparable
  performance measurements. Time budgets use the existing worker/main-thread
  alarm mechanism. A baseline timeout yields an inconclusive comparison and
  does not suppress an otherwise successful primary Jev parse.
- `jev_comparison` exports actual before/after completion, formulas, used
  lexical analyses, derivation action names, stats and hashes. Changes compare
  selected predicate symbols at the same word index; they do not grade truth,
  frame correctness or the intended meaning.
- Status distinguishes changed analyses, unchanged analyses, no usable Jev
  answers, and incomplete/inconclusive runs. An uncertain but valid answer is
  reported as a usable decision without claiming it changed the result.

## Interface and evidence

The visible comparison includes dictionary glosses and full composed formulas.
Decision details show the exact observed prefix, every choice/probability,
distribution confidence, available reported cost, latency, cache status and
provider errors. Probabilities are model preferences rather than calibrated
linguistic correctness. **Watch this revision** navigates the recorded DS
backtrack, preserving the original contribution. The main tree is the Jev run.

Regression coverage is in `tests/test_jev_comparison.py`. Live checks are
`scripts/check_jev_comparison.py` and `scripts/check_jev_comparison_browser.py`.
They read an existing local credential without storing it in artifacts. The
browser check verifies BYOK, both native backends, request settings, actual
comparison data, probabilities, revision navigation, JSON export, mobile layout
and dictionary-only operation. No new runtime model calls occur simply from
opening the demo panel or preparing an example without a connection.

Greek sense selection, TTR candidate compilers, paragraph/dialogue comparisons,
matched-budget speed experiments and held-out semantic-quality evaluation are
future work. Existing frozen lexical/frame benchmarks are unchanged.
