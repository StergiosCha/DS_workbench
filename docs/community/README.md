# Taking over and using the workbench

There are three entry points: use the public app for investigation or teaching,
run a pinned local copy for research, or extend a grammar/engine with executable
evidence. Handover should work without the original developer's machine,
model keys, Azure account or conversation history.

| I want to… | Start here |
| --- | --- |
| Demonstrate DS and inspect a derivation | [Using the app](using.md), [slides](../ds-workbench-slides.pdf) |
| Run locally or call Python | [README](../../README.md), [reproducibility](using.md#reproduce-a-result) |
| Add a word or domain vocabulary | [Executable extension tutorial](extending.md) |
| Add a construction or language | [Extension process](extending.md), [design template](construction-template.md) |
| Supply theory or empirical judgments | [Contribution routes](../../CONTRIBUTING.md), [research catalogue](../research/ds-theoretical-coverage.md) |
| Curate DS papers or extract an analysis | [Research library and classification guide](../research/library/README.md), [searchable catalogue](../research/library/index.html) |
| Maintain or host the project | [Maintainer guide](maintaining.md) |

The theory catalogue starts the backlog: 18 categories and 91 topics, with
the operations and semantic questions an implementation must address. A topic
being described in DS literature does not mean it is implemented here. The
first new slice from that survey is bounded English nonrestrictive relatives,
with exact meanings and excluded contrasts in `tests/test_nonrestrictive_relatives.py`.

## A practical community structure

Maintainers should collectively cover linguistic analysis, parser/semantic
implementation, and release/teaching infrastructure. These are responsibilities,
not appointed people. An extension can have a language-specific reviewer;
a change to shared MERGE, LINK, binding or formula equality needs evidence
across affected grammars. Preserve alternative analyses with explicit
assumptions instead of treating theoretical disagreement as one unexplained
“correct” parser result.

The public development source is [StergiosCha/DS_workbench](https://github.com/StergiosCha/DS_workbench).
Contributor terms and a versioned research/demo release remain maintainer work.
Choose one bounded family from the catalogue, add source cases and
semantic contrasts, implement it and publish the measured coverage delta.
[Maintaining](maintaining.md) records remaining release decisions.
