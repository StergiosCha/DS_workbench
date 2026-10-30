# LingEmbed integration · first working bridge

DS Workbench exports versioned native DS/CCG analyses to LingEmbed, where a new
`workbench.html` page replays prefixes, visualizes structures and tests explicit
encodings. No model calls, additional neural claims or public deployment are
part of this milestone.

## Running the two applications

```sh
# DS Workbench checkout
.venv/bin/ds-workbench --port 8770

# In a second terminal, from the LingEmbed checkout
python3 -m http.server 8781 --bind 127.0.0.1
```

Open `http://127.0.0.1:8770/experiments.html`, run a comparison, and use **Open in
LingEmbed** on an event. Its default viewer is
`http://127.0.0.1:8781/workbench.html`; change the address under **LingEmbed
connection** if necessary. File export/import is also available. The viewer has
three recorded examples and requires no parser server to inspect them.

Implementation branches: `codex/lingembed-bridge` in DS Workbench (based on
`codex/hybrid-syntax-research`) and `codex/workbench-bridge` in LingEmbed.
Neither production site has been deployed. LingEmbed's concurrently edited
homepage, original illustration, shared stylesheet and README were preserved.

## Design and scientific boundary

- `experiments/lingembed.py` adapts native analyses to `lingembed.analysis.v1`.
  Types, normalized meaning strings, node labels, edge roles and explicit native
  token spans are exported where supplied by the engine. No DS word alignment
  is invented. Partial/failure states keep their coverage status.
- CCG derivations are reconstructed from each actual prefix with its recorded
  lexicon/combinators; native before/after chart states are checked, and a changed
  source version is rejected. The first eight retained full-span alternatives
  are exported with omission counts. No completed tree is pruned to fabricate
  an earlier state.
- DS copies its selected native snapshots, preserving all address labels and
  pointer/requirements. Post-input completion is a separate frame, never shown
  as if it occurred after an earlier word.
- `experiments/lingembed_api.py` wraps the unchanged experiment API, adding only
  optional `export_lingembed: true` to the local `/api/experiments/run` route.
  Frozen grammar, host, memory, measurement, source hashes and synthetic pilot
  stay unchanged. The new wrapper decorates outputs after the original run.
- The browser transfer validates exact origins, opener window and a random
  channel. Manual JSON import works independently. Exports contain symbolic
  analysis information and provenance; no model credential is transferred.

The companion `LingEmbed/WORKBENCH_BRIDGE.md` specifies the complete contract,
import limits and diagnostic equations. The companion viewer separately checks
topology-only geometry and codebook-assisted recovery of typed node/edge records.
Its controlled role-overlap sweep is an illustrative binding diagnostic. It is
not a trained representation, semantic equivalence proof, memory fit or human
experiment, and does not change workbench response predictions.

LFG, feature, construction and Minimalist Grammar fragments have not been
presented as new independent parser backends. Graph/reentrancy support and
fixed-budget learned encoders require further explicit adapters and experiments.

## Reproduce

```sh
.venv/bin/python scripts/export_lingembed_examples.py --output ../LingEmbed/examples
.venv/bin/pytest -q tests/test_experiment_lingembed.py
python scripts/check_lingembed_browser.py
# In LingEmbed:
node --test tests/bridge-core.test.cjs
```

The browser harness exercises both applications, popup transfer, file import,
prefix selection, typed-record recovery, role overlap, example loading, mobile
layout, malformed inputs and literal rendering of imported text. Its screenshots
and downloaded artifacts stay under ignored `build/lingembed/browser/`.

Verification on 30 October 2026: 217 experiment/hybrid/workbench Python tests
passed, six Node diagnostic/validation tests passed, and the cross-application
Chromium harness passed on desktop and mobile. Frozen source/pilot checks passed.
This is targeted integration validation, not a claim of a new full-suite run.
