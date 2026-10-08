# DS Workbench presentation

English research presentation, updated 8 October 2026 against application
snapshot [`1aff525`](https://github.com/StergiosCha/DS_workbench/tree/1aff525).
It covers the public workspace, model controls, computational-rule playback,
DS Research Library and community repository alongside the semantic backends
and grammar extensions. Earlier evaluations retain their original dates.
Designed for roughly 30–35 minutes, with 33 main slides and nine optional
technical appendix slides. Allow another four to six minutes for the live
demonstration. For a shorter talk, omit the worked-relative details (14–16)
and use the appendix only for questions.

- `ds-workbench-slides.tex`: standalone editable Beamer source, 16:9.
- `ds-workbench-slides.pdf`: projection/share version.
- `ds-workbench-slides-notes.pdf`: slide and presenter notes side by side.
- `workbench-walkthrough.pdf`: the longer technical report.

The source embeds its vector diagrams and speaker notes; it does not need
external images, a bibliography file, the DS runtime, or a model key to compile.
Edit `\DSPresenter` near the start to add the presenter's name. The development
credits remain upfront: Astra with Codex; Fable 5.1 with Claude Code;
OpenRouter for models in the app. Dates and coverage figures refer to their
stated evaluations; updating the slides does not rerun those experiments.

## Added in this update

- Four workspace views, model settings drawer, grouped lexical evidence,
  retained zoom, mobile controls and meaning below the tree.
- The four LLM/Jev switch combinations, including the combined mode's lack of
  construction assistance, and actual usage counters separate from permissions.
- Lexical and computational rules in execution order, their relation to
  Introduction/Prediction, and the limits of rule/operation replay.
- The in-app library: 53 works, 30 fingerprinted source versions and eight
  analysis cards; source inspection and implementation are different records.
- An explicit distinction between the inherited DS–TTR semantic backend and
  Cooper and Larsson's TTR-DS recasting of states/actions, which is not implemented.
- The SMG PCC control `του με έδωσε`, alongside the valid third-person cluster.
- The public repository and current verification evidence. The release checklist
  stays in the maintainer guide; the appendix ends with the grammar-extension example.
- Updated demo steps using the visible model switches and library tab.

The 18-category/91-topic research map, worked nonrestrictive relative, PP
analysis, architecture, recorded model/Jev demonstrations, limitations and
extension tutorial are retained. No new linguistic coverage or live model
evaluation is claimed by this presentation update.

## Build

From the repository root:

```sh
python3 scripts/build_workbench_slides.py --notes
```

Requires XeLaTeX, Beamer, TikZ, fontspec and unicode-math (TeX Live/MacTeX).
Fonts use Arial and Menlo when available, otherwise DejaVu Sans and DejaVu
Sans Mono; mathematics uses STIX Two Math or Latin Modern Math. Install the
fallback fonts if compiling on a system without the preferred fonts.

The helper compiles twice, rejects missing characters and overflowing boxes,
and keeps build logs in the system temporary directory. No app dependencies
are required. Alternatively, from `docs/`, run twice:

```sh
xelatex ds-workbench-slides.tex
```

## Suggested delivery

1. Slides 1–6: development tools, problem, incremental tree growth and software foundation.
2. Slides 7–17: semantic systems, literature/library map, LINK, worked relative and Greek clitics/PCC.
3. Slides 18–25: independent DS execution, architecture, model responsibilities,
   explicit switches, construction proposals, Jev and evidence sources.
4. Slides 26–33: interaction, redesigned workspace, rule playback, coverage,
   limits, community use, roadmap and demo.
5. Slides 34–42: optional TTR distinction, algorithms, program/Coq details,
   verification, references, taxonomy and the extension tutorial.

The notes clarify schematic diagrams, source/draft pagination, readable naming
of generated predicates, sample limitations and interpretation assumptions.
The taxonomy is a structured review, not an exhaustive literature census or
91 implemented features. The deck separates formal completion from correct
interpretation and the frozen baseline from new authored construction checks.

For the live demo, open <https://ds-workbench.vercel.app/> in **Parse**.

1. Leave **Use analysis LLM** and **Use Jev** off. Parse
   `John, who Mary knows, walks.` in native English Classical/Constructive.
   Step through **Rules**, inspect LINK/MERGE, and select **Show final result**.
   To force the original vocabulary, open **Connect / models → Advanced** and
   choose **Original lexicon**, then close the drawer.
2. Connect an OpenRouter key privately. Turn **LLM on, Jev off** for
   `John walks provided Mary walks.` Inspect the proposed/used relation and
   **This result** counts. Both switches on selects a lexical assistance route
   without construction assistance, so it is not the configuration for this example.
3. Turn **LLM off, Jev on**, open **See Jev in action**, and compare
   `John lends a book to Mary.` with the same lexical candidates in two DS runs.
4. Open **DS Library**, search `PCC` or `CL25`, inspect review scope, and return
   to Parse to show the preserved result.

If services are unavailable, use the recorded examples on slides 23–24 and
identify them as recorded. The relative and library need no model request.
The extension tutorial is `examples/community/extend_grammar.py`; details are
in `docs/community/extending.md`.

## Verification scope

The 8 October workspace snapshot passed 81 targeted Python tests, six rule-playback
browser cases, 19 PCC browser cases, and seven grouped workspace checks on source,
the exact deployment bundle and the public URL. Workspace model controls were
checked with fixture credentials; these are not new live model-quality results.
CI [37753914626](https://github.com/StergiosCha/DS_workbench/actions/runs/37753914626)
passed Python 3.11/3.12 and installed-package jobs; its Python 3.13 job was
cancelled at the 45-minute limit. It is not described as an all-green run.
The preceding rule-playback commit had a successful full CI run. Counts overlap
and should not be added together. Earlier dated coverage samples remain unchanged.

Both presentation PDFs were rebuilt with two XeLaTeX passes on 8 October:
42 pages each, zero overflowing boxes and zero missing characters. The slides
were visually reviewed, including the new diagrams/tables and presenter notes;
extracted text stayed inside the page bounds. The library builder's consistency
check also passed for the counts shown in the deck.
