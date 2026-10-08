# DS Workbench · dynamicsyntax

An inspectable Dynamic Syntax workbench for teaching, experiments and grammar
development. It builds trees word by word, records operations and search
revisions, and exposes the resulting semantic representation. AI assistance is
optional; the DS engine executes and checks the grammar.

**Try it:** <https://ds-workbench.vercel.app/> ·
**Source:** <https://github.com/StergiosCha/DS_workbench> ·
**Start here:** [community guide](docs/community/README.md) ·
**Extend it:** [contributor guide](CONTRIBUTING.md)

This checkout extends the Python `dynamicsyntax` package, itself a port of
[DyLan](https://github.com/Dynamics-of-Language/DyLan). The inherited engine
supplies incremental parsing, trees, lexical/computational actions, backtracking
and TTR machinery. The workbench adds native Classical and Constructive
semantics, English/Greek grammar families, operation playback, paragraph/dialogue
interfaces, source evidence and bounded model assistance. The
[technical walkthrough](docs/workbench-walkthrough.md) distinguishes inherited
infrastructure from later extensions.

This repository is the workbench's development source; a versioned package
release is still pending. Installing `dynamicsyntax` by name from PyPI does not
establish that you have these changes. Use this source checkout or a wheel built from it.
Record a source version and settings for reproducible research.

## Run locally

Python 3.11–3.13; the current handover check uses Python 3.12 on macOS.
With [uv](https://docs.astral.sh/uv/) installed:

```sh
git clone https://github.com/StergiosCha/DS_workbench.git
cd DS_workbench
uv sync --locked --python 3.12
uv run --no-sync ds-workbench --port 8000
```

Open <http://127.0.0.1:8000/>. No Node build, model key, corpus download or
cloud account is required for bundled grammar examples. Start with
`John likes Mary.` and vocabulary assistance switched off. For offline use,
ignore the live corpus lookup panel. Optional resources are explained in
[setup and everyday use](docs/community/using.md).

For a conventional virtual environment, `python -m pip install -e .` followed
by `ds-workbench --port 8000` is an equivalent source-install route.
Use `uv sync --locked --extra hosting` for the optional ASGI server.
The development server binds to `127.0.0.1`; public hosting uses
`dylan.workbench_asgi:app`, as explained in the maintainer guide.

## Use the Python API

```python
import dynamicsyntax as ds

p = ds.parse(
    "John, who Mary knows, walks.",
    "2026-english-mltt",  # or 2026-english-classical
    strict=True,
    top_n=0,              # retain all lexical alternatives
    trace=True,
)
print(p.ok, p.tree.is_complete(), p.cap_hit)
print(p.semantics)        # (walk(john) ∧ know(mary, john))
p.vis()
```

`ds.get_grammars()` lists bundled grammars. Pass a `pathlib.Path` instead of a
name to load your own directory. The inherited API defaults to `top_n=3`:
that can exclude a needed entry for ambiguous punctuation/function words.
Use `top_n=0` for construction evaluation and record search limits. TTR uses
its own grammars, for example `ds.parse("john likes mary.", "ttr")`;
native extensions are not automatically available in TTR.

## Current scope

| Use | Support |
| --- | --- |
| Teach and inspect DS | Incremental trees, lexical/computational actions, backtracking, formula inspection, JSON export and prepared slides. |
| Compare semantics | Classical λ/ε/τ/ι and Constructive Σ/Π native grammars; distinct inherited TTR record grammars. Shared infrastructure does not imply equal coverage. |
| Develop English grammars | Bounded nominal/verbal constructions, quantification, PP arguments/modifiers, finite complements/connective clauses, restrictive relatives, polar dialogue fragments and named-host nonrestrictive relatives. |
| Investigate Greek | Native Standard Modern Greek extensions; reviewed clitic fragments for Standard, Cypriot, Pontic and Grico, with different coverage by variety. |
| Work with open text | Sentence, paragraph and dialogue interfaces with visible failures; optional WordNet/GDT vocabulary, live Greek evidence and model hypotheses. |
| Study model assistance | OpenRouter BYOK lexical/construction proposals; Jev sense preferences and two-run comparison. Every proposed continuation runs through DS. |

Completion means the selected grammar's requirements are satisfied under its
lexical/context assumptions. It does not establish grammaticality, the intended
word sense, general textual understanding or proof of a proposition. Coverage
is incomplete. Arbitrary paragraphs, full tense/aspect and agreement, broad
discourse inference and backend parity remain open work. The
[coverage protocol](docs/coverage/README.md) separates failures, timeouts,
semantic expectations and independently sourced judgments.

## Learn, reproduce and contribute

- [Practical use and reproducible exports](docs/community/using.md)
- [Executable grammar-extension tutorial](docs/community/extending.md)
- [Maintainer handover and release work](docs/community/maintaining.md)
- [Theoretical coverage catalogue](docs/research/ds-theoretical-coverage.md): 18 categories, 91 topics; source inspection and implementation status are distinct.
- [DS Research Library](docs/research/library/README.md): searchable bibliography (53 works, mostly abstract-level readings), source-to-implementation cards, classification guide and Zotero-compatible exports.
- [Technical walkthrough PDF](docs/workbench-walkthrough.pdf) · [LaTeX](docs/workbench-walkthrough.tex)
- [43 presentation slides](docs/ds-workbench-slides.pdf) · [presenter notes](docs/ds-workbench-slides-notes.pdf) · [LaTeX](docs/ds-workbench-slides.tex)

Contributions can be linguistic evidence, teaching material, grammar programs,
tests or engine/UI changes. No model subscription is needed. Start with
[CONTRIBUTING.md](CONTRIBUTING.md); issue templates support evidence and bugs.

## Distribution status

See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
The inherited BSD metadata conflicted with the cited DyLan LGPLv3 licence;
this snapshot removes that unsupported claim and records the upstream text.
Contributor terms and package release arrangements remain documented in the
[maintainer guide](docs/community/maintaining.md). This repository does not
assign a new blanket licence. GDT data separately carries
CC BY-NC-SA 3.0; corpus/dictionary terms are not replaced by a code licence.
