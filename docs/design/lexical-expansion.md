# Template-based lexical expansion

The workbench can extend the two native English lexicons before parsing. A new
surface form selects an existing lexical action template and supplies its semantic
symbol and argument sorts. The parser executes that template's actual make/go/put
program; both the action trace and the growing tree remain backend output.

## Run and inspect

```sh
.venv/bin/python -m dylan.workbench_server --port 8769 --lexical-model DeepSeek-V4-Flash
```

The model argument is a deployment name on Azure, or a model ID on an
OpenAI-compatible service. It may also be set with `DS_LEXICAL_MODEL`.
Azure reads `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and optionally
`AZURE_OPENAI_API_VERSION` (default `2024-10-21`). Otherwise the adapter reads
`OPENAI_API_KEY` and optionally `DS_LEXICAL_BASE_URL` (default
`https://api.openai.com/v1`). Credentials and endpoints are server configuration;
the browser cannot supply or retrieve credentials. Public configuration returns
only provider, model and availability. HTTPS uses certificate verification and
the certifi trust bundle in addition to the system trust store.

Open **Expand the vocabulary** to choose:

- **Original lexicon**: identical vocabulary to the shipped grammar.
- **Original + bundled extension**: an explicit, small inflection table for
  cat/child/teacher/student/book/letter, sleep/run/laugh/smile/greet/admire/read/
  write/see, Alice and red. This is not a learned or wide-coverage dictionary.
- **Original + extension + model proposals**: remaining unknown English
  open-class forms are proposed in one structured model request. The input text
  is included to disambiguate lexical senses. The result panel shows each added
  analysis, its provenance, validation and the instantiated DS program.

When a model is configured, the workbench starts in model mode; otherwise it starts
with the bundled extension. The collapsed control displays the active source.

Examples: `a cat sleeps.`, `every teacher greets a child.`, `mary reads a book.`
An uncached model example is `a cat purrs.`. Added entries are available to all
turns in a submitted dialogue and are instantiated separately in classical and
constructive modes. Shipped grammar files are never modified.

## Proposal contract

Each entry has exactly `surface`, `lemma`, `template`, `symbol`, `domains`,
`morphology`, and `evidence`. The allowed templates are:

| Template | Domains | Morphology | Declaration |
| --- | --- | --- | --- |
| proper | nominal sort | invariant | constant |
| noun | existing parent sort | singular | new nominal sort |
| adjective | object | invariant | unary predicate |
| intransitive | subject sort | finite | unary predicate |
| transitive | subject, object sorts | finite | binary predicate |
| clausal | subject sort (Content supplied by template) | finite | subject → Content → proposition |

The validator checks the whole batch before installing it. It rejects unknown
templates, code/formula injection through parameters, undeclared types, conflicting
declarations, reserved symbols and variable names, incompatible morphology fields,
duplicate entries, and attempts to overwrite existing words. Symbols must preserve
the lemma, optionally with a sense/frame suffix. Invariant/singular entries retain
their surface lemma; regular finite `-s` forms are checked against their proposed
lemma to reject synonym substitution such as `believes → think`. Nouns can supply sorts
used by another entry in the same batch. At most three analyses per surface form
are retained; normal DS search chooses between them. This supports distinct frames
and senses without globally changing the meaning of a verb.

Existing words, parser repair controls and an explicit English closed-class list
are protected. The prompt also excludes other function words. The finite list and
the prompt are not an independent POS oracle: a model can still misclassify a word
or invent a plausible but incorrect sense. **Validation establishes that an entry
fits a template, not that its linguistic analysis is correct.** Morphology fields
are compatibility declarations with the limited identity checks above; there is no
complete morphological analyser or agreement checker yet. The explicit bundled
inflections avoid heuristic suffix stripping.

Nominal declarations preserve the existing semantic distinction: classical DS
composes e/cn/t and epsilon/tau terms, while constructive DS composes nominal types
and Sigma/Pi terms. `a stone sleeps.` therefore fails constructive animal-domain
application, but has a classical e/t derivation. This difference is intentional;
the classical system does not acquire constructive selectional typing.

## Failure, caching and limits

One provider call handles at most eight unknown forms, with at most 24 analyses,
a 15-second connection/read timeout and a bounded response. The existing worker
deadline remains 30 seconds. There is no automatic model retry to obtain a parse.
The official structured-output request format is documented at
<https://developers.openai.com/api/docs/guides/structured-outputs>.

Provider failure, refusal or invalid output leaves the original and bundled
entries usable. Unknown words retain the `lexicon_gap` diagnosis; rejected model
output is reported separately. A complete model-assisted derivation carries no
new grammaticality judgment. The existing sourced Greek placement judgments stay
independent of parser outcomes.

Validated proposals, including empty proposals, are cached in
`.ds-workbench/lexical.sqlite3` (override with `DS_LEXICAL_CACHE`). Keys include
token context, grammar text, semantic theory, provider endpoint, model and schema
version. Cached proposals are revalidated and retain their original source and
timestamp. The cache holds at most 500 requests and is gitignored. Context hashes,
proposal entries and source explanations are stored, not credentials or the full
input transcript. Cached entries are experimental proposals, not globally trusted
lexical facts; cache failure does not prevent parsing.

Greek and TTR expansion are **not implemented**. Their original lexicons and
placement constraints continue to run; the UI disables expansion for them.

## Model choice and evaluation

Start with a smaller model for routine lexical analysis. The current Azure
resource has both DeepSeek-V4-Flash and gpt-6-astra deployments. The adapter takes
one configurable model; it does not silently route to a more expensive model.
An Astra review route should be added only after measuring which ambiguous frames
or senses the smaller model misses. Multiple agreeing models are not linguistic
evidence. Frame annotation and negative tests are more informative than a higher
parse-completion rate alone.

Deterministic tests cover both semantic backends, tree structure, Coq declarations,
type rejection, atomic validation, alternative frames, context-specific caching,
dialogue, failure handling, closed classes and the unchanged Greek constraints.
The browser test checks the controls, lexical-program inspector and mobile layout.

Optional live evaluation (uses the named deployment and server credentials):

```sh
.venv/bin/python scripts/check_lexical_provider.py --model DeepSeek-V4-Flash
```

It records every proposal and checks lexical frames as well as completions,
including a missing-object case and an unsupported quantifier. Five examples are
a connection/behaviour smoke test, not a model-quality benchmark.

On 25 September 2026, the five live Flash checks passed with the constrained domain
inventory (1.5–4.1 seconds per request). An earlier unconstrained-schema run rejected
one invented argument sort; constraining the provider schema fixed that observed
case without loosening backend validation. This is evidence for the integration,
not a broad accuracy claim. Full-suite validation at this step: 504 passed, three
skipped, the existing environment-dependent LaTeX smoke test deselected. After a
bundled-vocabulary limit fix, all 46 lexical-expansion tests passed (including two
additional cases). Browser checks, including the live provider, pass with zero
console errors. Add `--live-lexical` to
`scripts/check_workbench_browser.py` to exercise model proposals and cache reuse
through the frontend as well.

The subsequent [clause embedding step](clause-embedding.md) adds the `clausal`
template and the live `john believes that a man walks` check. The provider schema
continues to offer nominal subject sorts only; it cannot invent or alter the
Content argument, the clause-closure program or complementizer entries.

## Next grammar work

This layer increases lexical coverage within the existing constructions. It does
not make the parser wide-coverage by itself. The next changes need independent
grammar programs and corpus tests:

1. Case-bearing Greek full DPs, contextual reference and typed locally unfixed
   nodes. Use these to implement scrambling and LINK-based clitic left dislocation
   with explicit identification constraints; test clitic placement and PCC on both
   licensed and excluded cases.
2. Additional quantifiers with separate classical and constructive meanings.
   Singular existential/universal variants can reuse established programs;
   negation, cardinality and proportional quantifiers require more semantics.
   Do not label every determiner as existential merely to fill a vocabulary gap.
3. Recursive finite complements are now implemented, with optional `that` and
   explicit local closure. Next are relatives and adjunct clauses, with independent
   tests of long-distance dependencies and locality; intensional semantics and
   cross-clause scope require separate semantic work.
4. A morphology lexicon/analyser for inflections, case, agreement and dialect;
   corpus-backed lexical review; context substitution for anaphora, clarification
   and dialogue fragments; search/beam instrumentation as ambiguity grows.

Track vocabulary coverage, supported constructions, semantic correctness and
overgeneration separately. Preserve rejected minimal pairs while adding licensed
sentences; distinguish resource limits from absent derivations and do not equate
an uncovered construction with ungrammaticality.
