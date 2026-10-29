# Configuration pilot snapshot

These files belong to the authored **synthetic** pilot dated 2026-10-29.
They contain no newly collected human responses and are separate from
`data/hybrid`, which documents the earlier source-article reanalysis.

- `references-v1.json`: preserved implementation hashes and five DS trace fixtures.
- `study-v1.json`: complete versioned items, counterbalancing, scope and model choices.
- `pilot-report.json`: frozen protocol/source hashes, coverage, 18-model held-out
  comparison, fit diagnostics and nine recovery results.

All three study engines support 24/24 families. The older CCG lexicon supports
0/24 complete families. Across nine synthetic datasets, the exact generator is
best only once; small score gaps and identical no-memory design matrices expose
weak identification in this stimulus set. One shifted/no-memory fit reports
non-convergence; diagnostic scores remain visible and are excluded from
recovery winners. This is not a claim about which theory explains human language.

Items confound prime boundary, POS and length and currently contain no intended
negative controls. The browser task is a local rehearsal. See the
[design and reproduction guide](../../docs/design/modular-experiments.md) before
interpreting or extending the experiment.

Full per-seed reports and raw synthetic responses are reproducible under ignored
`build/experiments/pilot`. The aggregate includes their canonical JSON hashes.
This snapshot was computed with Python 3.12.8, NumPy 2.4.4 and SciPy 1.17.1.
