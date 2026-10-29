# Hybrid syntax research branch

Implemented on `codex/hybrid-syntax-research`, starting from plan commit `5b919a3`. The local experiment page is `/hybrid.html`. These are executable, bounded fragments with declared interfaces, not complete implementations of the named linguistic frameworks.

The [evidence snapshot](../../data/hybrid/README.md) reports the actual reanalysis. The [original plan](hybrid-syntax-research-plan.md) records the larger agenda. This document distinguishes delivered machinery from claims requiring further theory, annotation or experiments.

## Run and inspect

```sh
uv sync --locked --python 3.12
.venv/bin/ds-workbench --port 8769
```

Open <http://127.0.0.1:8769/hybrid.html>. The ordinary workbench links to it. The experimental API runs in the local loopback server; it has not been added to the public ASGI deployment. The page requires no statistical dependencies, credential or raw data download. Aggregate evidence is bundled.

| Example | Observable result |
|---|---|
| `John likes` | An open DS object requirement; LFG completeness remains pending before closure. |
| `John likes Mary` | Object completion and an explicit DS-address → f-node mapping. Earlier word buttons show earlier LFG projections. |
| `likes a`, left context `John` | A fragment recognized with unfilled rightward requirements. |
| `ο άνθρωπος ο μεγάλος περπατάει` | Repeated D and a postnominal adjective refine one definite referent. |
| `ο μεγάλος ο κόκκινος ο άνθρωπος περπατάει` | Prenominal repeated D, intersective modification and inherited agreement constraints. |
| `ο άνθρωπος η μεγάλη περπατάει` | Agreement failure in the declared analysis. |
| `will make his` in CCG | Composition yields unfinished `(S\NP)/N`. |
| `who did john like` in MG | `+wh/-wh` licensing, Merge/Move history and a lower-copy variable. |

`hybrid` selects DS plus partial LFG projection and, for Classical Greek, the opt-in polydefinite extension. `compare` runs native DS, CCG and MG side by side. The comparison does not align all lexical meaning symbols or establish equivalence.

## Formal commitments

The interface distinguishes states (Q_g), initial states (I_g), token/epsilon transitions \(\delta_g\subseteq Q_g\times(W\cup\{\epsilon\})\times Q_g\), completion (C_g), and interpretation (J_g). This is an interface specification; the implemented rules, lexicons and bounds supply its content.

### DS and memory

`traces.py` exposes the existing pointed tree, labels, context and search DAG. Initial states and epsilon actions come from the selected native resource grammar. Transitions execute its lexical programs with native preconditions/backtracking. Completion uses the native tree predicate after explicit completion steps; Classical formula labels supply interpretations.

The adapter retains all lexical candidates (`top_n=0`), disables repair, and bounds adjustment/completion at 1000. It records the first successful path, not an exhaustive forest. Fragment recognition, pending completion, unknown lexicon, unsupported construction and search limits are distinct outcomes. Each step records before/after states, actual programs/hashes, candidates, selected actions, atomic replay, pending labels and counters. Replay compares resources, observed states and candidate programs, including dictionary expansions. Optional LFG projections do not add DS actions.

The deterministic macro utility contains word-gated groups of partial action maps. On observed (w_i), it composes the corresponding actions on a cloned tree and context. Failed preconditions restore meta bindings and leave its index unchanged; the caller adopts the returned `MacroStep(tree, context)` on success. It never observes future words early. It does not learn macros or claim equivalence for branching action relations.

External sequence memory is reset independently of parse state. Immediately before trial (t):

\[
A_t(s)=\sum_{j<t:\ s\in O_j}\rho^{t-j-1},\quad \rho=0.8.
\]

Queries precede updates. Separate lexical/POS/tree/DS memories use actual histories, including fillers. RT regression consumes `log1p` activation; parser runtime is not interpreted as human RT.

### Feature constraints and constructions

`features.py` implements finite graphs (G=(V,r,\tau,F,a)), with partial feature function (F:V\times\mathcal F\rightharpoonup V) and optional atomic values (a). A finite subtype hierarchy supplies unique meets; appropriateness constrains feature/value sorts. Descriptions may omit appropriate features. Unification identifies roots, propagates sharing, meets types and refines appropriateness. It supports finite cycles, rejects conflicts and modifies neither input.

Construction inheritance is monotonic conjunction of own and inherited graph constraints. There are no silent overrides or defeasible defaults. The Greek construction inherits `nominal → singular-subject → polydefinite`. General `meaning` fields are annotations; the Greek construction's executable form conditions and semantics live in `PolyEffect`. The same feature kernel licenses repeated-article agreement inside the DS lexical effect, while the inspection graph records one nominal referential index. This coordination does not turn DS into an HPSG sign grammar.

### LFG

`lfg.py` uses a finite graph with primitive functions and `Predicate(name, arguments)`. At closure, completeness requires each governed argument; before closure missing arguments remain pending. Coherence rejects ungoverned governable functions. Dangling references and conflicting TOPIC assignments are errors. Functional uncertainty enumerates `(COMP|XCOMP)* OBJ` under an explicit depth bound; TOPIC shares its target node. Truncation differs from absence of a matching path.

`correspondence.py` maps declared native predicate argument positions to f-nodes: for the supported transitive layout, `00 → SUBJ`, `010 → OBJ`. It requires one declared predicate, otherwise returning `unsupported_projection`. It is not a general method for deriving primitive grammatical functions from meanings. Complex clauses and undeclared dictionary predicate symbols need additional mappings.

The `give` mapping additionally checks the active lexical frame: the declared double-object configuration maps recipient to OBJ and theme to OBJ2; `dative-to` maps theme to OBJ and recipient to OBL. These function assignments are explicit analysis choices and are tested separately.

### Minimalist Grammar

`minimalist.py` defines a finite Stabler-style fragment, not the Minimalist Program as a whole. An expression has a yield, ordered features, a lambda term, pending movers and distinct lexical occurrence identities. External Merge matches leading `=x`/`x` on disjoint occurrences. A lexical selector takes a right complement; subsequent selectors take left specifiers. Selected expressions retaining licensees are stored as movers and leave fresh lower-copy variables. Other residual features fail.

Move requires active `+f` and one matching `-f` mover. Competing leading licensees violate the declared Shortest Move restriction. Intermediate movement checks a feature without another pronounced copy. Final movement fronts the mover and applies its operator meaning to an abstraction over the lower-copy variable. Substitution avoids capture.

Null `=v c` and `=v0 =d c` lexical entries supply the declared declarative/intransitive structures; they are explicit choices, not inferred universal heads. The parser bounds numerations to eight overt words and search to 10,000 expressions. Finals require category `c`, no movers and the observed yield. Phases, cartography, economy and nanosyntactic spellout are not silently assumed.

### CCG

`ccg.py` defines atomic/slash categories, forward/backward application and harmonic composition. Optional NP raising is `NP → T/(T\NP)`, interpreted as `λf.f(x)`. Conjunction entries are instantiated for NP, N, S and VP. The chart returns unfinished as well as sentence categories, under 12-word/256-per-cell bounds. The lambda library uses capture-avoiding substitution and bounded normal-order reduction; it is not a general semantic type checker.

These combinators and MG Merge have different licensing, intermediate states and linearization. Shared examples do not prove string, structural, semantic or incremental equivalence. No such theorem is claimed here.

## Greek analysis and source limits

Kolliakou (2004), *Monadic definites and polydefinites: their form, meaning and use*, Journal of Linguistics 40(2), 263–323, [DOI](https://doi.org/10.1017/S0022226704002531), motivates definite concord, one semantic contribution of definiteness, and contextual restrictions. The accessible abstract describes an HPSG phrasal-affix analysis and contextual anchoring. The attempted PDF download returned an HTML access page; this work does not claim to reproduce the full analysis.

Our Classical hypothesis refines one restrictor: \(\iota x[P(x)]\leadsto\iota x[P(x)\land A(x)]\). Every article is consumed. Prenominal repetition opens a content requirement; postnominal repetition opens an adjective requirement on the existing CN, whose refinement recomposes the same DP. Agreement, missing content, indefinite doubling and repetition after a finite predicate are tested. Coverage is singular nominative masculine/feminine/neuter with declared big/red modifiers in a subject fragment.

Contextual identifiability is assumed, not inferred. Prosody, contrast, ellipsis, nonintersective adjectives, other cases, object polydefinites and general adjective ordering are outside the fragment. Iota semantics is our backend choice, not attributed as Kolliakou's exact analysis.

## Reproduce the pipeline

```sh
uv sync --locked --python 3.12 --extra research
.venv/bin/python -m dylan.hybrid.sources --raw --fits
.venv/bin/python -m dylan.hybrid.dataset
Rscript scripts/hybrid_reproduce.R
mkdir -p build/hybrid/downloads
curl -fL https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/r2.15/en_ewt-ud-train.conllu -o build/hybrid/downloads/en_ewt-ud-train.conllu
.venv/bin/python -m dylan.hybrid.contexts build/hybrid/downloads/en_ewt-ud-train.conllu
.venv/bin/python -m dylan.hybrid.coverage --output build/hybrid/audit
.venv/bin/python -m dylan.hybrid.coverage --vocabulary dictionary --output build/hybrid/audit-dictionary
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m dylan.hybrid.comparison --audit build/hybrid/audit-dictionary --output build/hybrid/comparison-final
.venv/bin/python -m dylan.hybrid.report
```

The dictionary audit needs the optional pinned WordNet 3.0 index, built with `scripts/build_wordnet_dictionary.py` from the archive declared in `dylan.lexical_dictionary`. Parsing does not download entries. R preprocessing needs `tidyverse` and `jsonlite`; saved posterior extraction needs no new `brms`/`rstan` fit. R 4.4.0 was used here.

The OSF importer checks ZIP CRCs, records SHA256/member paths/source dates, and uses HTTP ranges. Whole-archive hashes are supplied metadata, explicitly **not** verified by selective retrieval. Data are CC BY 4.0; source code MIT per upstream `license.txt`. UD EWT is CC BY-SA 4.0. Raw histories, full traces and fit outputs remain in ignored `build/hybrid/`. Committed evidence contains aggregate results, a few attributed stimuli and hashes.

Python reconstructs raw order, exclusions and Study 4's shortened displayed forms. Original R preprocessing matches all four archived processed datasets. Posterior contrasts use saved draws and `ndt + exp(cell_coefficient + sigma²/2)` at zero random effects; they are not fresh fits.

The context bank has 24 deterministic corpus-order prefixes, selected without priming outcomes, under a uniform finite-bank prior and open rightward requirements. The audit reports support fractions. Features currently union over contexts; they do not marginalize a fitted natural-context distribution.

The new outcome model is marginal-ML Gaussian log RT with crossed participant/item intercepts, distinct from the authors' Bayesian shifted-lognormal model. Standardization is train-only. Fixed three-fold lexical-family components block shared displayed strings; participant and target-POS components define separate regimes. Accuracy uses a separate regularized fixed-effects logistic companion.

M0 contains lexical frequency/repetition/recency, length, semantic similarity, order, study and constituent-condition controls. M1 adds POS bigram/trigram overlap/recency and independent EWT frequencies. M2 adds completed and unfinished bounded POS-CFG fragments. M3 adds DS action/state projections; M4 combines POS and DS. Template and pending-label projections are lossy, not action-equivalence classes. Unsupported histories contribute no DS features.

The reanalysis is exploratory, not preregistered. A protocol is saved before fitting, but no independent practical-gain threshold was fixed for this completed run. It does not select a winning architecture. Primary M1/M2 intervals span zero. The DS subset has two families, 233 observations, rank-deficient fixed effects and one observation per participant. Participant/residual variance is not separately identifiable; tiny score differences there carry no theoretical conclusion. Bootstrap intervals resample held-out groups with fitted models fixed, not refitted.

## Model support

`assistance.py` reuses validated lexical proposals and the TypeSafe/Jev Choice client. Drafts return reviewable programs/declarations with `installed=False`. Jev receives explicit candidates, the observed prefix, coverage status and available DS state. Sense/frame questions include uncertainty; all alternatives and original order remain recorded. Unsupported prefixes are labelled as such.

Use the ordinary OpenRouter credential: `OPENROUTER_API_KEY` and `DS_DECISION_PROVIDER=openrouter` in ignored `.env`. Direct TypeSafe is also supported. LLM configuration reuses existing Azure/OpenRouter settings. Never put keys in URLs or committed files.

```sh
.venv/bin/python -m dylan.hybrid.assistance rank --prefix 'John reads the' --word novel --live --output build/hybrid/assistance/live-jev-supported-prefix.json
.venv/bin/python -m dylan.hybrid.assistance draft --prefix 'The lamp' --word glimmers --model DeepSeek-V4-Flash --live --output build/hybrid/assistance/live-llm.json
.venv/bin/python scripts/check_jev_comparison.py --output build/hybrid/assistance/live-parser-comparison.json
```

The named deployment is local configuration, not a portable default. Ranking without `--live` produces a labelled stub. Live Jev checks and an Azure LLM draft succeeded. These establish connectivity and interface preservation, not calibration or linguistic correctness. Existing decision logs retain state, inventory, model, answers, latency, tokens and optional provider-reported cost; missing cost is not measured zero.

The existing lexical benchmark and with/without-Jev parser comparison remain available. The new adapter does not overturn prior negative search-calibration results. A new ordinary/count/Jev comparison on independently annotated hybrid constructions remains prospective; count ordering must train only on training observations. No newly claimed performance benefit is deployed.

The live parser check used `John lends a book to Mary` under Classical and Constructive semantics. Both with/without-Jev runs completed using the same 15 candidate programs; Jev selected the temporary-giving sense instead of the quality-bestowing sense in both backends. This is one prepared example, not a held-out accuracy estimate. The existing baseline has an extra four-second cap, recorded in the result; its timing is not a symmetric performance comparison.

## Prospective contrasts

These are **author-constructed design seeds**, not independently annotated examples or new human evidence:

| Contrast | Intended control | Independent review needed |
|---|---|---|
| `John saw the man with a telescope`, instrument vs man-description contexts | Same words/POS, different VP/NP attachment | Both readings and context naturalness. |
| `John likes Mary` / `He likes Mary`, with resolved pronoun context | Same proposed argument structure, different initial POS | Reference and discourse/lexical controls. |
| `ο μεγάλος άνθρωπος περπατάει` / `ο άνθρωπος ο μεγάλος περπατάει` | Shared referent, different article/adjacency patterns | Greek prosody and contextual distribution. |
| `who did john like` / an embedded object dependency | MG chain, LFG path sharing, DS unfixed dependency | Extend each grammar from published analyses before comparison. |

Before new data collection: obtain the full article through legitimate access, independently review stimuli and contexts, freeze family splits/tuning/practical gain/stopping criteria on separate pilot data, then register the prospective protocol. Authored fixtures do not establish equivalence. Optional head-order/phase/nanosyntactic experiments remain explicit future hypotheses; nanosyntax additionally requires lexical trees, spellout domains, matching and competition rules.

## Verification

Focused tests cover graph unification/reentrancy/cycles, inheritance, LFG closure/uncertainty, capture avoidance, MG licensing/linearization, CCG composition, Greek positive/negative controls, replay, macro rollback, source retrieval, leakage and mixed-model predictive covariance against dense Gaussian calculations. The broader run passed 2,160 tests in the sandbox; its sole failure was a blocked HTTP socket, which passed on the authorized rerun. Five existing tests were skipped. Targeted checks cover subsequent research edits.

The final focused run passed 70 tests. Macro checks include both rollback fixtures and execution of the actual native lexical/computational action group against its expanded execution.

All 49 saved DS traces belonging to the two complete matched families replayed successfully, including candidate programs and intermediate states. The wheel was built and inspected against the final source, then imported outside the checkout: English parsing, the Greek polydefinite example and packaged evidence all passed. Raw study observations and local credentials are absent from the wheel.

The browser harness runs all nine displayed examples, evidence cohort switches, stub ranking, mobile overflow and invalid/wrong-origin requests without live model calls. The API isolates execution in a 45-second subprocess. The ordinary parsing path is preserved.

```sh
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/pytest -q tests/test_hybrid*
.venv/bin/ruff check src/dylan/hybrid tests/test_hybrid* scripts/check_hybrid_browser.py src/dylan/workbench_server.py
python scripts/check_hybrid_browser.py --url http://127.0.0.1:8769
uv build --wheel --out-dir build/hybrid/package
```

Browser checks need Playwright/Chromium. Screenshots and checks are in `build/hybrid/browser/`. This is a reviewable research branch; it has not been merged into `workbench-main` or publicly deployed.

## Modular host extension · 2026-10-29

The [Configuration lab](modular-experiments.md) now runs the preserved DS
baseline and an independent incremental CCG engine through a neutral experiment
host. Memory, representation and response models are selectable components.
The new authored synthetic pilot and local task rehearsal are separate from the
article reanalysis above. They expose coverage, convergence and weak model
identification; no new human evidence has been collected.
