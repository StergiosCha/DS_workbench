# Modular linguistic experiments

Implemented on `codex/hybrid-syntax-research`, 2026-10-29. The Configuration lab
at `/experiments.html` compares independently selected engines under a shared
observation/task protocol. The existing `/hybrid.html` remains the place to
inspect feature constraints, LFG projections, constructions, MG derivations and
Jev/LLM assistance. Nothing here has been deployed to the public workbench.

## What is implemented

| Component | Available implementations | Boundary |
| --- | --- | --- |
| Grammar, processing, semantics | Native English DS; native Greek DS; Greek DS with the typed polydefinite construction; original CCG fragment; expanded incremental CCG; application-only CCG ablation | Coupled packages with explicit lexical and semantic assumptions |
| Representation for memory | Native cues; lexical bigrams; their union | A lossy, declared measurement projection, not a common syntactic ontology |
| Memory | None; cumulative counts; exponential recency | Queries precede updates; state resets per participant/session |
| Response measurement | Lognormal; lognormal with a fixed 150 ms shift | Interactive coefficients are illustrative; study comparisons fit coefficients on training observations |
| Experiment host | Shared observations, counterbalanced schedules, coverage intersection, trace export, response import, held-out comparison | It does not require a DS tree or call DS for CCG analyses |

These are executable **implementation fragments**. The registry does not claim
to provide full implementations of CCG, HPSG, LFG, Construction Grammar or the
Minimalist Program. In particular, the earlier feature unifier is HPSG-inspired
machinery; LFG remains an explicit projection/constraint fragment; the MG
fragment uses a particular formalization of Merge/Move. None has been silently
promoted into a full interchangeable parser.

DS has no mandatory role in the host. Choosing CCG imports no DS parser; a
fresh-process test also registers and executes a third opaque test engine.
The distribution still exposes its historical TTR data type at package import.
Parser facade exports load lazily, avoiding unnecessary DS initialization and
old circular imports. Exported classes and parser operations are unchanged.

## Formal interface and the limits of interchangeability

An observation is `(left_context, text, task)`, where task is `fragment` or
`sentence`. A grammar engine supplies:

```python
analyse(observation: Observation, *, trace: bool = True) -> Analysis
close() -> None
```

`Analysis` records the engine identifier, support status, native completion,
meanings, optional prefix states, counters, cue identities and provenance.
Internal states remain opaque to the host. A DS requirement-bearing semantic
tree and a CCG chart are not identified by placing them in the same record.

The Python registry accepts a trusted `register_grammar(id, specification,
factory)` extension. The specification declares family, language, role,
processing, semantics, reference and maximum words. A factory accepts the
identifier and returns an engine implementing the two methods above. Web
requests select registered identifiers; they cannot name arbitrary imports.
Adapters for additional formalisms can therefore be implemented independently.

Grammar/processing/semantics stay coupled in these packages. A DS lexical
action program cannot simply consume a CCG chart; a typed feature constraint
cannot assume that every engine state contains an HPSG sign. Deeper hybrids
need a concrete transformation with stated input/output types, preserved
information, failures and tests. Existing polydefinite and LFG interfaces are
examples of bounded implementations of such transformations.

The current memory component predicts responses from analyses; it does **not**
change grammar licensing or reorder parsing search. That is a distinct,
potential future intervention requiring an engine-specific interface.

## Memory and measurement

Let `C_t` be the deduplicated cue set for event `t`. Immediately before that
event, exponential memory has strength

`m_t(c) = sum_{j<t} rho^(t-j-1) * 1[c in C_j]`, with `0 < rho <= 1`.

Counts use `rho = 1`; the no-adaptation model returns zero. Activation is the
mean of `log(1 + m_t(c))` over `C_t`, or zero for a supported empty cue set.
Prediction happens before storing the current observation. Unsupported native
analyses produce unavailable activation and still advance the event clock.
Lexical controls may be computed for unsupported strings, while grammar
coverage remains explicitly false.

The interactive models use `RT = shift + exp(mu + epsilon)`, with
`mu = log(.8) - .12 * activation`, `epsilon ~ Normal(0, .25^2)`, and shift either
zero or `.15` seconds. These coefficients demonstrate that a component swap
changes an output; they are **not estimated human processing parameters**.

DS uses selected-path lexical action-template bigrams/trigrams from the displayed
continuation. CCG uses the union of rule/result/child-category tuples in retained
full-span derivations, including the supplied context. These projections have
different granularity and ambiguity policies. Thus a grammar-package comparison
also compares its declared representation/processing choices. It is not a pure
intervention on grammar theory alone. Lexical bigrams provide a shared control.

CCG appends one observed word and constructs only chart cells with the new right
boundary. Existing prefix cells are retained. It allows harmonic composition
and lexical NP type raising in the expanded configuration; the ablation removes
both. `will make his` supplies a concrete licensing difference. The maximum is
12 words and 256 signs per cell; reaching the bound is reported as a search
limit. Deduplication retains one derivation per category/meaning pair, not all
derivational histories. Lexical meanings are small lambda terms, not a complete
account of tense, quantification, modification or discourse.

## Preserved references

`data/experiments/references-v1.json` records source commit `c285928`, hashes for
the earlier DS trace, feature, construction, lambda-term and CCG implementation
files, and five native English/Greek state/action-trace fixtures. Those source
files remain unchanged. Tests compare the new DS wrapper against the frozen
states, selected lexical programs and grammar hashes.

`ccg-original-v1` preserves the earlier lexicon/combinators without type raising,
executed through the new incrementally maintained chart. Parity tests compare
its category/meaning results with the earlier chart implementation. The expanded
study lexicon is a separately named configuration. Its additional coverage must
not be attributed solely to a different processing architecture.

## First controlled computational pilot

`contextual-fragment-memory-v1` has 24 authored families: four proper names by
six nouns. An example is target `[John] likes the book`, with either prime
`[Mary] likes a dog` or `[Mary likes] the dog`. Brackets denote displayed prior
context. The lag is zero or two filler observations. Four cyclic lists give
each family every condition/lag combination across four participants, with
deterministically shuffled family order per participant.

The comparison crosses three engine packages, three memories and two observation
models: 18 configurations. DS English, expanded CCG and its application-only
ablation each support all 24 families. Every prime alternative, target and filler
must be supported for a family to enter the common sample. The legacy CCG
fragment supports zero complete families and is reported separately.

The pilot generates 36 simulated participants × 24 targets = 864 response times
per dataset, with three generators and three seeds. The full study, model grid,
generator parameters and source hashes are written before outcomes are generated.
Raw synthetic responses and per-run results go under ignored `build/experiments`;
the committed aggregate contains no collected human responses.

Comparison holds out whole participants in three folds. Lexical families remain
shared. All models receive the same eligible response rows and common RT domain
`RT > .15 s`. Training-only standardization precedes crossed participant/item
Gaussian maximum-likelihood fits on `log(RT - shift)`. Shared predictors are
order, condition, lag and condition×lag; activation is the model-specific column.
The predictive density includes the transformation Jacobian, so scores from the
two response scales are comparable. Uncertainty intervals resample participants
300 times from fixed held-out predictions; they do not refit each bootstrap.
Rank, convergence and variance diagnostics remain inspectable. Non-converged
fits are excluded from recovery winners.

The exact generator is best in only **1 of 9** recovery datasets. Many score gaps
are tiny; all no-memory grammar configurations have identical design matrices
within a measurement choice. One shifted/no-memory fit fails to converge in the
first dataset. This design does not reliably identify the grammatical package.
These observations motivate stronger diagnostic stimuli; they do not establish
equivalence of theories or superiority on human behaviour.

The two conditions confound boundary, POS and length. The items are unreviewed,
all intended positive, and do not have independent acceptability norms. Negative
controls, linguist review, sampling/power work and a finalized prospective
protocol are needed before a human decision experiment. This new authored pilot
is separate from the earlier Nielsen–Christiansen article reanalysis linked in
the original hybrid lab.

## Reproduce and use

```sh
uv sync --locked --extra research --group dev
.venv/bin/ds-workbench --port 8770
```

Open `http://127.0.0.1:8770/experiments.html` for comparisons and
`http://127.0.0.1:8770/experiment-task.html` for rehearsal. The former downloads
the selected configurations, observations, native traces and predictions as
JSON. Both pages and aggregate evidence are packaged in the wheel.

```sh
.venv/bin/python -m dylan.experiments.study
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m dylan.experiments.evaluation --export data/experiments
.venv/bin/pytest -q tests/test_experiment_engines.py tests/test_experiment_components.py \
  tests/test_experiment_study.py tests/test_experiment_evaluation.py
python scripts/check_experiment_browser.py --url http://127.0.0.1:8770
```

The browser check requires Playwright/Chromium. The interactive host itself
does not require NumPy/SciPy or model credentials; fitted comparisons require
the `research` extra. Existing model assistance remains available in the hybrid
lab with the configured OpenRouter/Jev credentials. No AI output is used as
independent human evidence or automatically inserted into this pilot's lexicon.

Rehearsal records a monotonic browser RT, choice and visibility/focus-interruption
flag, then downloads locally. It does not submit a participant database or
recruit anyone. Display onset is not calibrated laboratory timing. Exports are
explicitly labelled `rehearsal`; neither task responses nor their choices are
treated as gold grammaticality/accuracy labels.

```sh
.venv/bin/python -m dylan.experiments.responses build/experiments/browser/rehearsal-0.json \
  --output build/experiments/imported-rehearsal.json --evaluate
```

The importer checks the study hash, event identity, consecutive schedule prefix,
finite timings, explicit choice/visibility flags and duplicate participant
sessions. Both choices are retained; interrupted targets are excluded. Six
participants and six families are the minimum comparison guard, not a power
recommendation. Incomplete sessions remain labelled incomplete. Models replay
the scheduled prefix preceding each recorded target, never future responses.
Independently collected files may explicitly declare `human` and be imported
with `--data-kind human`; the importer cannot authenticate provenance and will
not relabel rehearsal or synthetic exports as human.

For programmatic use:

```python
from dylan.experiments.contracts import Configuration, Observation
from dylan.experiments.host import Session

session = Session(Configuration(grammar="ccg-incremental-v1", memory="count-v1"))
try:
    prime = session.observe(Observation("likes a dog", left_context="Mary"))
    target = session.observe(Observation("likes the book", left_context="John"))
finally:
    session.close()
```

The local API exposes `catalog`, `study`, `schedule?participant=0`, `references`
and `report` resources, plus `POST /api/experiments/run`. Requests are limited to
four configurations, two fillers, 40 words per observation, 16 KiB and a
45-second isolated worker. Each grammar may impose a smaller bound.

## Verification snapshot

The full suite passed **2,236 tests**, with five existing skips and one existing
collection warning. Both browser harnesses pass: independent state rendering,
component swaps, local response export, the original nine hybrid examples,
mobile layouts and invalid-request checks. The rehearsal export passed import;
its deliberately tiny sample correctly produces an insufficient-groups result.

The wheel was installed into a separate target and imported outside the checkout.
CCG runs without loading a DS parser; native English DS, the Greek construction,
packaged pages and report access work. Packaged source files match the recorded
hashes. Raw synthetic/rehearsal responses and credentials are absent.
