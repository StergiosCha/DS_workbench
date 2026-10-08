# Maintainer handover

## What another maintainer receives

The Python engine, generated grammar files and their builders, HTML/JS/SVG
frontend, local and ASGI servers, tests, source/evaluation data, technical
walkthrough, research catalogue and presentation slides are in this checkout.
No Azure account or shared model key is needed for core development.
The [community guide](README.md) and [extension tutorial](extending.md) are
the starting points; private development conversation history is not required.

The installed wheel now carries the interface and selected runtime evidence,
as well as grammars. `workbench_paths.py` prefers editable checkout files when
running from source; otherwise it resolves packaged assets. Workers use the
source root or launch directory for relative caches, never site-packages.
`DS_WORKBENCH_DATA` selects another data tree. Large WordNet/Brown/Gutenberg
indexes are optional external inputs, not wheel contents.

## Release questions still requiring ownership decisions

1. **Public home and responsibility.** Workbench source, issues and pull
   requests are at <https://github.com/StergiosCha/DS_workbench>, owned by
   `StergiosCha`. The initial snapshot preserves the public upstream history.
   The development checkout names `incrementaliser/DynamicSyntax` as `upstream`
   and the workbench repository as `origin`. Additional maintainers and review
   responsibilities can be agreed through this repository.
2. **Licence and contribution terms.** The old Python metadata claimed BSD
   while `LICENSE` deferred to DyLan. The actual referenced
   [DyLan licence](https://github.com/Dynamics-of-Language/DyLan/blob/ac70d021e5dc0eab24f185e5a34bbca19c0fc772/LICENSE.txt)
   is LGPLv3. The unsupported BSD label has been removed and verbatim licence
   evidence is included. Confirm terms for the port and later workbench
   contributions before a public release; do not announce a blanket BSD or
   newly assigned licence. Review/separate source-restricted research excerpts
   and GDT's CC BY-NC-SA data for the intended distribution.
3. **Versioned release and citation.** Commit the reviewed changes, create a
   prerelease with source and wheel plus checksums, and give the demo the same
   identifiable version. Set package URLs and publishing permissions for the
   actual owner. Do not publish under the upstream PyPI name without its
   maintainer's arrangement. Agree authorship/citation metadata; then add
   `CITATION.cff` and, if desired, an archival DOI. No authorship is invented here.

The inherited tag workflow must not be treated as permission to publish.
Its PyPI step now requires the `ENABLE_PYPI_PUBLISH` repository variable to be
`true`; configure it only for an authorised package/repository after the
questions above are settled. Development wheels are local validation artifacts.

## Build and verify

```sh
uv sync --locked --group dev --extra hosting
curl --fail --location https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip --output /tmp/ds-wordnet.zip
uv run --no-sync python scripts/build_wordnet_dictionary.py /tmp/ds-wordnet.zip
uv run --no-sync pytest -q
uv run --no-sync python scripts/corpus_run.py --all --in-process
uv run --no-sync python scripts/coverage_report.py --check
uv run --no-sync python scripts/sync_grammars.py
uv build
uv run --no-sync python scripts/check_release_contents.py dist
```

The full integration suite needs the optional WordNet index. Its builder
checks the archive's pinned SHA-256 before creating the local SQLite file;
CI performs these same preparation steps. The index is ignored by Git and is
not needed for the app's bundled grammar examples.

Coq must be installed for complete semantic-floor checks. Optional graphics,
TeX and live-provider tests have their own dependencies; report skips. The
source distribution includes the builders, tests, guides and examples, with
private histories/caches/account files excluded by `MANIFEST.in`. The archive
check enforces both required content and forbidden paths; it is not a licence
clearance or a general secret scanner. Inspect the artifact before release.

Install the resulting wheel with its `hosting` extra in a fresh virtual
environment. From a temporary directory, run that environment's Python:

```sh
/path/to/clean-venv/bin/python -I /path/to/source/scripts/check_installed_workbench.py
/path/to/clean-venv/bin/python -I /path/to/source/examples/community/extend_grammar.py --output /tmp/ds-extension-check
```

The `-I` flag prevents the checkout/PYTHONPATH from satisfying missing package
files. The check verifies three parser backends, installed resources, local
HTTP and streaming results for both native backends, and keeps failures visible.
The separate installed-package CI job runs this on a clean Ubuntu environment.
Local verification results are recorded in [handover-checks](handover-checks.md).

## Hosting and operational boundary

For local work use `ds-workbench`. For a host with the hosting extra installed:

```sh
uvicorn dylan.workbench_asgi:app --host 0.0.0.0 --port 8000
```

Put public TLS/routing and deployment limits in the hosting layer. The app
already bounds parse bodies, subprocess time and concurrent requests. Keep
request-scoped user keys and worker isolation. Do not load a maintainer's
`.env` into a public service or make a server key the public demo's billing
source. See [Vercel deployment](../design/vercel-deployment.md) for the existing
staging manifest and deployment procedure. A wheel install works without Vercel.

The code has mutable meta state; separate worker processes are deliberate.
Do not replace them with concurrent in-process parser calls as a casual
optimisation. The current full serving path is tested on macOS and uses
Unix-oriented pipe/timeout behaviour; Windows serving needs its own audit.

## A manageable next development cycle

Use the theory catalogue to propose one bounded family, have its source and
semantic assumptions reviewed, add deterministic positive/negative/meaning
fixtures, implement it, and measure interactions with existing coverage.
Useful independent work includes TTR identity/composition audits, Greek
nominal/PP coverage, broader held-out evaluation and classroom exercises.
Track linguistic correctness, operational correctness and AI preference quality
separately. Keep a changelog by construction/backend, with reproducible examples
and acknowledged limitations, so another maintainer can continue the work.
