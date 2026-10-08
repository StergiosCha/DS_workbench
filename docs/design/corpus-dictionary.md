# Corpus and dictionary integration

The workbench's **Corpus & dictionary** panel offers Greek through the public
Svarna Corpus Workbench and Triantafyllidis, and English through local
Brown/Gutenberg indexes and WordNet. Source lookups are read-only and require
no model key. Corpus attestation, dictionary senses and DS derivations remain
separate observations.

## Greek sources

1. Follow **Corpus & dictionary** below the sentence input. Choose General Greek,
   Literature, or Greek varieties. Corpus/variety, register and mode filters are
   loaded from Svarna's metadata when the panel comes into view.
2. Search for words/a phrase, or select one corpus and use a regular expression.
   Search returns 20 examples per page, retaining each complete source sentence,
   its metadata, query, filters and retrieval time. Export results downloads the
   current page and its search context; it does not export every matching sentence.
3. Type a lemma into the Triantafyllidis panel, or highlight text in an example
   and click **Look up selected word**. Search headwords or whole entries. The
   panel displays published entry text with source links and attribution. For
   more dictionary results, follow the source link to its pagination.
4. **Select example** opens the original text, metadata, and a separate editable
   analysis field. The full source is never silently truncated or normalized.
   Choose a short excerpt if necessary: parsing allows 500 characters/40 tokens.
5. Choose a comparison grammar and classical or constructive semantics, then
   **Analyse with DS**. The normal tree, diagnostics, alternative readings and
   semantic exports follow that parse.

Cypriot/Pontic corpus labels suggest their corresponding comparison grammar.
Other sources require an explicit choice. In particular, Cretan is not silently
mapped to Standard Greek, and the GRDD Griko label does not establish that a
sentence belongs to the Salentino Grico fragment. Literature and General Greek
also require an explicit comparison choice rather than assuming a historical
text is Standard Modern Greek.

The derivation's browser JSON export includes `research_source`: the untouched
source observation, search URL, time, query/filters, actual analysed text, an
`edited` flag, and the chosen grammar. This is browser-attached provenance, not
a server certification. A manually entered different sentence drops the earlier
source association. The source sentence's fingerprint is a content hash, not a
claimed upstream stable sentence ID. Missing source metadata stays missing.

## English sources

Choose **English · Brown / Gutenberg + WordNet** in the language selector.
Brown supplies general written English with document and genre filters;
Gutenberg supplies literature with book filters. Search a literal word/phrase,
or choose a document, book or genre for regex. Results, pagination, selected-word
dictionary lookup, source selection and JSON export use the same panel as Greek.

WordNet offers noun and verb senses from the existing installed dictionary
index. Each sense shows its synset identifier, words sharing that synset, gloss
with any source examples, and verb frames where available. Word/lemma lookup
includes candidate inflections such as `lends` → `lend`; definition search finds
a literal substring in glosses. Repeated synonyms are grouped into one synset.
Up to 60 senses are shown. The source link describes WordNet; it is not an
individual online entry. No LLM or Jev chooses a contextual sense in this panel.

Select an example and choose **Classical**, **Constructive** or **DS-TTR**.
Native modes select the English fragment; TTR offers installed English TTR
grammars, defaulting to `2015-english-ttr`. Transfer enables the existing local
WordNet lexical candidates for supported native grammars and turns decision
selection off. TTR uses its grammar's own lexicon. The source lookup does not
generate lexical programs or add constructions. Most unrestricted corpus
sentences remain beyond these fragments; a failed parse is a coverage result.

The analysis field is explicitly editable. For example, selecting a long Brown
sentence and replacing the analysis text with `john likes mary.` leaves the
original visible and exports `edited: true`. Reusing that text with a different
grammar updates the recorded comparison grammar. Entering an unrelated sentence
manually drops the source association.

### Local indexes and reproducibility

Build from already installed NLTK archives and plain-text English Punkt parameters:

```sh
# Use a Python environment with NLTK installed; the workbench runtime needs no NLTK.
python scripts/build_english_corpora.py --nltk-data ~/nltk_data
```

The builder performs no downloads. Required inputs are `corpora/brown.zip`,
`corpora/gutenberg.zip`, and `tokenizers/punkt_tab/english/` under that directory.
It writes ignored SQLite/FTS5 indexes under `.ds-workbench/corpora/`; override
the build location with `--output`, and set `DS_ENGLISH_CORPORA` to that directory
for the server. Each finished index replaces its staging file. A missing or
unreadable index produces an explicit error. WordNet uses the pre-existing
`.ds-workbench/dictionaries/wordnet.sqlite3` (`DS_DICTIONARY_PATH` override),
built with `scripts/build_wordnet_dictionary.py` as described in the
[lexical expansion notes](lexical-expansion.md).

The installed snapshot contains 500 Brown documents / 57,340 sentence units and
18 Gutenberg books / 94,434 automatically segmented spans. These are sentence
unit counts, not token occurrences. Their representations differ:

- Brown keeps one nonempty tagged line per unit. Display removes POS tags and
  joins tokens with single spaces, including spaces before punctuation. Metadata
  retains the original tagged line, line number, UTF-8 encoding and character
  offsets in the decoded document.
- Gutenberg decodes the NLTK files as Latin-1 and preserves exact character spans.
  English Punkt parameters are loaded from text, never pickle. Headings, verse
  and dialogue can yield imperfect sentence boundaries. Each observation records
  offsets, segmentation method, NLTK version and parameter-file hashes.

Both record the archive SHA-256, document identifier/title and local unit ID.
The source-passage endpoint returns the observation and the archive README with
its attribution. Fingerprints incorporate archive identity, unit ID and text;
local IDs are not claimed to be publisher identifiers. Search ignores case,
uses SQLite's Unicode token index and matches consecutive indexed tokens for
phrases. Punctuation is not an exact-character constraint; use regex for that.
Inflected forms are searched separately in corpora.

English requests run in a separate read-only worker with a hard 15-second limit,
including regex scans. SQL values and literal FTS phrases are parameterized;
regex requires a document/book or genre filter. A timed-out scan returns an
error, not a partial count. No runtime corpus downloads or model calls occur.

| GET endpoint | Options |
| --- | --- |
| `/api/research/english/corpora` | `db`: `brown` or `gutenberg` |
| `/api/research/english/search` | `db`, `q`, `kind`, `corpus` (document ID), `register` (genre), `mode`, `limit`, `offset` |
| `/api/research/english/dictionary` | `q`, `scope` (`headword`/`entry`) |
| `/api/research/english/passage` | `db`, `id` (local unit ID) |

Query and pagination bounds match the Greek routes. English sources currently
contain written material only. This is a local collection of Brown and NLTK's
Gutenberg selections, not an API connection to all Project Gutenberg or a
contemporary web corpus.

## Greek source behavior

- Words/phrase search uses Svarna's existing index; it is not lemma expansion,
  morphological analysis, or construction recognition. Regex matches raw text.
- Counts are matching sentences, not token occurrences. Regex totals are always
  labelled as potentially capped because Svarna can stop a scan early.
- Svarna currently incorrectly escapes hyphens in indexed metadata filters.
  For known, unambiguous metadata labels, the adapter uses equivalent token
  boundaries in the upstream phrase filter. The original labels and the actual
  upstream filters remain separate; returned observations must match the original
  selected filters. This handles names such as `ud_ud_greek-gud` and `spoken-like`
  without modifying Svarna or interpreting its error as an empty search.
- Triantafyllidis lookup reads identified `dl` entries and the source's result
  count, including multi-page count labels. It does not infer a lemma by stripping
  Greek endings. Missing entries do not reject dialect vocabulary. Dictionary
  forms, senses and examples remain source text, not executable DS programs.
- Source failures and changed HTML/JSON produce an error, distinct from a
  successful lookup with no matches. Large searches may time out; choose a
  smaller corpus. No automatic model fallback is used.
- Corpus attestation and DS success are separate observations. Most unrestricted
  corpus sentences exceed the current Greek grammar coverage. Their failures do
  not establish ungrammaticality or justify inventing a rule.
- Jev sense ranking/construction classification and Greek lexical expansion are
  future work; this first integration adds retrieval and explicit analysis.

## Greek API and implementation

`src/dylan/research_sources.py` supplies four same-origin workbench endpoints:

| GET endpoint | Options |
| --- | --- |
| `/api/research/databases` | None; public availability information |
| `/api/research/corpora` | `db`: `corpus`, `literature`, `dialectal` |
| `/api/research/search` | `db`, `q`, `kind` (`words`/`regex`), `corpus`, `register`, `mode`, `limit`, `offset` |
| `/api/research/dictionary` | `q`, `scope` (`headword`/`entry`) |

Queries are limited to 160 characters, pages to 50 results (UI: 20), and offsets
to 10,000. Regex requires a corpus filter. Requests use fixed HTTPS services,
verified TLS and no redirects; the browser cannot supply a destination URL.
There are four lookup slots separate from the two parse workers. Reads have a
20-second socket timeout, a checked 25-second elapsed budget, and a 1.5 MB byte
limit. The elapsed check occurs between reads; the browser aborts after 35 seconds.
Only public catalog metadata is cached (five minutes). No credentials, model
calls, database copies, dictionary crawl or automatic persistent corpus import
are involved. Source strings are inserted into the UI with `textContent`.

## Verification

```sh
.venv/bin/python -m pytest -q tests/test_research_sources.py
.venv/bin/python -m pytest -q tests/test_english_sources.py
.venv/bin/python -m dylan.workbench_server --port 8773
python scripts/check_research_browser.py --url http://127.0.0.1:8773 --live --english
```

The browser check first uses controlled source fixtures and the real DS parser:
both semantic modes, source/excerpt preservation, exported provenance, explicit
grammar choice, pagination, missing entries, unavailable sources, safe rendering
of quoted markup, and mobile width. `--live` additionally reads Pontic examples
from Svarna and the published `δίνω` dictionary entry, then transfers an actual
corpus sentence into DS, preserving its source even when parsing fails.
`--english` adds real local Brown/Gutenberg and WordNet lookups, genre/book
filters, pagination/export, source-passage retrieval, explicit edited-text
transfer in all three semantic modes, and language switching. Python tests
also check Brown tagged-source preservation, Gutenberg decoding and offsets,
literal phrase/definition searches, read-only indexes, missing-source errors
and bounded worker behavior.

Sources: [Svarna API](https://greek-corpus-workbench.wonderfulhill-e1c9f1a0.westeurope.azurecontainerapps.io/docs),
[Svarna source](https://github.com/StergiosCha/SVARNA_CORPUS_APP),
[Triantafyllidis](https://www.greek-language.gr/greekLang/modern_greek/tools/lexica/triantafyllides/),
[NLTK data](https://www.nltk.org/nltk_data/), [WordNet](https://wordnet.princeton.edu/).
