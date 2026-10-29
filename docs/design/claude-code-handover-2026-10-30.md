# Claude Code handover · 30 October 2026

## Start here

Repository: `https://github.com/StergiosCha/DS_workbench`.
Working branch: **`codex/hybrid-syntax-research`**.
Existing local checkout: `/Users/graogro/Dropbox/DS_workbench`.

The user asked to wrap up, commit, push this branch and hand the work to Claude
Code. The last implementation milestone is complete. The next development
milestone is **integrating the literature-based test battery** described below.
This handover does not claim that integration or new human data collection has
already happened.

Read these in order:

1. [Modular experiment architecture and reproduction](modular-experiments.md).
2. [Literature-based test battery](literature-test-battery.md).
3. [Machine-readable source selection](../../data/experiments/literature-selection-v1.json).
4. [Original hybrid lab and article reanalysis](hybrid-syntax-implementation.md).
5. [Implementation log](hybrid-implementation-log.md).

Key commits preceding this handover:

| Commit | Delivered work |
| --- | --- |
| `c285928` | Hybrid syntax lab, formal kernels, article reanalysis, assistance |
| `06b8559` | Neutral experiment host, independent CCG, memory/measurement swaps, synthetic pilot and rehearsal |
| `067288f` | Verified literature selection, source versions and availability notes |

`workbench-main` was `7f5d617` at handover. No main-branch merge, package
publication or public-site deployment is part of this handoff. A separate
deployment checkout exists; ordinary research edits belong in this repository.

## Scientific intent

The user wants a composable linguistics/cognitive-science laboratory: compare
specified grammar, processing, memory and interpretation configurations, along
with their reference versions and ablations. DS must not become a mandatory
internal representation for all engines.

Theoretical traditions are not interchangeable implementations. A useful hybrid
needs stated input/output contracts and observable predictions. Do not equate
the Minimalist Program with one fully specified formalism, or the small feature
kernel with a complete HPSG implementation. Keep distinctions between grammatical
coverage, formal equivalence, processing adequacy and human evidence explicit.

The workbench extends the inherited DyLan/dynamicsyntax codebase. Preserve
attribution and existing licence notices; do not describe the entire inherited
engine as newly authored code.

## What works now

| Area | Implementation / entry point |
| --- | --- |
| Ordinary workbench | `/`, English/Greek native parsing and existing teaching/research tools |
| Formal analysis lab | `/hybrid.html`; DS traces, typed feature constraints, LFG projections, Greek polydefinites, bounded CCG/MG, Jev/LLM assistance |
| Configuration lab | `/experiments.html`; up to four configurations, per-word native state inspection, memory/measurement swaps and JSON downloads |
| Local rehearsal | `/experiment-task.html`; counterbalanced authored items, local RT/choice export, interruption flags |
| Neutral host | `src/dylan/experiments/`: observation/analysis contract, registry, session, memory and measurement |
| Independent engines | `ds_engine.py` wraps the preserved DS adapter; `ccg_engine.py` maintains its own incremental chart |
| Study/evaluation | `study.py`, `evaluation.py`: coverage intersection, participant holdouts, crossed random intercepts, synthetic recovery |
| Response import | `responses.py`: validates study hash, schedule identity, consecutive prefix, timings, flags and provenance |
| Literature inventory | `data/experiments/literature-selection-v1.json`; source selection only, not an installed benchmark |

The selected grammar packages couple grammar, processing and semantics where
their interfaces require it. Memory, cue projection and response measurement
are independently selectable. Current memory predicts responses from analyses;
it does not alter grammar licensing or search order.

The CCG engine runs without importing a DS parser. `dylan` still exposes the
historical TTR type at package import; parser facade exports are lazy. Tests
guard against reintroducing circular imports or eager parser loading.

The HPSG-inspired feature machinery, LFG projections, construction extension and
MG fragment are in `src/dylan/hybrid/`. They have not all become independent
engines in the new host. Do not add a dropdown label that suggests otherwise.

## Evidence and limitations to preserve

**Original article reanalysis:** Nielsen & Christiansen's four studies yield
497 participants and 26,962 retained pairs. The original preprocessing counts
match. Posterior contrasts were recomputed from archived draws, not refitted.
The native DS vocabulary recognizes only 10/1,021 strings and zero complete
families; the dictionary-assisted audit recognizes 171 strings and two complete
families containing 233 trials. Rank/coverage limits prevent an architectural
conclusion from those DS comparisons. Details and aggregates are in `data/hybrid`.

**Synthetic design pilot:** 24 authored families, 18 configurations, 36 simulated
participants per dataset, three generators and three seeds. All three study
engines support all families; the legacy CCG lexicon supports zero complete
families. Exact generating-configuration recovery is **1/9**. One shared
shifted/no-memory fit is non-converged. All three grammar variants with no
memory have identical design matrices within each measurement choice.
This is weak model identification on synthetic data, not evidence for a winning
linguistic theory. The authored items confound boundary/POS/length, are all
intended positive, and still need independent review/negative controls.

**Measurement:** interactive RT coefficients are illustrative. Fitted comparisons
use training-only standardization and a transformation Jacobian when comparing
lognormal and shifted-lognormal densities. Non-converged scores remain diagnostic.
Bootstrap intervals resample fixed held-out predictions without refitting.

**Cue projection:** DS uses selected-path continuation action-template 2/3-grams;
CCG uses rule/category tuples from retained full-span analyses, including supplied
context. Those projections differ in granularity/context/ambiguity handling.
They are not a shared syntactic ontology or a pure intervention on grammar alone.

**Bounds:** observations currently allow `fragment` or `sentence`, with at most
40 words including context; CCG is additionally bounded to 12 words and 256 signs
per cell. HTTP runs have a 45-second worker limit, 16 KiB requests, at most four
configurations and two fillers. Naturalistic texts/discourse benchmarks require
an explicit extension, not silent truncation.

## Next milestone: literature ingestion and diagnostic evaluation

The selection has been checked against actual source files:

- **SyntaxGym / Hu et al. (2020):** 10 suites, 253 within-suite item sets and
  956 condition sentences. Related suites reuse lexical material, so 253 is
  not the number of independent lexical families. Each manifest entry pins the
  upstream revision, SHA-256, region metadata and original prediction formulas.
- **FraCaS/MultiFraCaS:** original English test-suite PDF and the current
  website-linked Greek XML are cached locally. The Greek file has 346 records.
  Some original problems are ill-defined/degenerate; define the scored denominator
  explicitly. Inference outcomes are entailment/contradiction/unknown, not RTs.
- **Priming/adaptation:** retain the article replication; Fine et al. (2013)
  Appendix S2 supplies Experiment 2 stimuli, fillers and presentation order.
  Fine's raw participant responses have not been verified.
- **Discourse:** Davis & van Schijndel (2020) provides given/new, referential and
  temporal context manipulations. Repository outputs are model outputs, not
  participant reading times.
- **Natural Stories:** use the corrected revision recorded in the manifest,
  incorporating the 2025-05-12 alignment fix and earlier corrections. Documentation
  and file listing were checked; the large human RT table was not downloaded in
  the literature search.
- **Dialogue:** the Purver/Cann/Kempson citation is a motivation for corpus-based
  split-utterance/repair tests. A ready-made normed test set/full text was not
  obtained; this still requires curation.

Suggested first implementation sequence:

1. Add source importers that verify the pinned hashes, preserve upstream IDs,
   conditions, critical regions, empty gap regions, punctuation and exposure
   history, and keep raw licensed materials in local caches. Do not rewrite the
   frozen synthetic pilot as if it had always used these published items.
2. Introduce appropriate task contracts/adapters for regional predictions and
   inference. The existing response importer is specific to the authored
   rehearsal protocol; it is not a generic importer for these datasets.
3. Audit each engine on complete condition families. Keep unknown vocabulary,
   bounded search and missing mechanisms distinct from grammatical rejection.
   Retain benchmark scope independently of what the current small grammars parse.
4. Build a diagnostic subset/development split and then extend the grammar and
   interpretation machinery from explicit analyses. Group shared lexical material
   across related suites when splitting; reserve genuinely held-out families.
5. Define the observable measure before reporting results. SyntaxGym's regional
   surprisal formulas require normalized predictive probabilities; chart counts
   and arbitrary cue activations are not substitutes. Human RT needs a declared,
   calibrated response model. Semantic inference needs a real interpretation/
   inference implementation. Publish separate outcomes, not one blended score.

The manifest quarantines `fgd_hierarchy`: the pinned JSON has `<` and `=`
predictions on the same region-6 subject-gap contrast. Resolve its intended
criterion against the paper before adopting it; do not silently fix source data.

Do not claim these literature tests are already runnable just because their
metadata is committed. Do not claim a human study has been conducted.

## Local setup and verification

```sh
git switch codex/hybrid-syntax-research
uv sync --locked --python 3.12 --extra research --group dev
.venv/bin/ds-workbench --port 8770
```

Open `http://127.0.0.1:8770/experiments.html`. If that port is already in use,
reuse a verified workbench instance or select another port; do not kill an
unidentified process. The existing Claude Code binary is `/usr/local/bin/claude`.

Historical verification on the final implementation (2026-10-29):

- Full suite: **2,236 passed, five existing skips, one existing collection warning**.
- Both browser harnesses passed, including all nine hybrid examples, new
  configuration comparison, mobile layout, API validation and rehearsal export.
- Installed wheel tested outside the checkout: CCG without DS parser imports,
  native English DS, Greek polydefinites, packaged UI/evidence and matching source
  hashes. Raw responses and credentials are absent from the wheel.
- Final pilot source hashes were rechecked during this handover and still match.

Fresh handover verification on 2026-10-30: **165 experiment/hybrid tests passed**
in 7.44 seconds. The handover changes documentation only; no new live model call
or full-suite rerun is claimed.

Useful commands:

```sh
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/pytest -q tests/test_experiment* tests/test_hybrid*
.venv/bin/ruff check src/dylan/experiments tests/test_experiment*
python scripts/check_experiment_browser.py --url http://127.0.0.1:8770
python scripts/check_hybrid_browser.py --url http://127.0.0.1:8770
```

The browser scripts require Playwright/Chromium. On this machine they previously
ran with `/Users/graogro/anaconda3/bin/python`; the `.venv` is Python 3.12.8.
The research snapshot used NumPy 2.4.4 and SciPy 1.17.1. Run a full regression
again when parser/grammar/import changes justify it, rather than assuming the
historical result covers new code.

`data/experiments/references-v1.json` freezes five native DS traces and hashes
of the earlier trace/combinator/feature/construction sources. Changes to those
references require an explicit versioning decision, not casually replacing
expected hashes to make tests pass.

## Local resources, AI providers and unrelated work

The ignored local `.env` exists. Jev reuses the existing OpenRouter configuration;
`OPENROUTER_API_KEY` / `TYPESAFE_API_KEY` are the relevant supported credential
names. The hybrid lab also has a configured LLM drafting provider. See
`src/dylan/hybrid/assistance.py` and its implementation guide. Live checks
previously succeeded; this handover does not claim a new live-provider check.
Use existing configuration without displaying credentials or copying them into
tracked files. A fresh clone needs its own local configuration for live models;
offline symbolic experiments do not require model keys.

Raw sources, detailed traces, simulations, model fits, literature downloads,
rehearsal exports, screenshots and built/installed test wheels are under ignored
`build/hybrid/` and `build/experiments/`. They are present in this Dropbox
checkout but are not transferred by Git. Reproduction commands are in the
linked guides; the literature manifest preserves external sources and versions.

The following pre-existing untracked work belongs to the user and has deliberately
not been added, changed or removed during the research implementation/handover:

```text
docs/paper/
docs/reports/
scripts/arash_walkthrough_cases.py
scripts/build_arash_meeting_report.py
scripts/build_arash_walkthrough.py
scripts/check_arash_walkthrough_examples.py
```

Keep it intact. Check `git status` before staging and use explicit file paths.
Do not treat those files as disposable generated output or include them in an
unrelated commit.
