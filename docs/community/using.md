# Using DS Workbench

## First session without AI

Open <https://ds-workbench.vercel.app/> or launch a local copy using the
[README](../../README.md). Choose Sentence, English and Classical or
Constructive. Leave **Use analysis LLM** and **Use Jev** unticked (the default).
A key is not needed. To use only the original lexicon, open **Models, vocabulary
& advanced settings → Advanced** and choose **Original lexicon**.

The **Parse**, **Corpus & dictionary**, **Greek lab** and **DS Library** tabs
keep these activities in separate views. Switching tabs preserves the current
derivation and makes no parser/model request. Corpus and Greek lab examples
return to Parse when you ask DS to analyse them. The library searches the
curated bibliography by text, topic and framework; review labels distinguish
metadata-only records from inspected sources.

**Connect / models** opens model setup in a side drawer. Connecting does not
enable either model: close the drawer and tick the desired switches. The
**This result** bar records actual model use for the displayed result, separate
from permissions for the next parse. Expand **What the models do** for details.
**Parse options & coverage** contains scope and alternative-analysis settings;
**All examples** opens the full example list. **Evidence & lexical analyses**
below the tree contains diagnostics, source evidence and candidates grouped by
word, with recorded selected entries first where that information is available.

Try `John likes Mary.` and `John, who Mary knows, walks.`. The sentence field
wraps and grows as you type, up to a few lines. **Enter** builds the derivation;
**Shift+Enter** inserts a line break within the same sentence. Use Paragraph
mode for multiple sentences; Sentence mode retains its existing input limits.

After parsing, the tree opens at the **final result**, including the stopping
point of an incomplete derivation. **Replay from start** shows how it grew;
**Show final result** returns to the endpoint. Choosing another analysis or
paragraph sentence also opens its endpoint. Inspect Words, Rules and Operations.
The pointer shows where growth takes place; outstanding requirements explain
why a prefix is incomplete. Expand a node formula for its full lambda term.
During replay, the current tree can be partial even if the final derivation
completed; the meaning heading and status distinguish these states.

**Focus on derivation** fills the app window with the tree, meaning and rule
inspector. Its context strip shows the input and grammar of the displayed
result, its actual model usage and any failure explanation. Paragraph results
have a sentence selector in this view. Playback controls remain reachable while
scrolling. **Fullscreen** uses the browser's fullscreen mode where supported;
**Back to editing** (or Escape outside fullscreen) restores the editing view.
Entering focus pauses playback and preserves the step, selected node and manual
zoom. Switching views makes no parser or model request and does not change model
permissions.

Zooming or panning turns off **Auto-fit**, retaining your view as you step.
Tick it again to fit the growing tree automatically. On mobile, meaning stays
under the tree and **Inspect this step** opens the node/rule inspector.

Playback defaults to **Rules**: lexical rules and computational rules carry
different labels and appear in execution order, with the active rule, pointer
movement and changed decorations above the tree. This includes assisted
sentences and individual sentences in a paragraph. Pause and use Next to
inspect introduction, prediction/anticipation, completion, elimination and
other rules wherever the selected grammar actually uses them. **Operations**
opens the instructions within a rule for ordinary sentence/dialogue traces;
assisted and paragraph traces use the more compact rule level.

These are replays of the path selected by DS at each word, emitted as the
parser advances, not a debugger showing every rejected search branch.
Backtracking explicitly restores an earlier tree. An assisted retry starts
at a new axiom and displays its attempt number. Paragraph rows each have
their own replay. To keep hosted responses bounded, large rule traces can
end with an explicitly labelled jump to the final recorded tree; this display
limit does not change parsing or the coverage count.

Change semantic systems and repeat. Classical uses individual terms with
λ/ε/τ/ι; Constructive composes propositions and dependent types including
Σ/Π. TTR has distinct record grammars: choose a supported TTR example rather
than assuming native examples transfer.

Paragraph mode retains every sentence's success/failure. Failed sentences are
excluded from subsequent context and recorded as gaps; later success does
not establish a complete paragraph interpretation. Dialogue distinguishes
continuing a shared tree from starting another proposition. These modes have
bounded construction coverage, not unrestricted discourse understanding.

## Optional assistance and evidence

The bundled lexicon is always available. The wheel/source checkout includes
the GDT training-derived Greek index with its separate source terms. It is
lexical/frame evidence, not exhaustive valency or test-set training.

For English WordNet candidates, obtain the pinned NLTK WordNet 3.0 archive
from `dylan.lexical_dictionary.ARCHIVE_URL`, then run from source:

```sh
uv run --no-sync python scripts/build_wordnet_dictionary.py /path/to/wordnet.zip
```

The builder verifies the archive hash and preserves its licence. Default
output is `.ds-workbench/dictionaries/wordnet.sqlite3`. For a wheel launched
elsewhere, set `DS_DICTIONARY_PATH` to that absolute path. Without the index,
the bundled grammar still works and dictionary availability is reported.
Local Brown/Gutenberg indexes can be built separately; start with
`scripts/build_english_corpora.py --help`. Their inputs/terms are separate.

Svarna and Triantafyllidis support live investigation and opt-in bounded Greek
lexical evidence. Lookups need network access. Neither a corpus match nor a
gloss supplies a new DS construction by itself.

Connect your OpenRouter key to make model assistance available. Connecting or
choosing a model does not turn assistance on. Tick the controls above the
examples to choose what the next parse may use:

| Analysis LLM | Jev | What runs |
| --- | --- | --- |
| Off | Off | DS with the selected original, bundled, dictionary or corpus vocabulary. No model requests. |
| On | Off | DS with bounded vocabulary and construction assistance when needed. English dialogue supports vocabulary proposals only. |
| Off | On | DS with Jev word-meaning preferences. No generative fallback or cached generative proposals. |
| On | On | DS with Jev word-meaning preferences and an analysis-LLM fallback for missing words. This combined mode does not perform open text construction assistance. |

Jev word-meaning assistance is available for native English; neither model
provides TTR assistance. Unavailable controls explain the applicable limit.
The advanced search-order control remains separately calibrated. **Turn off
all AI** unticks both models and resets that search control. Changes affect
the next parse; they do not automatically start one. A completed result has
separate LLM and Jev request indicators, which do not change when the next-parse
settings change. An enabled model may make zero requests.

The browser retains your key for
the tab session and sends it through the DS server for your requests; calls
use your account. The chosen model proposes lexical analyses or choices within
supported construction families. DS instantiates programs, checks types and
builds the derivation. Unsupported syntax remains incomplete. Jev's pinned
model can reconsider senses; its comparison shows two actual DS runs with
the same candidates. This differs from the separate calibrated search ordering.

## Experimental grammar proposals

The separate **Experimental grammar proposals** checkbox enables the analysis
LLM to write new DS lexical action programs after a failure, including constructions
beyond the ordinary templates. It also works with Jev enabled. Choose a native
English or Standard Greek sentence in Classical or Constructive DS; paragraphs,
dialogue and TTR are not supported by this experiment. Turning off the analysis
LLM or **Turn off all AI** also disables experimental proposals.

Inspect the experimental result panel for the proposed rules, declarations and
DS retries. A success is explicitly labelled **Complete under experimental grammar**:
DS satisfied its requirements assuming these unreviewed rules. That is not an
independent validation of their linguistic analysis. The rules last for this
request and are included in Export JSON. Review and test them before contributing
them to the maintained grammar. **Edit & keep rules** opens the grammar workshop:
edit programs and declarations, add positive/negative examples and expected
meanings, and check them with DS. Save a personal pack, then tick **Use my rules**
to reuse it on new sentences without AI. **My grammars** reopens saved packs;
download a contribution pack to back it up or share it. Personal results retain
an explicit label; saving does not add rules to the shared grammar. See the
[workshop workflow](../design/grammar-workshop.md) and
[experimental limits](../design/experimental-grammar.md).

## Reproduce a result

Export JSON and record source version (release or commit), grammar/backend,
exact input and turn/sentence boundaries, vocabulary mode, dictionary/data
version, search limits and context assumptions. For AI-assisted runs also
record provider/model, candidates, decisions and the actual DS result. Replay
saved candidates for deterministic comparisons; a fresh model request need
not return the same answer.

For Python experiments, `ds.parse(..., strict=True, top_n=0, trace=True)`
retains all lexical alternatives and records states/actions. Check `ok`,
`tree.is_complete()` and `cap_hit`. The [tutorial](extending.md) writes grammar
hashes, expected meanings and outcomes. The HTTP schema and `dylan.*` internals
are experimental; pin a version. The hosted API has interactive limits and
is not a batch-service SLA.

Check exported files for private source text before sharing. Constructive
Coq export can be compiler-checked; that does not prove the sentence true or
the type inhabited. Record compiler availability and result separately.

The Python API's older LaTeX export additionally requires `latexmk` and the
PSTricks-related TeX packages (`pst-tree`, `pstricks`, `epic`, `ecltree`,
`txfonts`, `rotating`). This is separate from the presentation/report build,
which uses XeLaTeX. Optional export checks skip with the missing dependency
named; installing a TeX executable alone does not establish all packages exist.

## Limits that matter in research

Completion, intended interpretation, independently sourced grammaticality and
unseen-text generalisation are separate measurements. Small published probes
are dated engineering samples; new passing examples do not revise them.
Theory, authored tests, held-out evaluation and model assistance each need
their own evidence and denominator.
