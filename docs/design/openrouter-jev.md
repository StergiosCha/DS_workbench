# OpenRouter configuration and current coverage

The workbench supports the user's OpenRouter key for both Jev decisions and
generative lexical proposals. A separate TypeSafe account or key is not
required. Put these settings in the repository's ignored `.env`:

```dotenv
OPENROUTER_API_KEY=your-key
DS_DECISION_PROVIDER=openrouter
DS_LEXICAL_PROVIDER=openrouter
DS_LEXICAL_MODEL=deepseek/deepseek-v4.1-flash
```

The server loads `.env` at startup without evaluating shell expressions.
Existing process variables take precedence. Restart the server after editing
the file. Provider selection is explicit so older Azure endpoint settings do
not take precedence over the user's OpenRouter choice. The public API reports
provider/model configuration but never the key.

## Transport and verification

Jev uses OpenRouter's native `POST /api/v1/systemone`, with `state` and typed
`questions`. The pinned request and response model is
`typesafe/jev-1.13-20260917`. This is the underlying decision model, distinct
from the chat routing service `typesafe/jev-router`. Answer types, option
identities, distributions and the returned model version are validated.
Provider and model identities are included in cache keys and calibration
evidence. Direct TypeSafe remains available with
`DS_DECISION_PROVIDER=typesafe` and `TYPESAFE_API_KEY`.

Verified against the live OpenRouter documentation on 2026-09-30:

- [Jev overview](https://openrouter.ai/docs/guides/community/jev)
- [System One compatibility and model IDs](https://openrouter.ai/docs/guides/community/typesafe-sdk)
- [Reasoning options](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)

`scripts/check_decision_provider.py` performs one explicit connection check.
The local live result returned the pinned Jev model, a valid Choice, 764 ms
latency and USD 0.00002583 cost. This verifies connectivity and response
handling; it is not a DS accuracy or speed calibration.

Lexical proposals use OpenRouter chat completions with a strict JSON schema.
DeepSeek Flash thinking is explicitly disabled for this small structured task.
Response reads are bounded by bytes and elapsed time, including gateway
keepalives. Six live fixtures passed, including intransitive, transitive and
clausal frames, missing arguments, and unsupported `no`. They took roughly
0.9–3.1 seconds each including parsing. These are fixture results, not a
general lexical accuracy measurement. The DS validator still chooses only
existing action templates and preserves each proposed lemma's own predicate.

## Search controls

For contextual vocabulary selection, tick **Use Jev** (`lexical_mode: "jev"`). This is optional
and separate from the search control below. It ranks validated dictionary senses
and frames. Tick **Use analysis LLM** as well to allow a bounded fallback from
your selected model for words missing from the dictionary. Leaving it off sends
`allow_model_fallback: false`, which blocks both fresh and cached generative
proposals. Connecting a key or selecting a model does not tick either box.
See [the lexical-selection measurement](jev-lexical-selection.md) for its contract,
live integration results and accuracy limits.

The UI offers normal DS order, local recording, and Jev preferences. Runtime
preferences remain disabled until measured evidence passes the existing
per-grammar entry/fan-out gates. A working key alone does not enable them.
Local recording makes no model calls and retains deterministic traversal.

The hooks capture the observed prefix, grammar/dialect, pointer, requirements,
lexical evidence and existing continuation trees. They attach ordering priors;
they do not remove candidates. Existing completion heuristics take precedence.
The client supports provider-specific replay keys and an in-request cache.
The end-to-end runner and first measurement are now available; see
`jev-calibration-2026-09-30.md`. It found no search benefit in the current
sample, so no activation gate was enabled. The connection check itself
does not create a calibration gate.

## Offline dictionary

The optional Princeton WordNet 3.0 index supplies English noun senses and
documented verb frames. Build it using `scripts/build_wordnet_dictionary.py`
from the pinned archive described in that script. The source checksum and
Princeton license are retained in the index. Runtime parsing uses local
SQLite and makes no dictionary network calls.

The installed source has 119,034 noun lemmas and 11,531 verb lemmas, including
multiword and unsupported entries; these counts are not parser coverage.
All supported senses/frames are retained. Dictionary mode defaults to no
lexical top-N truncation, while parser work/time caps still apply. Provenance,
synsets, morphology and unmapped frames remain in the result.

Only singular noun and active base/third-person/past verb analyses currently
compile. Recognized plurals and participles remain unsupported morphology.
WordNet does not supply a complete countability or contextual sense analysis;
its noun proposals may overextend the singular-count template. Tense and
agreement are recorded but not enforced. Dictionary candidates, model
proposals, parser success and independently sourced grammaticality judgments
remain separate.
