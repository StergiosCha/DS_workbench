# Claude Fable: deep DS research, library expansion and implementation audit

Prepared for this checkout on 7 October 2026. Copy everything below the divider into Claude Code, or ask it to read and execute this file. Paths below are relative to the repository unless absolute.

---

You are working on **DS Workbench**, a research and teaching application built on the Python `dynamicsyntax` package. Carry out a substantial, source-verified investigation of Dynamic Syntax literature, expand our existing research library, and connect the findings to the actual implementation. The result must help the wider DS community understand, use and extend this system.

**Repository:** `/Users/graogro/Dropbox/revisiting-formal-semantics/DynamicSyntax`

**Public application:** https://ds-workbench.vercel.app/

**Existing local PDF archive:** `/Users/graogro/Dropbox/NeSy_linguistics/frameworks/dynamic_syntax/`

Work in the repository with access to its files, terminal and web research tools. If you only have a web-research environment, state that limitation, produce the source review, and mark code findings as unverified until you can inspect the checkout. Never claim to have read files, executed tests or changed the application without doing so.

## 1. Purpose and deliverables

Answer these connected questions:

1. What has DS actually covered theoretically, empirically and computationally, across languages and semantic frameworks?
2. Which works are missing from our library, and which existing entries need deeper reading or bibliographic correction?
3. Which published analyses have executable counterparts here, which are our adaptations, and which are absent, incomplete or defective?
4. What reusable mechanisms would increase coverage across construction families, especially English and Greek?
5. What can a community contributor implement next, with exact source passages, code locations, expected meanings and tests?

Deliver an expanded, validated library; source-located analysis cards; a code-grounded research report; and a prioritized implementation backlog with a complete specification for its first bounded slice. Research and documentation changes are part of this task. Treat parser implementation as a separately identified next work item, rather than silently rewriting the engine during bibliography work.

Do the research and update the artifacts. A proposed search strategy alone is not the deliverable. Preserve partial findings and unresolved sources honestly if access or time limits intervene.

## 2. Orient yourself before searching

Inspect `git status --short`, applicable repository instructions and current files. This checkout contains substantial uncommitted work, including untracked files. Preserve it. A fresh upstream checkout will omit local work.

Read these in order:

1. `README.md`, `HANDOVER.md` and `CONTRIBUTING.md`.
2. `docs/research/library/README.md` and the editable library JSON files listed below.
3. `.claude/handover/2026-10-07-ds-library.md`, `.claude/handover/2026-10-07-ds-literature-and-relatives.md` and `.claude/handover/2026-10-07-pcc.md`.
4. `docs/research/ds-theoretical-coverage.md` and its JSON catalogue.
5. `docs/workbench-walkthrough.md`, particularly the foundation, semantic backends, AI, PP, coverage, backend, programming and forward-plan sections.
6. `docs/community/README.md`, `using.md`, `extending.md`, `construction-template.md` and `maintaining.md` in that directory.

Then inspect the relevant source code and tests. Earlier handovers and `docs/design/maps/` are navigation aids, not reliable statements of current behavior: some maps describe defects that have since been fixed. Recheck claims against current code and execution. The live deployment and working tree are different snapshots; report which one you inspected.

## 3. Existing library: extend its structure

The starting edition has **35 selected works, 15 fingerprinted PDF versions, five bounded analysis cards, and 18 categories containing 91 tracked topics**. These numbers are a dated baseline; recompute them. The works have mixed reading depths, including 17 citation-only entries. Ninety-one topics does not mean ninety-one implemented or fully reviewed analyses.

| File | Purpose |
| --- | --- |
| `docs/research/library/papers.json` | Canonical work metadata, reading status, facets, source versions and next actions. |
| `docs/research/library/analyses.json` | Bounded claims with source locators, examples and separate implementation states for each backend. |
| `docs/research/library/taxonomy.json` | Controlled facets, review states and browsing collections. |
| `docs/research/library/discovery.json` | Search provenance, candidate records, screening decisions and unresolved leads. |
| `docs/research/library/library-template.html` | Source for the offline browser. |
| `docs/research/library/index.html` | Generated searchable library. |
| `docs/research/library/ds-library.bib` and `ds-library.csl.json` | Generated reference-manager exports. |
| `docs/research/library/validation.json` | Dated checks and artifact hashes; refresh accurately after changes. |
| `docs/research/ds-theoretical-coverage.json` | Existing category/topic IDs and source-to-implementation inventory. |
| `docs/research/ds-source-artifacts.json` | Original 13 source-version fingerprints; newer versions also occur in `papers.json`. |
| `scripts/build_ds_library.py` | Validates references and generates HTML/BibTeX/CSL. |
| `scripts/check_ds_library_browser.py` | Offline browsing, filtering, export and mobile checks. |

Keep stable IDs and provenance. Extend the controlled vocabulary only when a new distinction is justified. Keep discovery candidates separate from admitted works. Preserve the four entities **work → inspected version → bounded analysis → implementation**.

An earlier bounded Crossref search returned 150 records, of which 25 matched an exact title phrase. Eight are now catalogued, four were excluded, and 13 remain unresolved. Screen that queue, then search beyond it. Many relevant DS works do not put “Dynamic Syntax” in their title.

## 4. Conduct the deep search

Use primary publisher pages and papers, ACL Anthology, institutional repositories, theses, author bibliographies, and the DS community bibliography where accessible. Use Crossref, OpenAlex, Semantic Scholar and general search to discover and corroborate records, not as substitutes for reading the argument. Record which services were actually used and any access failures. Follow references backward and citations forward from the core works. Search through the current date without inventing forthcoming publications.

Search by constructions, mechanisms, authors and language names as well as framework names. Useful combinations include Dynamic Syntax with LINK/modification, underspecification, Introduction/Prediction, unfixed nodes/MERGE, ellipsis/action reuse, incremental generation, dialogue repair, clitic placement/PCC, scrambling, clefts, auxiliaries, conditionals, TTR, dependent types, vector semantics and grammar induction. Exclude unrelated programming-language “dynamic syntax” results with recorded reasons.

Use the existing stable IDs to start these reading batches; retrieve exact metadata from `papers.json`:

| Batch | Seed works and questions |
| --- | --- |
| Foundations | `KMW01`, `CKM05`, `HG21`, supporting `BMV94`: tree logic, requirements, lexical/computational actions, Introduction, Prediction, LINK, MERGE, completion and context. |
| Semantic architectures | `C25` Constructive DS; `PEH11`, `E15`, `ECH13` for DS–TTR; `CL25` for TTR-DS; `SPHK18` and `KV19` for vector semantics. Separate formal definitions, proposals and implemented results. |
| Immediate construction gaps | `M02` and `C17` on modification/underspecification; `CA11` on English auxiliaries; `G06` on conditionals. Find the actual mechanisms and semantic commitments before proposing code. |
| Interaction and ellipsis | `CKP07`, `PGMC10`, `H14`, `KC16`, `GK16`, `KE19`, `HE17`, `HE21`: strict/sloppy reuse, split utterances, person shifts, repair, feedback, grounding and contextual accessibility. |
| Languages and variation | `C10`, `CK11`, `KK10`, `GI12`, `GI16`, `SG16`, `SE13`, `SE21`, `NC21`, `B08`: Greek varieties, Japanese, Rangi, Kazakh, Spanish and languages found through citation chains. |
| Computational evidence | `PEH11`, `EPH13`, `ECH13`, `H14`, `SPHK18`: parser/generator/learning architecture, available code, datasets, evaluation units and reproducibility. |

Cover all existing category families: core growth; nominals/quantification; valency/copulas; word order/case; relatives/extraction; modification; coordination; anaphora/binding; clitics/PCC; auxiliaries/situations; clause linkage; ellipsis; interaction; information structure; agreement/typology; diachrony/variation; learning/search/generation; semantic architecture. An absence of located evidence should be recorded as a search gap, not as proof that DS has no analysis.

For every substantive claim record the identified work, inspected version, printed page, physical PDF page where different, section/example number, and a short supporting quotation or precise paraphrase. Preserve language, variety, speaker/context assumptions and the source's limits. Separate an author's account from a competing account and from our proposed adaptation. Inspect formulas and diagrams visually when extracted text loses notation.

Do not pad the library to reach a target count. Prioritize primary-source depth and missing families. Report admitted works, upgraded readings, exclusions and unresolved leads separately.

## 5. Bibliographic and source cautions already established

- `KMW01`, *Dynamic Syntax: The Flow of Language Understanding*, and `CKM05`, *The Dynamics of Language: An Introduction*, are different books.
- The local CKM05 PDF is a final draft dated 12 December 2004 of the 2005 work. Its pagination must not be attributed automatically to the published book.
- The local ellipsis preprint has a 2016 draft date; the chapter's publication metadata is 2019, with some references using 2018. Preserve the version distinction.
- `KV19`, *Why Natural Language Models Must Be Partial and Shifting: A Dynamic Syntax with Vector Space Semantics Perspective*, is real. The exact title and seven authors are listed as contributed presentation 5 on p. 3 of https://aclanthology.org/W19-09.pdf. That public workshop document contains a one-paragraph abstract; our local archive has a separate two-page contribution. Do not describe the public document as the two-page paper. The library entry now records this distinction.
- `CL25`, Cooper and Larsson (2025), *Dynamic Syntax in a Theory of Types with Records*, DOI https://doi.org/10.3390/languages10120300, explicitly distinguishes TTR-DS from earlier DS–TTR. Inspect §§1–3 and §§4.8–5 before drawing architectural conclusions. Its discussion does not establish that this workbench implements TTR-DS.
- `EPH13` and `ECH13` are distinct induction studies with different semantic representations and evaluation conditions. Do not combine their results or identify our LLM template proposals with their learning algorithms.
- Several previously located cloud files were zero-byte placeholders. Check PDF readability and content, not just filenames. `/tmp/ds-literature-2026-10-06/` and `/tmp/ds-library-CL25.pdf` may contain previous downloads; temporary paths are optional caches, not permanent references.

Use DOI/ISBN/author-title matching and explicit version relationships. A missing DOI does not make a work fictitious. A plausible title or local filename does not verify a venue. Record metadata-only or abstract-only status when that is all you inspected. Preserve source access/reuse conditions; do not redistribute the local PDF archive as part of the library.

## 6. Understand the software foundation and three backends

This checkout extends the **`dynamicsyntax` Python package**, a Python port of DyLan. It reuses and develops tree growth, the action interpreter, context DAG and incremental parser. The public Python namespace is `dynamicsyntax`; most engine code is under `dylan`. Establish inherited behavior versus later extensions from repository history, documentation and tests. Use the package/project name when explaining provenance; the user removed personal upstream credit lines from the presentation.

Classical and Constructive grammars use separate native semantic compilation paths. Shared native code happens to live under `src/dylan/formula/mltt/`; that directory name does not mean every class there is exclusively Constructive. The inherited TTR implementation has its own record-type machinery and grammar resources. A common parser does not establish common linguistic coverage.

For each proposed extension distinguish:

- **Classical:** term structure, binding, epsilon/tau commitments, scope and referent identity.
- **Constructive:** dependent types, Sigma/Pi structure, witnesses, dependencies, scope and accessibility; identify our adaptations explicitly.
- **DS–TTR:** record fields, paths, event/referent identity, freshening, merge and subsumption. Audit the existing port independently.
- **TTR-DS:** the additional proposal to represent DS tree descriptions, states and parsing actions themselves in TTR. It is not another name for our TTR output option.

Do not manufacture backend parity by relabeling a formula or translating only a final display string. Type checking, Coq export and DS completion have specific formal scopes; none independently proves that an interpretation is linguistically correct.

## 7. Code navigation map

Trace at least one real parse from the UI/request through tokenization, grammar loading, lexical choice, computational actions, tree/context update, semantic composition and the returned trace. Then inspect the paths relevant to each analysis card.

| Area | Files/directories to inspect |
| --- | --- |
| Public API and grammar resolution | `src/dynamicsyntax/__init__.py`, `_parse.py`, `_session.py`, `parse_result.py`, `parse_trace.py`. |
| Incremental parser and search | `src/dylan/parser/interactive_context_parser.py`, `dag_parser.py`, `parse_stats.py`; `src/dylan/dag/`, especially `word_level_context_dag.py`. |
| Tree, labels and modalities | `src/dylan/tree/tree.py`, `node.py`, `label/`; inspect address, requirement and modality handling in this directory. |
| Actions and grammar loading | `src/dylan/action/grammar.py`, `lexicon.py`, `lexical_action.py`, `computational_action.py`; `atomic/effect_factory.py`, `if_then_else.py`, `make.py`, `merge.py`, `put.py`, `delete.py`, `beta_reduce.py`; metavariable machinery under `action/meta/`. |
| Native meanings | `src/dylan/formula/mltt/terms.py`, `semantics.py`, `coq.py`; `src/dylan/action/atomic/semantic_effects.py`. |
| TTR meanings | `src/dylan/formula/ttr_record_type.py`, `ttr_formula.py`, `ttr_field.py`, related path/formula classes; `src/dylan/action/atomic/ttr_fresh_put.py`. |
| Native finite clauses | `src/dylan/clause_inventory.py`, `construction_assistance.py`; `src/dylan/action/atomic/causal_effects.py`. |
| Relatives and dialogue meanings | `src/dylan/action/atomic/nonrestrictive_effects.py`, `native_dialogue.py`; `src/dylan/dialogue_workbench.py`. |
| Greek and paragraph orchestration | `src/dylan/greek_workbench.py`, `paragraph_workbench.py`; tokenization in `src/dylan/nlp/types.py`. |
| Lexical candidates and AI retries | `src/dylan/lexical_dictionary.py`, `lexical_expansion.py`, `lexical_provider.py`, `assisted_parsing.py`, `openrouter_connection.py`. |
| Greek corpus and live evidence | `src/dylan/greek_lexical_dictionary.py`, `greek_lexical_evidence.py`, `research_sources.py`; `data/greek-lexicon/README.md`. |
| English source investigation | `src/dylan/english_sources.py`, `research_sources.py`; WordNet builder below. |
| Jev preferences and search | `src/dylan/lexical_selection.py`, `jev_comparison.py`, `decision/`, including provider, ranking, gates, state and logs. |
| Learning/generation inheritance | `src/dylan/induction/`, `src/dylan/parser/language_derivation.py`; inspect callers and tests to establish what is executable. |
| HTTP and result serialization | `src/dylan/workbench_api.py`, `workbench_server.py`, `workbench_asgi.py`, `workbench_readings.py`, `workbench_environment.py`, `workbench_paths.py`. |
| Current browser application | `workbench/index.html`, `app.js`, `styles.css`, `openrouter.js`, `research.js`. Plain frontend assets, no Node build required. Distinguish this from older `web/` experiments. |
| Packaging/hosting | `pyproject.toml`, `setup.py`, `MANIFEST.in`, `.github/workflows/`, `deploy/vercel/`, `scripts/prepare_vercel.py`; consult community maintainer docs. |

Grammar sources are under `src/dynamicsyntax/grammars/`: native `2026-english-classical`, `2026-english-mltt`, and Classical/MLTT pairs for SMG, Cypriot, Pontic and Grico; inherited TTR includes `2015-english-ttr`. Inspect the actual available directories and aliases. Review `computational-actions.txt`, `lexical-actions.txt`, `lexical-macros.txt`, `lexicon.txt` and native `semantics.json`. Historical copies also occur under `resources/`; establish which files the loader uses.

Generators include `scripts/build_everyday_extensions.py`, `build_pp_extensions.py`, `build_dialogue_extensions.py`, `build_causal_extensions.py`, `build_nonrestrictive_extensions.py`, `build_greek_fragments.py`, `build_greek_lexicon.py`, `build_wordnet_dictionary.py` and `sync_grammars.py`. Read their behavior before running them: some regenerate shared resources. Identify the source of truth for each proposed grammar change.

Shared mutable metavariable state makes threaded concurrent parsing in one process unsafe without further work; current servers isolate parse requests in subprocesses. Inspect rollback and cloning carefully. Grammar loaders may skip malformed entries; a grammar appearing in a selector is not evidence that every entry loaded correctly.

## 8. Existing behavior and regressions to preserve

Consult the relevant `docs/design/` documents and tests instead of assuming the old screenshots describe today's code:

| Topic | Design and verification entry points |
| --- | --- |
| Semantics/core | `native-semantics.md`, `constructive-ds-design.md`, `loft-engine-status.md`; `tests/test_native_semantics.py`, `test_loft_engine.py`, `test_formula_hashing.py`, `test_ttr_referent_identity.py`. |
| Greek clitics and PCC | `greek-clitics.md`, `thesis-clitic-system.md`, `thesis-full-system.md`; `tests/test_pcc.py`, `test_clitic_restrictions.py`, `test_greek_workbench.py`, `test_greek_ditransitive_expansion.py`. |
| PP arguments, modifiers and similes | `pp-and-revision.md`; `tests/test_pp_similes.py`; `scripts/check_pp_revision_browser.py`; handover `2026-10-03-pp-similes.md`. |
| Embedding and relatives | `clause-embedding.md`, `restrictive-relatives.md`, `nonrestrictive-relatives.md`; `tests/test_clause_embedding.py`, `test_relatives.py`, `test_nonrestrictive_relatives.py`. |
| Clause relations | `causal-clauses.md`, `construction-assistance.md`; `tests/test_causal_clauses.py`, `test_clause_constructions.py`. |
| Nominals and everyday constructions | `tests/test_common_noun_dp.py`, `test_plural_quantification.py`, `test_copular_predication.py`, `test_everyday_constructions.py`. |
| Dialogue and paragraphs | `dialogue.md`, `paragraph-coverage.md`; `tests/test_dialogue_workbench.py`, `test_dialogue_repair.py`, `test_native_dialogue_questions.py`, `test_paragraph_workbench.py`. |
| AI and Jev | `assisted-open-text.md`, `lexical-expansion.md`, `jev-lexical-selection.md`, `jev-comparison.md`, `openrouter-jev.md`; corresponding assisted parsing, lexical selection, Jev comparison and decision replay tests. |
| Sources during parsing | `svarna-lexical-integration.md`, `corpus-dictionary.md`; `tests/test_greek_lexical_evidence.py`, `test_research_sources.py`, `test_english_sources.py`. |

All design filenames in that table are under `docs/design/`; bare test filenames are under `tests/`.

Important checks:

- In the maintained SMG clitic reading, **`του με έδωσε` must not receive a complete derivation**. The latest fix restores the tree before retrying failed conditional branches, preventing a spurious nested unfixed node. Positive controls include `του το έδωσε` and `της τον έδωσε`. Preserve argument identity and distinguish a PCC explanation from a generic failure. Do not generalize the SMG restriction to all dialects.
- A TTR referent-identity bug was fixed. Recheck subject/object distinction, deliberate coreference, field freshness and paths; completion alone would not catch collapsed referents.
- The native nonrestrictive fragment has bounded named-head support. Inherited TTR relative entries do not establish equivalent supplemental meaning or projection.
- Inspect PP implementations for the actual distinction between selected arguments, LINK modifiers and similes. Do not assume every PP has the same structural analysis, or cite a general DS account as proof that our chosen implementation follows it.
- Introduction/Prediction must be traced to actual rules and behavior. Distinguish formal structural prediction from a model predicting a likely word or choosing a sense.
- Finite clause templates distinguish cause, time, condition, concession and contrast. These labels do not supply full tense/aspect, causal reasoning, counterfactual semantics or all published conditional analyses.
- Failed paragraph sentences remain gaps. Speaker-sensitive dialogue, repair and shared completion need context-sensitive expected meanings, not flattened sentence tests alone.

## 9. AI boundaries and evidence

Users must be able to see what DS does without AI. Current visible LLM and Jev controls are independent and default off; connecting a key is not permission to enable either. Preserve those controls and request provenance.

The generative model can propose vocabulary and declared finite-clause template instances; the DS engine constructs and checks derivations. Jev can supply contextual lexical preferences and, separately, optional search ranking. Neither is a proof of linguistic correctness. Normal DS ordering with Jev search off can coexist with Jev lexical preferences: distinguish the controls and actual calls.

Inspect the controlled Jev comparison with identical lexical candidates. The earlier “John lends a book to Mary” demonstration changed a dictionary sense after later context; it is an illustrative comparison, not an accuracy benchmark. Keep failed, uncertain, cached and unchanged decisions visible. The selected vocabulary model and pinned Jev model are separate.

TTR assistance is currently not provided by the native assistance paths. Treat any proposed TTR extension as new work. WordNet and GDT frames are hypotheses, not exhaustive valency descriptions. Live Svarna/Triantafyllidis evidence can inform Greek proposals, but browsing a corpus is not grammar training or automatic verification of a DS analysis. Check actual integration code and source provenance.

Keep API keys out of reports, screenshots, exports and logs. Offline research and parser checks should not require model calls; record any live calls actually used and distinguish them from fixtures.

## 10. Turn readings into implementation-ready cards

For each high-priority bounded analysis, supply:

1. Work/version IDs and exact passages; the claim's scope and any competing accounts.
2. Language/variety, discourse setting, source examples with judgments, and separately labeled authored controls.
3. Required DS mechanism and incremental sequence: initial requirements, lexical/computational actions, intermediate tree states, LINK/unfixed/MERGE behavior and completion conditions.
4. Expected semantic representation, argument roles, identity, binding, scope, accessibility and strict/sloppy or restrictive/supplemental contrasts where relevant.
5. Separate Classical, Constructive and TTR obligations and evidence states; distinguish TTR-DS research from the existing backend.
6. Exact existing code/grammar/test locations; classify the gap as vocabulary, construction, engine operation, semantics, context, search/resource limit or UI reporting.
7. Positive and negative tests, meaning-sensitive assertions, incremental traces and interaction with existing constructions. Include failure cases that a shallow workaround would incorrectly accept.
8. Dependencies, a bounded first implementation, excluded cases and a measurement plan.

Rank the backlog by source readiness, reusable mechanism, practical coverage, semantic risk, dependency cost and reviewability. Investigate the existing queue: Greek relatives, broader English relatives/projection, strict/sloppy ellipsis, nominal coordination/possessives, event/situation semantics and auxiliaries/voice, questions/answers and agreement. Revise priorities when the evidence warrants it. Avoid expanding a construction solely by adding surface words to the lexicon.

Choose the first slice from that evidence, and make its specification actionable without this conversation. Do not promise unrestricted paragraph coverage from a small collection of examples.

## 11. Verification and output

Use the existing environment where possible. From the repository root:

```sh
.venv/bin/python scripts/build_ds_library.py
.venv/bin/python scripts/build_ds_library.py --check
.venv/bin/python -m dylan.workbench_server --port 8769
```

Run the server only when needed for UI/API inspection. The offline library can be opened directly. `README.md` documents clean installation using `uv sync --locked --python 3.12`. Browser scripts require a Python environment with Playwright and Chromium; inspect their arguments before use.

For behavior you audit, run the relevant existing tests, for example:

```sh
.venv/bin/python -m pytest -q tests/test_pcc.py tests/test_ttr_referent_identity.py tests/test_nonrestrictive_relatives.py
```

Use meaningful targeted checks first; broaden to the shared-engine suite if engine work is subsequently authorized and undertaken. Report skipped prerequisites and failures explicitly. Dated earlier results are not a new run: the PCC handover recorded 1,888 passed and four skipped, and public browser evidence is in `data/coverage/pcc-public-2026-10-07.json`.

For evaluation inspect `data/coverage/`, `docs/coverage/`, `scripts/audit_bilingual_coverage.py`, `audit_paragraph_coverage.py`, `audit_assisted_coverage.py` and `sample_paragraph_coverage.py`. Keep development cases and held-out material separate. Report lexical coverage, complete derivations, judged semantic adequacy and sample denominators separately. Historical small-sample results remain historical.

Produce:

- Updated canonical library records, discovery log and source fingerprints; regenerated HTML, BibTeX and CSL exports, with validation evidence.
- A dated research report under `docs/research/`, linked from its README, with source-by-source findings and a phenomenon/mechanism/backend matrix. Follow existing report tooling if producing a standalone LaTeX/PDF version.
- Bounded analysis cards for the strongest new readings and a prioritized backlog with the complete first-slice specification above.
- A concise architecture audit explaining the relationship between theory, inherited software, our native semantic extensions, TTR, lexical assistance and Jev.
- A dated handover under `.claude/handover/` listing actual changes, checks, unresolved sources and next actions.

Review `docs/workbench-walkthrough.md` and the slide sources `docs/ds-workbench-slides.tex` / `docs/ds-workbench-slides-README.md` for claims your findings change. Update relevant claims and rebuild affected generated documents using their documented scripts; do not silently edit only a generated artifact. Preserve the requested development acknowledgments: Astra with Codex, Fable 5.1 with Claude Code, and OpenRouter for models in the application. Do not reintroduce the removed personal upstream credit slide or irrelevant hosting remarks about Svarna.

No deployment, package publication or new external collaboration account is part of this research task. Prepare local, reviewable results. Preserve existing work and distinguish local changes from the public application.

Finish with the strongest findings, verified additions and corrections, remaining uncertainty, and the recommended next implementation. Clearly separate **what the literature says**, **what this code does**, **what you tested**, and **what you propose**.
