# DS Workbench presentation

English research presentation, updated 7 October 2026. It includes the
literature survey, native nonrestrictive-relative implementation and community
handover work, while retaining the original dates of earlier evaluations.
Designed for roughly 25–30 minutes, with 30 main slides and nine optional
technical appendix slides. Allow another three to five minutes for the live
demonstrations.

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

- A source-linked map of 18 DS categories and 91 tracked research topics.
- LINK's different semantic uses, followed by a worked nonrestrictive relative:
  `John, who Mary knows, walks.`
- The new family's scope, failure controls and dated verification evidence.
- Community use, independent grammar extensions, packaging and maintenance.
- A research-driven roadmap and a reproducible Python extension example.
- Updated verification and source-release status, including the unresolved
  licence mismatch. Local preparation is distinguished from a public release.

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
2. Slides 7–16: semantic systems, literature map, LINK, the worked relative and Greek clitics.
3. Slides 17–23: independent DS execution, architecture, model construction
   proposals, Jev and evidence sources.
4. Slides 24–30: interaction, coverage evidence, limits, community handover, roadmap and demo.
5. Slides 31–39: optional algorithms, program/Coq details, verification, references,
   full taxonomy, the extension tutorial and release decisions.

The notes clarify schematic diagrams, source/draft pagination, readable naming
of generated predicates, sample limitations and interpretation assumptions.
The taxonomy is a structured review, not an exhaustive literature census or
91 implemented features. The deck separates formal completion from correct
interpretation and the frozen baseline from new authored construction checks.

For the live demo, open <https://ds-workbench.vercel.app/>. Start with **Original
lexicon** and `John, who Mary knows, walks.` in Classical and Constructive.
Then choose **Open text · LLM + verified DS** for the `provided` example and
**See Jev in action** for the `lends` comparison. Enter any API key privately;
model calls use that account. If services are unavailable, use the recorded
examples on slides 21–22 and identify them as recorded results. The new relative
example needs no model request. The offline extension tutorial is in
`examples/community/extend_grammar.py`; details are in `docs/community/extending.md`.
