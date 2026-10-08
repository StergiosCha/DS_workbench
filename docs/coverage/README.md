# Reproducing coverage

Run from the repository root with the project environment:

```sh
uv run python scripts/corpus_run.py --all --in-process
uv run python scripts/coverage_report.py --check
uv run python scripts/grammar_lint.py --all --results build/coverage/greek-clitics-top3.jsonl build/coverage/english-top3.jsonl --json build/coverage/grammar-lint.json
uv run python scripts/sync_grammars.py
uv run python scripts/scale_probe.py
```

The default corpus runner isolates each parse in a subprocess with a 30-second timeout. `--in-process` uses a per-row alarm and resets meta bindings; it is faster for local regression runs. Both paths use the real workbench parser with lexical expansion off. `--top-n 0` retains every lexical entry. Reports carry parser counters, failure kinds, cap names, semantic strings, Coq results and the actual lexical templates on successful paths.

`coverage.lock` files contain per-grammar/per-phenomenon floors. Vocabulary, construction agreement, semantic checks and overgeneration are separate. Unknown source judgments never enter rates; missing vocabulary never earns a successful rejection; a cap or timeout is inconclusive. Semantic credit requires supplied expected substrings and, for constructive results, a successful `coqc` check. No semantic expectation means unmeasured, rather than automatically correct. The compiler checks the exported type, not truth or inhabitation.

Greek sources include adapted CASES pairs in both scripts, diagnostic fixtures, explicit starred prose, literal manuscript glosses and thesis examples. Each row includes a locator and the transcription's raw source excerpt where applicable. PDF page numbers are physical PDF pages, starting at 1. `transcription_queue.jsonl` retains ambiguous or multiline source blocks. No human review is claimed: `human_labels` remains null until an actual annotator reviews the row. Chapter context supplies a provisional variety where an example does not name one explicitly; such rows require source review before promotion into a grammar's acceptance tests. Abstract pattern names and bare-cluster shorthand are not manufactured into full sentences.

The English set contains native fixtures, the historical TTR and robot probe strings, and 100 BabyDS GoldSent utterances. A historical parser acceptance/failure report is not a linguistic judgment; those rows remain `not_stated` unless an independent source establishes otherwise.

At the first M0 measurement, all runs agreed on `ok`/`complete` at top_n 0 and 3, and no starred row completed. The robot probes `take it` and `take the ball and drop it` hit the mandatory-rule limit. Their older "accepted" descriptions are superseded by the explicit inconclusive results. No grammar has been expanded in M0.

To rebuild the source data:

```sh
uv run python scripts/build_clitic_corpus.py --pdf /path/to/chatzikyriakidis-phdthesis.pdf --manuscript /path/to/benjaminsvolume.tex
uv run python scripts/build_english_corpus.py
```

`--write-lock` is for reviewed baseline changes; it refuses overgeneration and execution errors. `--check` also rejects results that do not match the current corpus IDs and grammar mappings. CI installs Coq, runs the corpus regression tests and independently runs the coverage commands.
