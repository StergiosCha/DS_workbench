# Vercel deployment

Public demo: **https://ds-workbench.vercel.app/**

**7 October 2026 PCC correction:** Deployment
`dpl_3Y1wYaPPk27C9syVhDyhZca6Zt8A` restores failed conditional effects before
trying another metavariable binding. `του με έδωσε` stops at the second clitic
with an explicit PCC explanation in both native semantic systems; valid
genitive + third-person accusative clusters remain available. Open-text mode
does not request a lexical repair after this diagnosed constraint failure.
The isolated snapshot `.ds-workbench/vercel-pcc-20261007` changes five files
against the controls deployment below. The final regression run passed 1,888
tests, with four skips. See the
[PCC deployment record](../../data/coverage/pcc-public-2026-10-07.json).

**7 October 2026 controls update:** Deployment
`dpl_75awDHsN99GSe875jqpCESk8JCZG` publishes the visible independent LLM/Jev
checkboxes. The isolated snapshot is `.ds-workbench/vercel-ai-controls-20261007`;
it changes nine interface/control files against the preceding production
manifest. Public browser checks covered all four switch combinations in both
native English backends, visible controls on desktop/mobile, connection,
disconnect, refresh and unsupported grammars. They used real DS parses and a
fixture connection, with no billed inference. See the
[deployment record](../../data/coverage/ai-controls-public-2026-10-07.json).

The DS workbench runs on the `stergios-projects3/ds-workbench` Vercel project.
The account's Hobby plan was verified through the Vercel API before deployment.
This deployment uses Python 3.12, FastAPI, and the Frankfurt (`fra1`) function
region. It needs no Azure container. The local workbench remains available with
its original server and optional model configuration.

## What is hosted

- The existing browser UI and Python DS engine, including native classical,
  constructive and TTR grammars, dialogue, alternative derivations and exports.
- Read-only Brown/Gutenberg indexes and the pinned WordNet index. Source queries
  and edited excerpts retain their original metadata in browser JSON exports.
- Existing Greek source adapters and the Greek grammar evidence. External Greek
  searches still contact their source services.
- Native bilingual paragraph processing, per-sentence failure/context reporting,
  a visible unseen-text coverage baseline and the attributed GDT training lexicon.
  [Paragraph coverage remains incomplete](paragraph-coverage.md).
- Optional OpenRouter connection with each visitor's own key, a searchable
  model selector and current listed token prices. Normal parsing and local
  dictionary searches need no key and make no model calls. No local `.env`,
  API key, proposal cache or decision log is uploaded.

## Connecting models

The **Use analysis LLM** and **Use Jev** checkboxes sit directly below the input,
outside collapsed settings. Both default off. The controls have a direct link:
<https://ds-workbench.vercel.app/#ai-controls>.

Open **Connect / choose models**, paste a key, and press **Connect**.
This checks `/api/v1/key` and reads the authenticated OpenRouter model catalog;
it makes no inference call. The selector lists text models advertising structured
outputs, filtered by that account's provider/privacy settings. Connecting or
selecting a model does not switch on assistance. Tick **Use analysis LLM**, then
build a derivation. Native English and Standard Greek Classical/Constructive
grammars support this bounded assistance: dictionaries/corpus candidates first,
then lexical model proposals and failure-driven retries when needed. The DS
engine compiles approved templates and checks completion. TTR assistance is not
available. The **Missing words only · analysis LLM** strategy remains available
under Advanced for native English missing-vocabulary proposals.

The composer explains the effective settings for the next parse. **Turn off all
AI** unticks both controls and disables vocabulary
AI and Jev search ordering; a connected key is not sent for those requests.
The guide explains LINK modifiers, selected PP arguments, and each semantic
system. Result summaries report actual assistance provenance and model requests.

If the account's catalog includes Jev 1.13, **Use Jev** enables word-meaning
preferences for native English. Jev uses the System One endpoint and a separately pinned model
(`typesafe/jev-1.13-20260917`); the vocabulary selector controls the chat model,
including the lexical fallback. With both boxes ticked, Jev ranks word meanings
and the analysis LLM supplies missing words only. Unticking the analysis LLM
blocks that fallback, including cached generative proposals. Full open-text
construction assistance is available with the analysis LLM on and Jev off.
Search-order preferences keep their existing
per-grammar calibration gates. Connecting does not bypass these gates.

The key lives in a JavaScript closure in the current tab. Successful connection
clears the password input. Disconnect, navigation and refresh clear it; it is not
written to browser storage, cookies, URLs, parser data or exports. Requests send
it in an Authorization header to the same-origin DS backend, which uses it only
to contact OpenRouter. The app stores no key/session on the server. Each parse
gets its own child environment; host provider keys and custom endpoints are
removed. Model proposal caching and decision logging are disabled for these
workers, preventing shared disk retention of visitors' model inputs/results.

Inference is billed by OpenRouter to the supplied key. Prices are the catalog's
base input/output rates, not a total estimate. A connection check cannot promise
that every model/provider will successfully answer every request; unsupported
responses, rate limits and timeouts produce explicit lexical notices. Model
calls retain a 15-second provider limit inside the 30-second parser deadline.

`src/dylan/workbench_asgi.py` adapts the existing endpoints to ASGI. Parser
requests run in separate Python processes so mutable parser state is isolated.
Workers retain a 30-second limit. Streaming uses NDJSON, with a complete final
error frame on timeout or excessive output. A 4 MiB output limit keeps responses
within the host's payload allowance. Two parse slots and four source slots apply
per function instance; Vercel can create additional instances.

Oversized and interrupted workers are killed; stdout is drained during cleanup
so a paused pipe cannot prevent reaping the process. Child interpreters inherit
the runtime's Python import paths, including Vercel's bundled dependencies.
English source workers retain their own 15-second timeout. Static routes serve
only `workbench/`; database files and deployment configuration are not served.

## Preparing and deploying

The deployment is a CLI snapshot, not an automatic deployment from Git.
Files remain in the local working tree until separately committed.

```sh
# Install the optional ASGI dependencies for local checks.
uv sync --extra hosting

# Requires the English/WordNet indexes to have been built already.
.venv/bin/python scripts/prepare_vercel.py

# From the generated .ds-workbench/vercel directory:
vercel deploy --dry --format json
vercel deploy --prod --yes --scope stergios-projects3
```

The staging script copies an explicit set of runtime files into the ignored
`.ds-workbench/vercel/` directory and records a hash manifest. It also installs
the repository's `resources/` folder under `src/dynamicsyntax/resources/`, as
`setup.py` normally does. The package contains about 75 MiB before dependencies,
well below Vercel's standard Python bundle limit. Runtime NLTK is unnecessary.

Templates are in `deploy/vercel/`: the entrypoint, requirements, Python version,
Vercel configuration and upload exclusions. Vercel's local project link lives
under the ignored staging `.vercel/` folder. If linking creates `.env.local`
and `.gitignore`, remove those generated files from the disposable staging
folder before staging again. `.env*` and `.vercel/` are excluded from uploads.
The staging script rejects unexpected files instead of publishing them.

The entrypoint deliberately does not load a local environment file. Corpus
paths resolve to the bundled read-only data. Public requests always require
their own key for model features; server-side credentials cannot supply one.

## Checks

```sh
.venv/bin/python -m pytest -q tests/test_openrouter_connection.py tests/test_workbench_asgi.py tests/test_english_sources.py tests/test_research_sources.py
python scripts/check_openrouter_browser.py --url https://ds-workbench.vercel.app --live
python scripts/check_research_browser.py --url https://ds-workbench.vercel.app --live --english
python scripts/check_readings_browser.py --url https://ds-workbench.vercel.app
```

Use a Python environment with Playwright and Chromium for the browser scripts.
The API tests cover real parsing and streaming in all three semantic modes,
credential isolation, model selection, static-file boundaries, query validation, output limits,
busy responses, and worker termination. Browser checks cover source lookup,
editing and export, grammar selection, alternative playback, Coq, and mobile.
The OpenRouter browser check covers invalid keys, model selection, tab isolation,
disconnect/refresh, credential-free exports and mobile layout. Its opt-in `--live`
mode reads the existing local OpenRouter key and makes two small billed vocabulary
requests using GPT-4.1 mini and DeepSeek V4.1 Flash; credentials are not recorded.

Hobby usage limits still apply, including active CPU time. Reaching the free
quota can pause service. OpenRouter inference billing is separate from hosting.
No paid Vercel upgrade was made.
