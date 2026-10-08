# Contributing to DS Workbench

The aim is a resource DS researchers can inspect, teach with, challenge and
extend. A contribution need not involve programming. A sourced example,
corrected interpretation, dialect judgment with context or reproducible
counterexample can define the next piece of grammar work.

## Choose a starting point

| Contribution | Starting material | Useful result |
| --- | --- | --- |
| Classroom/demo | [Using the app](docs/community/using.md), slides | Walkthrough with settings, expected meanings and known failures. |
| Linguistic evidence | [Research catalogue](docs/research/ds-theoretical-coverage.md), construction issue template | Reference/page/example, language/variety, source judgment and discourse assumptions. |
| Lexical extension | [Runnable tutorial](docs/community/extending.md) | Typed predicate/entry, semantic checks and excluded contrasts. |
| Construction family | [Design template](docs/community/construction-template.md) | Sourced DS operations, backend-specific composition, positive/negative tests. |
| Engine/interface | [Architecture](docs/workbench-walkthrough.md) | Minimal reproduction, focused fix, trace/export/API regression as appropriate. |

Use [workbench issues](https://github.com/StergiosCha/DS_workbench/issues) and
[pull requests](https://github.com/StergiosCha/DS_workbench/pulls) for these
contributions. This repository maintains the workbench extensions; upstream
DyLan and `dynamicsyntax` retain their own project governance.

## Development loop

```sh
uv sync --locked --group dev --extra hosting
uv run --no-sync python examples/community/extend_grammar.py --output /tmp/my-ds-extension
uv run --no-sync pytest -q tests/test_nonrestrictive_relatives.py
```

Choose an unused output directory; the tutorial refuses to overwrite one.
On Windows, use an appropriate writable path. Python grammar work is intended
to be portable, but full server/timeout parity on Windows is not established.

For generated native grammars, edit their builder and rerun it. Do not only
patch generated `.txt` files. The extension guide maps builders to families.
Run relevant tests first; for shared tree/search/semantics changes or a release,
also run the full suite and [corpus protocol](docs/coverage/README.md).
Coq-dependent checks require `coqc`; skipped checks are not passes.

## What review should establish

1. The construction has a source or is marked as a new implementation proposal.
   Distinguish source judgments from authored probes.
2. Tree operations are visible and requirements actually close. Check intended
   scope, argument roles and referent identities, not only completion.
3. Excluded contrasts and unsupported combinations stay visible. A search cap
   is inconclusive, not evidence of ungrammaticality.
4. Supported semantic backends are checked separately. Record missing TTR or
   Greek coverage instead of silently generalising native English results.
5. Grammar tests run without a paid model. Live assistance checks separately
   record provider/model, candidates and revisions; model preference is not gold.
6. New data has provenance and reuse terms. Do not commit keys, `.env`, personal
   histories, account configuration or downloaded source PDFs.

Use small reviewable changes. Conventional commits (`feat(grammar): ...`,
`fix(parser): ...`, `docs: ...`) are supported by the inherited tooling.
The optional local hook is `git config core.hooksPath scripts/git-hooks`.
Contribution terms must be explicit when the release's licence is settled;
no contributor licence agreement or transfer is assumed here.
