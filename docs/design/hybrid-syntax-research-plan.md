# Hybrid syntax research plan

Date: 2026-10-27. Status: proposal; the capabilities below are planned unless explicitly identified as existing.

Build an incremental research workbench in which sequential memory, grammatical structure and interpretation make separately inspectable contributions. Use Nielsen and Christiansen's nonconstituent priming findings as the first empirical comparison, then develop a bounded multilingual hybrid. Keep alternative analyses executable when their theoretical commitments conflict.

## 1. Starting point and questions

The existing Workbench has a DS parser, action-bearing DAG edges, distinct semantic backends, grammar induction, bounded construction assistance, a grammar workshop and optional model-assisted lexical selection. Relevant implementation points are:

- `src/dylan/parser/interactive_context_parser.py`: incremental parsing, search and replay.
- `src/dylan/dag/dag_edge.py`: actions and words on derivational edges.
- `src/dylan/induction/em_learner/candidate_sequence.py`: candidate sequences and equivalence modulo peripheral computational actions, in inherited induction machinery.
- `src/dylan/lexical_selection.py`: prefix-sensitive preferences and revision.
- `src/dylan/construction_assistance.py` and `src/dylan/grammar_workshop.py`: bounded proposal compilation and inspectable grammar packs.

These are implementation hooks, not an existing general chunk-learning or human reaction-time model. TTR induction does not automatically transfer to the native Classical and Constructive backends. The September Jev search calibration found no search improvement in its measured fragments; the separate lexical-sense demonstrations do not overturn that result.

First questions:

1. Does ordered category-sequence memory explain the published priming contrasts beyond lexical and semantic predictors?
2. Do shared DS actions or partial states explain additional variation?
3. Can independently specified hierarchical fragments explain the same effects?
4. Do combined representations improve prediction on held-out items, or merely add parameters?

A positive answer for one representation is not a proof that another representation is absent. A null incremental contribution is an informative outcome.

## 2. First deliverable: data reproduction and coverage audit

Import the public OSF material for Studies 1–4. Preserve source identifiers, experimental lists, participant identifiers, trial order, prime/target pairing, responses, exclusions and condition labels. Record source versions, checksums and reuse terms. Keep corpus material requiring separate access outside redistributable bundles.

Reproduce published contrasts using the supplied analysis code where available. Record effect estimates and uncertainty, including differences caused by software versions or exclusions. This is a reproduction of existing data, not a new preregistered replication. Preregister only genuinely prospective comparisons or new data collection.

Audit the entire stimulus inventory for lexical and construction coverage before selecting a DS subset. Report unknown words, unsupported constructions, timeouts and analysis ambiguity separately. A parser's failure is not a grammaticality judgment. If a subset is necessary, choose complete matched item sets using criteria independent of the human effects and report how it differs from the full dataset.

The original task presents complete short strings and asks whether they could occur somewhere in an English sentence. Some are sentence-medial fragments. Running each from the ordinary DS sentence-start axiom would test the wrong thing. Specify a fragment-recognition task model: sample or marginalize over possible left contexts from an independent corpus, under a fixed search bound and prior; leave rightward requirements open. Apply the same context protocol to the compared structural models. Condition-supplied contexts constitute a separate contextualized experiment. Exhausting a bounded search establishes lack of a found analysis, not impossibility in English.

Deliverables: source manifest, normalized trials, reproduction report, full coverage report and an inspectable set of complete matched examples. No claim about the winning theory is required to complete this stage.

## 3. Formal contract and trace instrumentation

Start with the existing native Classical English fragment to limit simultaneous changes. Expose DS through an adapter; keep its commitments explicit. The common interface specifies observations and tasks, not a universal linguistic ontology.

For each grammar module g, specify its state space Q_g, initial states I_g, transition relation delta_g, completion predicate C_g and interpretation relation J_g. A token transition is a relation in Q_g × W × Q_g, allowing multiple analyses. Specify epsilon steps, search bounds and failure outcomes separately. An unimplemented capability returns unsupported, rather than false.

Every traced transition records input position, observed text, speaker/context, pre-state, action and lexical program identity, post-state, pending requirements, semantic contribution, alternatives considered and provenance. Scoring is separate from structural licensing. Store the actual computational actions, not merely their display names. Normalize variable names only with an explicit binding-preserving procedure; preserve pointer conditions, feature constraints and semantic operation shape.

For a deterministic action sequence, a proposed reusable macro has the form A_c = a_k ∘ ... ∘ a_1, a partial map from states to states. If actions branch, compose relations instead. Reuse preserves its applicability conditions. A POS sequence is an observed pattern, not automatically an action equivalence class. Audit the inherited CandidateSequence equivalence operation before using it across words or semantic backends.

For runtime incrementality, execute a multiword macro only as its words arrive. Prediction may anticipate later words but cannot treat them as observations. Retain intermediate states for ambiguity, interruption and repair. Priming between separate trials requires an explicit memory that persists while task-specific parse state resets.

Acceptance: traces can be replayed; instrumentation preserves existing analyses; macro execution matches expanded execution on bounded fixtures including failed preconditions and ambiguous paths. Search-cap outcomes remain visible. These tests establish local properties, not general equivalence of frameworks.

## 4. Controlled model comparison

Use the same data splits, available context and outcome model. Give competing representations comparable adaptation mechanisms and tune their capacity on training/development data. Include:

| Model | Added representational predictors |
| --- | --- |
| M0 | Lexical frequency, repetition, length, semantic similarity and task controls |
| M1 | Ordered POS sequence frequency and recency, including bigram and trigram ablations |
| M2 | Explicit constituent/tree-fragment memory, including incomplete fragments |
| M3 | DS partial-state and action-sequence memory, with separate state/action ablations |
| M4 | Combined sequential and DS predictors |

M2 prevents a comparison in which only the sequential model is permitted to represent fragments. An unweighted deterministic DS parser alone cannot predict priming. Specify how memory activation affects search or prediction and how those quantities map to human measurements.

For an initial representational comparison, fit the same mixed-effects reaction-time model with each feature family; model accuracy separately. Fit the mapping only on training data and assess held-out predictive likelihood and priming contrasts with uncertainty. Reaction time, next-token surprisal, task accuracy and parser runtime are distinct outcomes. A feature model that predicts reaction times is not yet a mechanistic account of those times. Develop a more detailed task model only if the first comparison warrants it.

Hold out matched item families together so lexical variants cannot leak across splits; separately assess new participants and generalization to new category patterns. Prevent future trials from entering recency features. Preserve trial histories and counterbalancing. Retain the published reversed-order and part/whole contrasts. Add independently annotated examples with the same POS sequence but different structural analyses, and structurally similar examples with different POS sequences. Use these in a subsequent prospective test.

Primary decision: does an added representation improve held-out prediction with uncertainty that supports a practical gain, after accounting for coverage and complexity? Fix the metric, model selection procedure and any practical threshold before the final evaluation. Retain the simpler model when additional machinery supplies no reproducible benefit. Extend to reading and conversation only after the experimental pipeline is stable; those observational data require their own confound analysis.

## 5. Grow the hybrid through explicit linguistic modules

The empirical comparison and broader grammar development share traces and examples, but neither requires completing the other. Add one bounded phenomenon at a time. Each module needs objects, constraints/operations, an interpretation, positive and negative examples, and a declared interaction with existing modules.

| Contribution | Concrete first implementation | Required check |
| --- | --- | --- |
| DS | Existing incremental interpretation, unfixed structure and contextual revision | Partial input, continuation, ambiguity and repair |
| HPSG-inspired constraints | Typed feature graphs, appropriateness, reentrancy, agreement and valence constraints | Unification failures, underspecification and argument sharing; TTR records alone are not this system |
| LFG | Explicit PRED/SUBJ/OBJ/COMP structures and mappings from the chosen surface/derivational representation | Completeness/coherence at declared closure points; pending obligations during input; bounded functional uncertainty for extraction |
| Construction Grammar | Inheritable constraints on form, meaning and use, with declared conflict/override semantics | Novel slot fillers, incompatible inheritance, and constructions spanning partial analyses |
| Minimalist grammars | A specified Stabler-style feature-driven Merge/Move fragment with copy/interpretation conventions | Feature licensing, movement dependencies and contrasts on which the grammar disagrees with DS or LFG |
| CCG | A bounded lexicon with explicitly enumerated application, composition and type-raising rules | Flexible constituency, unfinished categories and coordination examples from the paper |

Start the first hybrid grammar extension with Greek polydefinites, an existing Workbench gap. Use a sourced account of shared reference, repeated definiteness, adjective order and agreement. Add an ordinary clause example to expose LFG grammatical-function mappings. Then use a bounded extraction/relative-clause family to compare DS dependency resolution, LFG functional uncertainty and MG Move.

Minimalist locality, phases, economy and functional-head hierarchies become separately declared hypotheses. Stabler-style MGs do not automatically implement every phase theory or cartographic proposal. For a small cartographic test, specify a finite head order and competing orders; encoding an order does not derive it. A nanosyntactic experiment additionally needs explicit lexical trees, spellout domains, a matching relation and competition rules, and is a later extension.

Use coordinated modules where they express compatible constraints. Use competing configurations where they disagree: primitive LFG functions versus configurationally derived relations, movement copies versus an unfixed-node account, or differing locality restrictions. Specify correspondence conditions in a hybrid configuration. Do not conjoin all frameworks and call the result their synthesis.

For any claimed translation, state the preserved property: strings, interpretations, dependencies or incremental behavior. Demonstrate soundness/completeness for the declared fragment if claiming equivalence; otherwise call it a partial mapping. Shared examples alone do not establish notational equivalence.

## 6. LLM and Jev support after fixed baselines

Use the existing model interfaces and the TypeSafe pattern of code-defined candidates with narrow judgments. An LLM can draft lexical entries, construction hypotheses, annotations and counterexamples for inspection and compilation. Generated examples remain synthetic evidence and are checked independently before entering an evaluation set.

Jev can rank licensed sense, construction or continuation candidates using the available context. Provide no-match/uncertainty handling and retain alternative analyses. The selected grammar configuration determines licensing; model scores do not silently add grammatical rules. Log the state, candidate inventory, model identity, answers, revisions, latency and cost. Freeze prompts and parameters before evaluation; use held-out local calibration rather than a universal confidence threshold.

Compare the same candidate inventory under ordinary ordering, count-based ordering and Jev ordering. Measure interpretation quality, coverage, search work and total latency including network calls. Public stimulus familiarity in a pretrained model prevents treating its success as uncontaminated human-like learning. Newly constructed, independently checked contrasts are a separate evaluation.

Acceptance: an additional model earns deployment through measured benefit on the target task and preserved grammatical checks. Lack of benefit remains a reportable result, consistent with the existing search calibration.

## 7. Workbench experiment view and delivery order

Add an experiment view after the trace and comparison formats stabilize. Show a prime and target, observed input, representations activated, pending requirements, candidate scores and the resulting analysis. Allow replay under frozen model configurations. Keep observed human measurements separate from model predictions and software timings. Link each rule, stimulus and claim to its source and version.

Deliver in this order:

1. OSF import, reproduction and full coverage report.
2. Task protocol, canonical traces and replay checks on complete matched item sets.
3. M0–M4 comparison, uncertainty report and prospective contrast specification.
4. Polydefinite feature/construction extension and explicit LFG mappings.
5. Bounded MG and CCG comparisons; optional head-order and spellout experiments later.
6. Controlled LLM/Jev additions and the experiment interface.

The first implementation increment stops at a reproducible data-and-trace report. The eventual research claim depends on which representations improve empirical predictions and linguistic coverage, and on the costs and restrictions they introduce.

## Sources and limits of the current review

- Nielsen and Christiansen, [Evidence for the representation of non-hierarchical structures in language](https://www.nature.com/articles/s41562-025-02387-z), published 21 January 2026; [public supplement](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41562-025-02387-z/MediaObjects/41562_2025_2387_MOESM1_ESM.pdf); [OSF data and code](https://osf.io/ymndq/). The current review accessed the abstract and full supplement, not the subscription-restricted main text. Obtain the complete paper through an available legitimate source before finalizing the study specification.
- [Workbench source and coverage report](../reports/arash-meeting-report-2026-10-19.md), including distinctions among semantic backends and the polydefinite gap.
- [Induction pipeline](../induction-pipeline.md).
- [Existing Jev search calibration](jev-calibration-2026-09-30.md) and [separate lexical comparison](jev-comparison.md).
- Live TypeSafe [building guide](https://docs.typesafe.ai/concepts/how-to-build-with-system-one) and [reranking example](https://docs.typesafe.ai/cookbooks/rerank_typesafe), consulted 2026-10-27. Their examples motivate an integration pattern, not evidence of benefit on this linguistic task.
