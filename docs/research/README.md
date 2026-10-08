# DS theory-to-implementation research

- [DS Research Library](library/index.html): searchable offline bibliography,
  53 selected works, separate discovery screening, eight source-to-implementation
  cards, and BibTeX/CSL exports. See the
  [classification and contribution guide](library/README.md) and the
  [7 October expansion report](ds-library-expansion-2026-10-07.md), which records
  the search services used, access failures, admissions, corrections and the
  reading queue.
- [Research report](ds-theoretical-coverage.md), [PDF](ds-theoretical-coverage.pdf),
  and [standalone LaTeX](ds-theoretical-coverage.tex).
- [Machine-readable catalogue](ds-theoretical-coverage.json): eighteen
  categories and ninety-one tracked topics. These include open questions and
  secondary leads, not ninety-one verified construction analyses.
- [Source artifact fingerprints](ds-source-artifacts.json): thirteen inspected
  PDF versions, with SHA-256, size, physical page count and retrieval location.
  The fourteenth bibliography entry is metadata only. Full source texts are
  not redistributed here.
- [First implementation](../design/nonrestrictive-relatives.md): native
  English Classical/Constructive nonrestrictive relatives with named heads.

Build from the repository root:

```sh
python3 scripts/build_ds_research_report.py
```

Requires Pandoc and XeLaTeX; shares the technical report renderer. The output
TeX is standalone. It can subsequently be compiled with XeLaTeX without
Python or the repository. Build logs are in the system temporary directory's
`ds-theoretical-coverage-latex` folder.

To run the first construction's semantic checks:

```sh
.venv/bin/python -m pytest -q tests/test_nonrestrictive_relatives.py
```

Coq export checks run when `coqc` is installed. Browser checks, including
JSON export and displayed meaning, use:

```sh
/path/to/python-with-playwright scripts/check_nonrestrictive_browser.py --url http://127.0.0.1:8797
```

The review is dated 6–7 October 2026. Add precise source passages and evidence
status when extending it; do not promote an unreviewed pointer or a successful
parse into an empirical coverage claim.
