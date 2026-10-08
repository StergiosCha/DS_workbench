# Extending a grammar

## First extension without changing the installed package

Run this from a checkout, or run the same script with the Python interpreter
of an installed wheel:

```sh
uv run --no-sync python examples/community/extend_grammar.py --output /tmp/my-ds-extension
```

Choose a new output directory. The script copies both native English grammars
using `importlib.resources`, adds the predicate `dance : human → Prop` (or
`e → t` in Classical composition) to each semantic signature, and adds these
lexicon rows:

```text
dances intransitive dance human
dance intransitive-base dance human
```

The existing templates build the argument/functor nodes; no LLM or new parser
operation is needed. The semantic compiler for the chosen backend supplies
its own formula/type representation. This is a lexical extension using
existing constructions, not a claim to have implemented a new syntax family.

Twelve checks exercise both backends: two names, negation, a nonrestrictive
relative and two incomplete/extra-argument contrasts. In particular:

```text
John dances.                         → dance(john)
John does not dance.                  → ¬(dance(john))
John, who Mary knows, dances.         → (dance(john) ∧ know(mary, john))
John dances Mary.                     → no complete derivation
John dances because.                  → no complete derivation
```

The script checks exact meanings and absence of search caps, and writes
`results.json` with version, grammar-file hashes, inputs and outcomes. These
are authored engineering probes, not newly elicited grammaticality judgments.
It does not alter installed files and refuses to overwrite an existing folder.

Load your copy through the public API:

```python
from pathlib import Path
from dynamicsyntax import parse

result = parse("Mary dances.", Path("/tmp/my-ds-extension/2026-english-mltt"),
               strict=True, top_n=0, trace=True)
print(result.semantics)
```

`top_n=0` matters: the public API's default of three lexical alternatives can
prune needed punctuation/construction entries. It does not remove parser search
caps. The browser's grammar selector currently lists registered bundled
grammars; custom local folders are supported through Python, not uploaded
through the public web server. Registering a new browser grammar also requires
configuration/example changes in `workbench_api.py` and possibly
`greek_workbench.py`, with frontend/configuration tests.

## Implement a construction family

Start from a topic in the [theory catalogue](../research/ds-theoretical-coverage.md)
and fill the [design template](construction-template.md). A lexical LLM can
instantiate permitted frames; it cannot supply an unimplemented binding,
scope or LINK-composition rule. Implement the family with its applicability
conditions, not a special case for one sentence.

The nonrestrictive-relative extension provides a worked implementation trail:

| Layer | File and responsibility |
| --- | --- |
| Analysis and limits | `docs/design/nonrestrictive-relatives.md`: source locators, matrix named hosts, excluded embedding/quantification, composition assumptions. |
| Lexical/computational programs | `scripts/build_nonrestrictive_extensions.py`: opening/closing punctuation, relativizer, completion-time evaluation. |
| Tree operations | `src/dylan/action/atomic/nonrestrictive_effects.py`: LINK growth, head copying, unresolved requirements, closure and applicability guards. |
| Effect dispatch | `src/dylan/action/atomic/effect_factory.py`: explicit effect names; no evaluation of arbitrary model code. |
| Semantics | Native semantic terms/profile, with distinct Classical and Constructive composition; verify formula scope and witness closure. |
| Tests | `tests/test_nonrestrictive_relatives.py`: exact meanings, identity/role, modifiers, traces, local indefinites, negative boundaries and Constructive Coq checks. |
| App integration | `workbench_api.py` examples and `workbench/app.js` coverage wording. |

Both existing generators and new lexical templates are inspectable text/code.
Reuse a primitive when its semantics matches; introduce a new one only when
its preconditions and effects are explicit. A LINK edge by itself does not
determine whether the result is conjunction, restriction or discourse attachment.
Test pointer return, head identity, local requirements and final composition.

## Where changes belong

| Area | Main locations |
| --- | --- |
| Public API / result | `src/dynamicsyntax/_parse.py`, `_session.py`, `parse_result.py` |
| Parser/search/context | `src/dylan/parser/`, `dag/`, `tree/` |
| Atomic DS operations | `src/dylan/action/atomic/` |
| Native semantic compilers | `src/dylan/formula/mltt/` (contains shared terms and both native backends despite its directory name) |
| TTR | `src/dylan/formula/ttr*`, record/path/freshening operations and separate TTR grammars |
| Grammar files | `src/dynamicsyntax/grammars/`; inherited resources also under `resources/` |
| Everyday, PP, dialogue, finite connective families | `scripts/build_everyday_extensions.py`, `build_pp_extensions.py`, `build_dialogue_extensions.py`, `build_causal_extensions.py` |
| Lexical/model assistance | `lexical_expansion.py`, `lexical_provider.py`, `assisted_parsing.py`, `construction_assistance.py` |
| Jev preferences / comparison | `lexical_selection.py`, `jev_comparison.py` |
| Server and workers | `workbench_server.py`, `workbench_asgi.py`, `workbench_api.py`, `workbench_paths.py` |
| Browser | `workbench/index.html`, `app.js`, `styles.css`, `research.js`, `openrouter.js`; no Node build |

`dylan.*` is implementation code, not a stable plugin ABI. Prefer the public
API and independent grammar directories for downstream experiments. Threaded
concurrent parsing in one process is unsafe without addressing shared mutable
meta state; the servers isolate parse requests in subprocesses. Preserve that
boundary when hosting or doing parallel batch work.

## Validate and publish the change's evidence

Run strict loading and the affected tests, then inspect a full trace. For a
shared rule change, run the broader [corpus checks](../coverage/README.md).
Regenerate grammars and confirm a second generator run makes no changes.
Keep model-off checks separate from live-provider checks. Record unsupported
backends and source/context assumptions in the design document and app wording.

Do not promote a source example to a grammaticality gold label merely because
it now completes. Do not adjust coverage floors to hide a regression. New
phenomena need semantic expectations, relevant contrasts and held-out checks;
extending a hand-written test set does not establish open-text accuracy.
