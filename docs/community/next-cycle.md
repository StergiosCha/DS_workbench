# A proposed first community development cycle

This is an invitation to organise the next increment together. Tasks are
unassigned and timings are suggestions, not commitments. Start with one
bounded construction family and a small group covering source analysis,
implementation and independent review. Contributions can also be entirely
linguistic, bibliographic or pedagogical.

## Choose a first contribution

| Interest | A small first task | Deliverable |
| --- | --- | --- |
| Linguistic analysis | Review the PCC or nonrestrictive-relative analysis card against the cited source. | Corrected source locators, context, intended meanings and excluded cases; distinguish source examples from authored probes. |
| Theory/library | Read one paper or a specified section in a chosen topic. | Verified metadata/version and a bounded analysis card; record exactly how much was read. |
| Grammar programming | Run the independent `dance` extension tutorial, then propose one family using the construction template. | Reproducible results, separate backend expectations and a reviewable implementation plan. |
| TTR | Audit one existing record-grammar example for participant identity, dependencies and composition. | Expected record content, trace and regression test; treat a TTR-DS state/action prototype as a separate proposal. |
| Evaluation | Assemble a small, source-documented English or Greek test set, separate from examples used to develop the fragment. | Inputs, contexts, semantic expectations and all outcomes, including failures and search caps. |
| Teaching/interface | Prepare a short exercise using Rules playback, formula inspection and one failure contrast. | Settings, expected steps/meaning and a reproducible issue for any confusing behaviour. |
| Maintenance | Reproduce the local setup and investigate the Python 3.13 CI timeout recorded for application snapshot `1aff525`. | A documented reproduction and focused fix, if identified; then a fresh CI result. |

Open a [construction/evidence issue](https://github.com/StergiosCha/DS_workbench/issues/new?template=construction.yml)
or a [reproducible problem report](https://github.com/StergiosCha/DS_workbench/issues/new?template=bug.yml).
Check existing issues first. State the area you would like to take on and
whether you can supply evidence, implement, review, or combine these roles.
Opening an issue is an expression of interest, not an assignment of authority.

## Start using the existing resources

The [public app](https://ds-workbench.vercel.app/) needs no key for bundled
grammar examples. Use **Parse**, leave **Use analysis LLM** and **Use Jev** off,
and try `John, who Mary knows, walks.` in native English Classical/Constructive.
Inspect **Rules**, the full node formulas and the final meaning. Switching
to **DS Library** preserves the result. TTR has its own examples and grammar;
native English coverage does not transfer automatically.

For local research, clone the [repository](https://github.com/StergiosCha/DS_workbench),
then follow the [setup instructions](../../README.md#run-locally). Record the
commit used; the slides describe application snapshot `1aff525` and were updated
in `cdb1f3b`. Installing the upstream package by name is not a substitute for
this checkout.

The [grammar tutorial](extending.md) creates independent copies and runs twelve
checks across the native backends. It is a manageable first programming task.
The [using guide](using.md) explains model permissions, traces and exports;
the [maintainer guide](maintaining.md) covers packaging, workers and hosting.
The [technical report](../workbench-walkthrough.pdf) provides longer background;
the using guide documents the latest workspace controls.

## Agree one construction family

Use the [18-category/91-topic catalogue](../research/ds-theoretical-coverage.md)
and [research library](../research/library/README.md) to choose a tractable
increment. Possible starting proposals include a bounded Greek relative
fragment, a source-based PP argument/modifier extension, or predicate reuse
for a restricted ellipsis example. These are candidates for review, not claims
that the necessary general constructions already exist.

For the chosen family:

1. **Define the analysis.** Name the language/variety and discourse assumptions;
   cite a source version, section and example. Mark implementation adaptations
   and competing analyses explicitly.
2. **Agree the interpretation before the code.** Specify roles, reference,
   scope and the intended semantic object. Add licensed examples, excluded
   contrasts and incomplete prefixes. Do not derive grammaticality labels
   from parser acceptance or failure.
3. **Map the DS program.** Identify lexical triggers, computational actions,
   pointer motion, requirements and any LINK/MERGE/reuse operations. Specify
   their preconditions and how requirements close.
4. **Implement and review by backend.** Classical, Constructive and TTR have
   separate semantic obligations. Starting with one backend is acceptable;
   mark the others as unsupported until independently checked.
5. **Measure the increment.** Run deterministic grammar tests and interaction
   checks, then evaluate fresh examples. Publish the denominator, failures,
   caps and semantic errors as well as completions. Keep model-assisted
   comparisons separate from grammar coverage.

Use the [construction template](construction-template.md) for the proposal.
The [nonrestrictive-relative implementation trail](extending.md#implement-a-construction-family)
shows where builders, atomic effects, semantics and tests fit together.

## A suggested four-week rhythm

| Stage | Work | Reviewable result |
| --- | --- | --- |
| Week 1 | Try the app/tutorial, gather interests and select one family. | An issue naming scope, proposed contributors and the source-reading task. |
| Week 2 | Review the source and agree semantic/negative examples. | A construction proposal and independent linguistic review, with disagreements retained. |
| Week 3 | Implement the bounded fragment and inspect its traces. | A small PR with deterministic meaning/requirement tests and declared backend support. |
| Week 4 | Test interactions and fresh examples; write the teaching/reproduction example. | Reviewed code if ready, dated results and a clear list of remaining gaps. |

Evidence-only work can complete at week 2; difficult analyses should remain
proposals until their semantic contract is clear. No deployment, meeting date
or reviewer is appointed by this plan.

## Share responsibility so the project can continue

Agree responsibility for linguistic review, engine/semantic review and
release/CI maintenance. Language-specific maintainers can curate fragments;
changes to shared tree or formula operations need review across affected
grammars. Preserve source reasoning and reproducible commands in the repository
so progress does not depend on private chat history.

Before a tagged workbench package release, settle contributor/licence terms,
citation metadata, release ownership and reproducible artifacts, as recorded
in the [maintainer guide](maintaining.md). The public development repository
already exists. A shared Zotero group and synchronization workflow are optional
future library work; the current bibliography and import files are available now.

The first cycle is successful when another contributor can explain, reproduce
and review an increment using its source analysis, programs and tests.
