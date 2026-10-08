# DynamicSyntax engine capability audit, search scaling and debt list (read-only, 2026-09-27)

Repo: `/Users/graogro/Dropbox/revisiting-formal-semantics/DynamicSyntax`, branch `constructive-ds`, working tree clean. All paths below are relative to that root unless absolute. No file in the repo was edited; the only files written are the probe script `/private/tmp/claude-501/-Users-graogro-Dropbox-formalizing-formal-semantics/60610210-84b6-448d-a246-5b2b22aa0524/scratchpad/ds_scale_probe.py` and scratchpad grammar copies under `.../scratchpad/gram/`. Every runtime claim was executed with `uv run python` in-process monkeypatches (counters only).

## Part 1. Engine capability per coverage gap class

Legend: EXISTS = usable by a grammar today; PARTIAL = exists but not in the form the thesis needs; MISSING = no code path.

### (a) Kleene-star closure in modality triggers (needed for *ADJUNCTION, LATE *ADJUNCTION, generalized unfixed nodes)

Status: PARTIAL. What exists is Kleene-PLUS over existing nodes, not star over fixed paths, and `*`/`U`/`P` are literal edge characters.

- `src/dylan/tree/basic_operator.py:22` `OP_PATTERN = (/\\|\\/)((?:[01]\+)|\+|[01L\*UPC]*)`: closures accepted are `0+`, `1+`, bare `+`; the comment at :18-21 says "Closures are only meaningful in trigger modalities, never in navigation (make/go)".
- `src/dylan/tree/modality.py:87-122` `Modality.reachable`: for a plus op it walks the address inventory; for `*`/`U`/`P` it does `addr.go_op(op)` (literal append, :117-120). Docstring :92-93: "`*`, `U` and `P` themselves denote literal unfixed edges". `modality.py:124-131` `relates` uses `reachable` only when `addresses` is passed.
- `src/dylan/tree/node_address.py:104-105, 113-114`: `modality_path_matches` and `go_op` return False/None on any plus op.
- `docs/design/loft-engine-status.md:21-26`: "`*`, `U`, and `P` remain literal unfixed address edges in modalities. Plus closures are relations used in triggers, not paths for `make` or `go`".
- Runtime check (tree with keys `0, 0*, 0*1, 00, 0L, 0L0, 0P, 0U`): `Modality.parse(r"<\/*>").reachable(...)` = `{'0*'}` only (does not reach `00` or `0*1`); `<\/+>` reaches `{'0*','0*1','00','0P','0U'}`; `<\/1+>Ex.x` False (no `01`); `make(\/1+)` and `go(\/1+)` return None; `[\/*]Ty(e)` evaluates as a box over the single literal `0*` target. Tested closures in `tests/test_loft_engine.py:40-52` (`test_reachable_partial_tree`) are exactly `<\/1+>`, `<\/0+>`, `<\/+>`, `<\/*>` (expects `{"0*"}`), `<\/>`, `<\/1+\/0>`.
- Box semantics now real: `src/dylan/tree/label/labels.py:636-670` `ModalLabel.check_with_tuple_as_context` returns False on the first failing target for `required` boxes and True on empty domain (:665). This is the mechanism behind the SMG gate `[\/1+]?Ty(x)` (`src/dynamicsyntax/grammars/2026-smg-mltt/lexical-actions.txt:5`).
- What *ADJUNCTION (thesis 2.37, `docs/design/thesis-full-system.md:85-86`) needs and lacks: (1) a guard "no unfixed node in this local tree" that quantifies over all descendants, not the literal `pointer+"*"` key (the Java comment at `src/dynamicsyntax/grammars/2015-english-ttr/computational-actions.txt:107` "should actually check for no existing unfixed node in this sub-tree" still stands); (2) an external star modality `<u*>Tn(a)` with address entailment for MERGE (thesis 2.41, `thesis-full-system.md:95-97`), i.e. `NodeAddress.subsumes` (`node_address.py:138-146`) used inside a trigger; `subsumes(Y)` still parses to `GenericLabel` (runtime: "Unsupported trigger label 'subsumes(Y)'; evaluating as False"). LATE *ADJUNCTION additionally needs a star daughter under a type-complete non-root node; `make(\/*)` works at any pointer (literal), so structure building is possible but the guard/merge side is not.

### (b) Unfixed-node MERGE

Status: two mechanisms, neither usable for relatives, wh or long-distance.

- Semantics-time `Tree.merge_unfixed` (`src/dylan/tree/tree.py:295-329`, called only from `get_maximal_semantics` :547): still never merges. Runtime today: `unfixed("0*").is_unifiable(fixed("00"))` = False, reversed = True; `merge_unfixed()` on a tree with `0*`, `00 ?Ty(e)`, `01` returns 1 tree with keys `['0','0*','00','01']`. Cause unchanged since `docs/design/maps/tree-internals.md:66`: `src/dylan/tree/node.py:123` tests `other.address.subsumes(self.address)` (fixed merge point subsumes only itself). Only consumer is the TTR path; `get_maximal_semantics` returns early for native grammars at `tree.py:531-543`, so the 2026 grammars never touch it. `tree.py:550` raises `NotImplementedError("more than two trees after mergeUnfixed")`.
- Action-time `Merge` (`src/dylan/action/atomic/merge.py:33-51`): works mechanically (`merge(\/*)` returned a tree in the probe) with no type/formula compatibility check; compatibility is the calling rule's IF job. In `2015-english-ttr` the `merge` rule (`computational-actions.txt:140-148`) needs `subsumes(Y)` (GenericLabel, dead) and `<Y>(?Ex.tn(x) & ty(V))`; `*late-star-merge` (:150-163) needs `<\/*>?Ex.tn(x)`, which now holds only for a literal `pointer+"*"` node. Probe: `who does john like?` ok=False (`who` yields 0 children), `who likes john?` ok=False, `john likes mary who arrives.` ok=False after 6 successful backtracks.
- What relatives/wh/long-distance need: address entailment in the IF language (`subsumes`-style label over `Tn` values), `Ex.Tn(x)` on unfixed nodes (exists: `TnLabel`, `labels.py` via factory :930; `Ex.tn(x)` now checks True), a merge target search over the local tree rather than a literal modality, and conflict detection on `Fo` (only the metavariable clash in `put.py:42-47` exists).

### (c) LINK adjunction and evaluation

Status: 2026 grammars EXISTS for one construction only; 2015 TTR has the general machinery but its rules are partly dead.

- 2026-english-mltt: LINK is built inside the hard-coded `semantic-adverb` effect (`src/dylan/action/atomic/semantic_effects.py:131-181`), which also hard-codes the modifier name `quickly` (:155); evaluation is `anticipation-link` / `semantic-link` (`grammars/2026-english-mltt/computational-actions.txt:49-54`; `semantic_effects.py:182-200`), which copies the LINKed formula back into the VP. No LINK adjunction rule, no relativizer, no `?<d*>Fo(a)` copy requirement, no appositive. `docs/design/native-semantics.md:123-128`: relatives, coordination, questions not supplied.
- 2015-english-ttr: `*link-evaluation` (:167-179) fires (per `maps/tree-internals.md:79`); `anticipationL` (:72-76) was activated in wave 1 (`loft-engine-status.md:33-36`); `link-adj-e` is block-commented (:79-91); `pron_whrel` (lexical-actions.txt:441) builds LINK plus an unfixed node whose MERGE is dead per (b).
- Needed: general LINK ADJUNCTION (2.79), relativizer copy (2.83), LINK EVALUATION for Props (2.90) with a Σ/∧ semantic effect instead of the TTR `conjoin`, plus completion crossing `L-1` (already in `completion` rule via `¬</\L>Ex.x` guard at `2026-english-mltt/computational-actions.txt:35`).

### (d) Metavariable SUBSTITUTION and the presupposition solver

Status: MISSING as a solver; restrictions are literal symbols.

- `src/dylan/formula/formula_metavariable.py:23-26`: `restriction` = the suffix after `_` in the name (`U_Sp'` -> `Sp'`). `src/dylan/action/atomic/put.py:42-47`: two restricted metavariables with different restrictions at one node make `put` fail (the PCC clash); an established restriction is kept (:46-47).
- No code substitutes a formula for `U` from context: grep `substitut|presuppos` over `src/dylan` finds only TTR variable substitution and the `restriction` docstring. `loft-engine-status.md:63-66`: "does not implement ... a general substitution-presupposition solver ... Restrictions here are literal symbolic presuppositions".
- Greek fragments avoid the problem: clitics put constant `Fo(mltt:REF)` with REF in `{him, theme}`; verbs put `Fo(SUBJECT)` in `{pro, speaker, hearer}` (`scripts/build_greek_fragments.py:14-20, 81, 97`; `docs/design/dialogue.md:74-76` "not dynamically resolved to the turn names").
- Needed: a `?Ex.Fo(x)` requirement satisfied by SUBSTITUTION with anti-locality (`thesis-full-system.md:44-48`), a discourse-referent store on `Context`, and person/case features that today do not exist as labels (`_UNARY_PRED_RE` at `labels.py:26` admits only `Tense|Class|person|Accept|Mood`).

### (e) Clitic clusters

Status: engine can hold two locally-unfixed-plus nodes (collapse semantics); grammars cannot produce two clitics.

- Blocker in the generated grammar: `clitic(REF)` guard `¬[+CLITIC]` and effect `put([+CLITIC])` at the root (`build_greek_fragments.py:73, 83`; generated `2026-smg-mltt/lexical-actions.txt:6, 15`). Probe: `το τον ξέρω.` on 2026-smg-mltt gives 0 children at the second clitic; `greek_workbench.py:285` labels it `construction_gap`.
- Fixed `01/010` object slot: the fragment clitic builds `\/1` then `\/0` (`lexical-actions.txt:7-13`), so a second accusative has nowhere to go anyway.
- Engine-level cluster behaviour exists only in `tests/test_clitic_restrictions.py:80-101` (`clitic_rule`): DAT builds `make(\/P)` locally unfixed with `?Ex.Tn(x)`, ACC builds fixed `\/1\/0`; `test_indicative_dat_acc_order_and_imperative_proclisis_block` (:119-127), `test_smg_imperative_permits_both_clitic_orders` (:130-136), `test_gsg_imperative_blocks_acc_dat_order` (:139-143), `test_two_local_clitics_fail_with_incompatible_persons` (:146-150). Address `0P` collapse: `Tree.make` at `tree.py:585-591` creates only if the key is absent, so a second `make(\/P)` reuses the node and `put` decides the clash.
- A cluster template needs: `clitic(REF,PERSON,CASE)` with case deciding fixed vs `\/P` (thesis 6.49, `docs/design/thesis-clitic-system.md:81, 118-119`), removal of the root `[+CLITIC]` flag, a MERGE that later fixes `0P` into `010/0110` (b), and the `[\/+]?Ex.Tn(x)` imperative gate already present.

### (f) Case filters and full DPs with case

Status: MISSING. No `Case(...)` label parses (`labels.py:26`); no grammar row carries case (`grep "Case\b|case(" grammars/*/lexical-actions.txt` = 0). The thesis output-filter case `?<u0>Ty(e->t)` / `?<u0>Ty(t)` (`thesis-full-system.md:59-60`) is expressible as a `Requirement` over a `ModalLabel` (the factory builds `?<mod>...` via `Requirement`), and `Requirement` blocks `Tree.is_complete` (`tree.py:626-636`) so it would act as a filter; untested. Greek lexicons have no DP rows at all (`build_greek_fragments.py:12-40`: clitics, verbs, `δεν`, `να`).

### (g) Questions

Status: 2026 grammars MISSING; 2015 TTR PARTIAL.

- 2015-english-ttr: `pron_whq(CLASS)` (:313), `pron_whq_det` (:342), `question(PRED)` (:825), `+Q` feature; `Tree._max_sem_at` conjoins `[p==question(head):t]` on `+Q` (`tree.py:514-517`), which is TTR-only. `does a man arrive?` parses ok (probe), `who ...` do not (b).
- 2026-english-mltt: `?` is a `punctuation` row and `Q` has no semantic counterpart; `native-semantics.md:125` lists questions as not supplied.

### (h) Coordination

Status: MISSING in both. `2015-english-ttr/lexicon.txt` has no `and` row (`grep "^and "` = 0; probe `john likes mary and bill arrives.` stops at `and`, parser returns None at `interactive_context_parser.py:614-617`). The thesis lexical `and` (`thesis-full-system.md:111-112`, LINK + `?Ty(X)`) needs LINK EVALUATION over `Ty(X)` for X in `{e, t, e->t}`, which (c) lacks.

### (i) Tense/aspect and the situation spine

Status: MISSING. `docs/design/greek-clitics.md:45-48, 60` ("stands in for the situation projection", "tense/aspect are not interpreted"); `clause-embedding.md:99`. The fragment's `negative`/`subjunctive` build a fixed open subject slot instead (`build_greek_fragments.py:131-137`). TTR grammars have `event_restrictor(TENSE)` macros (`maps/semantics-flow.md`), not reusable by the native backend.

### (j) Scope beyond narrow/wide

Status: two settings only. `src/dylan/formula/mltt/semantics.py:138-151` `close_witnesses(scope)` either wraps witnesses inside all leading Π (`narrow`) or outside (`wide`); `workbench_api.py:104-105` validates `{narrow, wide}`. `native-semantics.md:96-98`: "semantic closure settings over the same DS tree, not two independently searched syntactic paths". Witnesses are a flat tuple (`semantics.py:108, 182`), so per-quantifier ordering, inverse linking or nested scope islands have no representation.

### (k) Dialogue

- `MAX_REPAIR_DEPTH = 1` (`interactive_context_parser.py:64`), `backtrack_and_parse` (:828-863) replaces the nearest repairable word edge only; `test_dialogue_repair.py:55` sets `max_repair_depth = 0` for the boundary test.
- Grounding: only the `uhu` ack path calls `ground_for` (`:416-419`); checked at `:849, 854`. `dialogue.md:71-76`: grounding judgments, QA fragments, clarification, ellipsis, anaphora not implemented.
- Speech acts: `SpeechActInferenceGrammar._rules` is always empty (`speech_act_inference_grammar.py:17-23`, "rules not loaded in v0"); `InferSpeechAct.exec` (`infer_speech_act.py:22-33`) therefore returns a clone; `infer-sa` is only reachable through `effect_factory.py:204-205`; 2015 `assert/question` templates rely on `Assert(Y)`, `Speaker(X)` labels that fall to `GenericLabel` (`maps/public-api-packaging.md:105`).

### (l) Semantics: Coq export, proof terms, LaTeX

- `src/dylan/formula/mltt/coq.py:38-54`: hierarchy loop raises `ValueError("Coq export needs an acyclic single-parent nominal hierarchy")` (:47); `Parameter quickly : Prop -> Prop.` hard-coded (:60); `coq_term` raises on any kind outside `name/sigma/pi/lam/arrow/app/fst/and` (:26), so `eps/tau/pair/cn` cannot export. No Γ_DS context export (design §4). Only `Definition meaning : Type` and `Check meaning.` (:61-62): the export checks well-typedness of the meaning type, never inhabits it.
- Proof-term synthesis: `grep proof src/dylan/formula/mltt/*.py` = 0 hits; `native-semantics.md:125` lists it as not supplied.
- LaTeX: `ParseResult.to_latex(kind="semantics")` calls `semantics_figure_tex(self.semantics)` (`src/dynamicsyntax/parse_result.py:82-110`, `src/dylan/formula/latex/semantics_tex.py:8-10` typed `TTRRecordType`); runtime on `a man walks.` (2026-english-mltt): `AttributeError: 'SemanticFormula' object has no attribute 'to_latex'`. No `to_tex` in `src/dylan/formula/mltt/` (design `constructive-ds-design.md:92-93` unmet).

### (m) Grammar loading: strict mode, dialect gates, generated fragments

- Strict mode exists only on `DAGParser.from_resource_dir(..., strict=)` (`dag_parser.py:63-73`); `InteractiveContextParser._apply_resource_dir` builds `Lexicon(path, self._top_n)` and `Grammar(path)` without `strict` (:233-234), so `dynamicsyntax.parse`, `icp` and the workbench (`workbench_api.py:216 parser = icp(grammar)`) never validate strictly. `tests/test_grammar_validation.py:91-103` documents that bundled `2026-english-ttr` warns (`v_ditran_fin ... not found in lexical-actions.txt`) and still parses.
- Dialect gates are compile-time: `GATES` (`build_greek_fragments.py:42-46`) are pasted into the `clitic(REF)` trigger; `semantics.json` `dialect`/`fragment` keys are metadata only (no `src/dylan` consumer outside `greek_workbench.py`). Dialect = grammar id; there is no runtime parameter.
- Generated fragments: 11 templates, 5 computational rules copied by string slicing from `2026-english-{backend}/computational-actions.txt` between `anticipation0` and `anticipation-link` (`build_greek_fragments.py:141-143`), so Greek grammars have neither `intro-pred` nor LINK rules. A hand-written thesis SMG grammar needs: templates with person/case/number parameters, a `situation` or spine rule, `*ADJUNCTION`/`LATE *ADJUNCTION`/`LOCAL *ADJUNCTION` computational rules, `MERGE`, `LINK ADJUNCTION`, TOPIC rules, and a maintained `lexicon.txt` instead of `LEXICA`; plus `semantics.json` predicates for each verb.

## Part 2. Search scaling measurements

Method: `InteractiveContextParser(grammar, top_n=N)`, `init/new_sentence/parse_utterance`, then `complete()` for native grammars (same as `_parse.py:99-110`). Counters: DAG tuples/edges at end, `go_first` traversals, `attempt_backtrack` (ok/calls), `ComputationalAction.exec` calls (ca), `LexicalAction.exec` calls (la), per-word fan-out (lexicon rows, rows after `top_n`, children built). Times are single runs on this machine, warm process, in ms.

### 2026-english-mltt (top_n=3; every word has 1 lexicon row)

| sentence | tok | ok | ms | tuples | edges | traversed | backtracks | ca | la |
|---|---|---|---|---|---|---|---|---|---|
| a man walks. | 4 | T | 4.1 | 8 | 7 | 6 | 0/0 | 101 | 9 |
| every man walks. | 4 | T | 2.8 | 8 | 7 | 6 | 0/0 | 101 | 9 |
| every doctor examined a patient. | 6 | T | 4.7 | 10 | 9 | 8 | 0/0 | 147 | 13 |
| a black dog walks. | 5 | T | 3.8 | 9 | 8 | 7 | 0/0 | 124 | 11 |
| john walks quickly. | 4 | T | 3.1 | 9 | 8 | 7 | 0/0 | 109 | 9 |
| bill shouts. | 3 | T | 1.7 | 7 | 6 | 5 | 0/0 | 78 | 7 |
| john thinks that mary walks. | 6 | T | 5.2 | 11 | 10 | 9 | 0/0 | 184 | 17 |
| john says that mary thinks a man walks. | 9 | T | 10.7 | 15 | 14 | 13 | 0/0 | 295 | 27 |
| john thinks mary walks. | 5 | T | 4.7 | 10 | 9 | 8 | 0/0 | 166 | 15 |
| every doctor examined a patient quickly. | 7 | T | 6.5 | 12 | 11 | 10 | 0/0 | 178 | 15 |

Every word builds exactly 1 child (max_children = 1 in all 10). The DAG is a chain: tuples = tokens + 2 (axiom plus completion), no backtracking. Rule attempts per word: 9 (noun, no left adjustment), 18 to 27 (determiner/name: optional BFS over 6 optional rules), 32 to 60 (verb), and 28 to 86 at `.` (the `complete_tree` loop, growing with tree size). Time is linear in tokens (about 1.1 ms/token).

### 2015-english-ttr (workbench_api.py:18-23 sentences)

| sentence | top_n | ok | ms | tuples | edges | traversed | backtracks | ca | la | max children | top_n cuts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a man knows you. | 3 | T | 23.7 | 12 | 11 | 7 | 0/0 | 226 | 18 | 3 | 0 |
| a man arrives. | 3 | T | 11.9 | 11 | 10 | 6 | 0/0 | 196 | 16 | 3 | 0 |
| does a man arrive? | 3 | T | 16.7 | 12 | 11 | 7 | 0/0 | 261 | 30 | 2 | 0 |
| john likes mary. | 3 | T | 13.2 | 13 | 12 | 6 | 0/0 | 178 | 16 | 4 | 0 |
| same four | 0 (unlimited) | T | 17.0 / 12.3 / 16.8 / 12.9 | identical | identical | identical | 0/0 | identical | identical | identical | 0 |

Fan-out here comes from optional rules, not the lexicon: `knows` (1 row) builds 3 children, `likes` (2 rows: `v_tran_fin`, `v_subjcon_fin`) builds 4. `top_n` is not hit on these four sentences. Loaded lexicon: 232 forms, 360 entries (560 rows on disk; rows with missing templates skipped), 86 forms with more than 1 entry, 14 with more than 3: `arrest 4, begin 6, can 4, fly 4, go 4, hate 4, leave 4, like 4, read 6, start 6, stay 4, think 4, travel 4, want 4`. The cut is therefore live for those 14 forms only (probe: `who does john like?` hides 3 entries of `like`). Per-child cost is 3 to 5x the mltt cost (TTR maximal semantics is computed eagerly for each child at `interactive_context_parser.py:436, 485`).

### Greek CASES (2026-{smg,cypriot,pontic}-mltt, top_n=3)

| grammar | sentence | ok | ms | tuples | edges | traversed | backtracks | ca | la | max children |
|---|---|---|---|---|---|---|---|---|---|---|
| smg | τον αγαπά. | T | 2.9 | 6 | 5 | 4 | 0/0 | 49 | 12 | 1 |
| smg | αγαπά τον. | F | 1.5 | 3 | 2 | 1 | 0/2 | 47 | 9 | 1 |
| smg | δεν τον ξέρω. | T | 3.8 | 9 | 8 | 5 | 0/0 | 114 | 25 | 2 |
| smg | δεν ξέρω τον. | F | 3.1 | 4 | 3 | 2 | 0/2 | 113 | 21 | 1 |
| smg | γράφε το! | T | 2.2 | 6 | 5 | 4 | 0/0 | 54 | 11 | 1 |
| smg | το γράφε! | F | 1.1 | 3 | 2 | 1 | 0/2 | 34 | 9 | 1 |
| smg | να το γράψει. | T | 3.6 | 9 | 8 | 5 | 0/0 | 114 | 19 | 2 |
| smg | να γράψει το. | F | 3.2 | 4 | 3 | 2 | 0/2 | 113 | 17 | 1 |
| smg | το τον ξέρω. | F | 2.0 | 6 | 5 | 4 | 0/1 | 59 | 14 | 1 |
| cypriot | ιξέρω τον. | T | 2.0 | 6 | 5 | 4 | 0/0 | 54 | 11 | 1 |
| cypriot | τον ιξέρω. | F | 1.3 | 3 | 2 | 1 | 0/2 | 37 | 7 | 1 |
| cypriot | εν τον ιξέρω. | T | 4.0 | 9 | 8 | 5 | 0/0 | 114 | 25 | 2 |
| cypriot | εν ιξέρω τον. | F | 3.1 | 4 | 3 | 2 | 0/2 | 113 | 21 | 1 |
| cypriot | γράφε το! / το γράφε! | T / F | 2.0 / 1.2 | 6 / 3 | 5 / 2 | 4 / 1 | 0/0, 0/2 | 54 / 37 | 11 / 7 | 1 |
| cypriot | να το γράψει. / να γράψει το. | T / F | 3.9 / 3.3 | 9 / 4 | 8 / 3 | 5 / 2 | 0/0, 0/2 | 114 / 113 | 19 / 17 | 2 / 1 |
| pontic | ekser aton. / aton ekser. | T / F | 1.9 / 1.1 | 6 / 3 | 5 / 2 | 4 / 1 | 0/0, 0/2 | 54 / 37 | 11 / 7 | 1 |
| pontic | ci kser aton. / ci aton kser. | T / F | 4.6 / 2.3 | 11 / 4 | 10 / 3 | 5 / 2 | 0/0, 0/2 | 137 / 86 | 27 / 16 | 2 / 1 |

Verbs have 3 lexicon rows (`finite-plain/neg/na`) but at most 1 survives its `[+NEG]`/`[+NA]` guard, so children per word stay at 1 (2 at `.` when a completion edge splits). Excluded strings fail at the misplaced clitic (0 children) after 2 fruitless backtrack calls. All 20 sourced strings run in under 5 ms.

### Synthetic scaling (scratchpad copies of 2026-english-mltt; nothing in the repo touched)

k extra lexicon rows per open-class word (distinct PRED names, all type-correct), `top_n=0`:

| k | every doctor examined a patient. ms / tuples / la | john says that mary thinks a man walks. ms / tuples / la |
|---|---|---|
| 1 | 5.8 / 10 / 13 | 11.3 / 15 / 27 |
| 2 | 5.2 / 14 / 19 | 11.8 / 24 / 42 |
| 4 | 6.2 / 22 / 31 | 18.2 / 42 / 72 |
| 8 | 8.4 / 38 / 55 | 19.1 / 78 / 132 |
| 8, top_n=3 | 5.9 / 18 / 25 (9 cuts, 45 hidden entries) | 13.2 / 33 / 57 (18 cuts, 90 hidden) |

Tuples grow linearly in k (about 4 tuples per k per open-class word), traversed edges stay constant (8 and 13): DFS takes the first child and never returns because every child completes. Time grows sublinearly because building a child is cheap relative to the fixed per-word optional-rule BFS.

m extra optional rules (copies of `anticipation0`, `anticipation1`, `intro-pred` under new names), `top_n=3`:

| m (total optional rules) | every doctor examined a patient. ms / ca / max children | john says ... walks. ms / ca / max children |
|---|---|---|
| 0 (6) | 4.7 / 147 / 1 | 10.7 / 295 / 1 |
| 3 (9) | 7.6 / 194 / 2 | 16.1 / 403 / 2 |
| 6 (12) | 8.4 / 241 / 3 | 22.0 / 511 / 3 |
| 12 (18) | 13.3 / 335 / 5 | 36.8 / 727 / 5 |
| k=4 and m=6, top_n=0 | 11.2 / 259 / 12 | 31.2 / 565 / 12 |

Optional-rule count multiplies `ca` and time linearly (each optional rule is tried on every pair in `global_pairs`, `interactive_context_parser.py:464`), and each distinct prefix sequence becomes an extra child (children = lexical entries x rule-prefix variants: 4 x 3 = 12 at `examined`). Combined growth is multiplicative in children (108 tuples for the 9-token sentence) but traversal stays 13 because the first path succeeds.

Caps: no `cap hit` message was logged in any run (loguru sink on "cap hit"/"exceeded"). `max_lexical_adjustment_pairs` 50_000 (`:63`), `max_nonoptional_adjust_passes` 10_000 (`dag_parser.py:27`) are three orders of magnitude above measured pair counts (largest `global_pairs` observed indirectly: 12 children per word). The 64-attempt IF loop (`if_then_else.py:240`) cannot be observed without editing; the Greek rules bind at most one meta (`<Z>`), so it is not reachable. `top_n=3` is hit for 14 forms of the 2015 lexicon and for any grammar with 4 or more rows per form.

### Where coverage growth multiplies search, and which lever fits

| growth source | code site | measured effect | right lever |
|---|---|---|---|
| more templates per word (case/person variants of clitics, verb readings) | `lexicon.py:370-373` lookup, `icp:422-441, 477-492` child build | tuples linear in k; traversal unchanged while first child completes; hidden entries once k > 3 | Engine: lift or parameterize `top_n` (constructor exposes it: `icp(grammar, top_n=0)`); Jev idea 1 (entry prior) only matters when the first child is wrong, which today never happens on the shipped sentences. Prior-ordered DFS is the lever only after such sentences exist (clusters, VSO). |
| more optional rules (*ADJUNCTION, LATE *ADJ, LINK ADJ, TOPIC) | `icp:446-475` BFS over `global_pairs`, sorted alphabetically `:464` | ca and ms linear in rule count; children = entries x rule-prefix variants | Engine first: per-pair rule applicability caching keyed by `_tree_structural_key` already exists (`tried`); a cheap win is skipping rules whose trigger cannot match the pointed node type (static pre-filter). Then Jev idea 2 (child ordering) once alternative prefixes actually lead to dead ends; today the comparator's completeness score decides and ties fall to insertion order (`word_level_context_dag.py:115`). |
| MERGE and unfixed nodes | `merge_unfixed` semantics-time, `Merge` action | not measurable: never fires | Engine fix (b); no ordering question until merge candidates exist, then a Choice over merge addresses is well typed. |
| eager semantics per child | `icp:436` `tup.get_semantics`, `:485` `get_maximal_semantics` | TTR children cost 3 to 5x mltt; runs for every child even when never traversed | Engine: lazy semantics (compute on traversal or completion); pure speed, no Jev role. |
| completion at `.` | `dag_parser.py:164-188` state key over all nodes per pass | ca at `.` grows 28 -> 86 from 4 to 9 tokens | Engine: fine as is; memoize `is_complete`/state key if trees reach 50+ nodes. |
| DFS never re-ranks after a dead end | `attempt_backtrack` :335-352 nearest ancestor | 2 fruitless backtrack calls per excluded Greek string; 6/8 on `john likes mary who arrives.` | Engine: backtracking is correct and cheap; a beam is not needed at these sizes. Prior-ordered DFS helps only when several siblings survive. |

Conclusion for the plan: at present fan-out is 1 child per word on every shipped native sentence, so ordering (Jev ideas 1 and 2) has nothing to order; the multiplicative regime only appears once the thesis grammar adds templates and optional rules together (measured 12 children per word at k=4, m=6). Engine changes that pay first: `top_n` exposure, lazy child semantics, real MERGE and star guards. A prior-ordered DFS becomes valuable at the point where the k x m product exceeds about 4 and the first child stops being the winning one.

## Part 3. Engine debts a wide-coverage push will trip over

1. Bare `return 1` tie-break: `src/dylan/dag/word_level_context_dag.py:115` (also `:86, :91, :97`); with equal incompleteness siblings keep insertion order, and `hyp-*` induction names are special-cased at `:107-114` inside the parser comparator.
2. Alphabetical rule order everywhere: `src/dylan/parser/dag_parser.py:126` (star fixpoint, first applicable wins), `:156` (completion, first match), `src/dylan/parser/interactive_context_parser.py:464` (optional BFS). Renaming a rule changes parse order.
3. Silent `top_n` cut: `src/dylan/action/lexicon.py:370-373`; default 3 from `interactive_context_parser.py:85`; `dynamicsyntax.parse` and `workbench_api.py:216` never pass it. 14 forms of 2015-english-ttr lose entries today.
4. Generated Greek grammars: `scripts/build_greek_fragments.py` is the source of truth; six shipped directories are outputs; computational rules are string-sliced from the English file (`:141-143`); `[+CLITIC]` one-clitic limit (`:73, 83`); subject/object constants instead of metavariables (`:81, 97`).
5. `Tree.merge_unfixed` never merges (`src/dylan/tree/tree.py:295-329`, `node.py:123`); `NotImplementedError` at `tree.py:550`; 2015 `merge` and `*late-star-merge` rules dead (`grammars/2015-english-ttr/computational-actions.txt:140-163`); `subsumes(Y)` is a `GenericLabel` (`labels.py:770-793`, factory fallthrough `:983`).
6. Empty speech-act rules: `src/dylan/action/speech_act_inference_grammar.py:17-23`; `InferSpeechAct` no-op (`infer_speech_act.py:28-33`).
7. Hard-coded `quickly`: `src/dylan/action/atomic/semantic_effects.py:155` and `src/dylan/formula/mltt/coq.py:60`; `semantic-adverb` builds LINK only under root `\/1` (`:134-141`).
8. Coq export limits: `coq.py:47` single-parent hierarchy, `:26` unsupported kinds raise, no Γ_DS.
9. LaTeX for native semantics broken: `parse_result.py:82-110` -> `semantics_tex.py:8-10` expects `TTRRecordType`; `SemanticFormula` has no `to_latex` (runtime AttributeError).
10. Strict validation not plumbed into the live parser: `interactive_context_parser.py:233-234` vs `dag_parser.py:63-73`.
11. Verb pointer hack: `_repoint_for_verb_lexical` (`interactive_context_parser.py:41-60`) moves the pointer to `01` for `v_*` templates only (TTR naming convention).
12. Hard-coded completion names: `_index_of_trp` `{"trp", "completion", "merge"}` (`:527-534`); `_separate_grammars` routes by name prefix `anticipation` (`dag_parser.py:51-60`); `_ALWAYS_GOOD_EDGE_NAMES` (`word_level_context_dag.py:27`).
13. Metavariable reset hack: `if_then_else.py:229-233` resets all named metas at embedding level 0 ("until Label.getMetas / backtracker parity is complete"); `exec_exhaustively` is single-path (`:274-281`).
14. Eager per-child semantics: `interactive_context_parser.py:436, 485` (cost item above).
15. Hashing: `Tree.__hash__` (`tree.py:661-663`) can raise on TTR formulas; the parser uses `tried: dict[str, set[Tree]]` at `:451` relying on total hashing added in wave 0; `maps/tree-internals.md:73` history.
16. Dead/duplicated data: `src/dylan/formula/epsilon_term.py` (44 lines, used only by induction `induction_semantics.py:44-83`); three byte-identical copies of `2015-english-ttr` (md5 `8e0684936553a67d0d18ab0bec124aa7` in `src/dynamicsyntax/grammars/`, `resources/`, `web/public/grammars/`), no sync script (`maps/public-api-packaging.md:111`); TTR freshening no-op and dropped `det_quant` manifests (`maps/semantics-flow.md:11, 49`).
17. Label vocabulary whitelist: `_UNARY_PRED_RE` `(Tense|Class|person|Accept|Mood)` at `labels.py:26`; any new feature (`Case`, `Person`, `Number`) falls to `GenericLabel` with a one-time warning (`:784-787`).
18. `star-adjunction` and `link-adj-e` are block-commented in the shipped 2015 grammar (`computational-actions.txt:58-69, 79-91`) but active in `resources/2015-english-ttr-robot` and `resources/2025-seed-grammar`.
19. One real TODO: `src/dylan/type/dstype.py:193` "TODO(verify): full MetaType port".
20. Coordination and wh lexicon gaps: no `and` row in any grammar; `who` rows exist only in 2015 (`lexicon.txt:589-590`) and depend on dead MERGE.

KEY FACTS:
- Kleene closure status: only plus closures (0+, 1+, +) exist (basic_operator.py:22, modality.py:87-122); star/U/P are literal edges (runtime: <\/*> reaches {'0*'} only); make/go reject closures; subsumes(Y) parses to GenericLabel (always False); loft-engine-status.md:21-26 confirms
- Tree.merge_unfixed still never merges (tree.py:295-329; node.py:123 inverted subsumes; runtime verified); action-level Merge works mechanically without compatibility checks (merge.py:33-51); 2015 merge/*late-star-merge rules dead; wh sentences fail (who does john like? ok=False)
- LINK in 2026 grammars exists only as the hard-coded semantic-adverb effect with literal 'quickly' (semantic_effects.py:131-181, :155) plus anticipation-link/semantic-link; no LINK adjunction, relativizer, coordination or appositive rule
- No substitution/presupposition solver: FormulaMetavariable.restriction is a name suffix (formula_metavariable.py:23-26); put.py:42-47 is the only PCC mechanism; Greek fragments use constants him/theme/pro/speaker/hearer
- Clusters blocked by the root [+CLITIC] flag (build_greek_fragments.py:73,83); two-clitic engine behaviour exists only in tests/test_clitic_restrictions.py:80-150 via make(\/P) collapse; no Case label parses (labels.py:26 whitelist Tense|Class|person|Accept|Mood); no DP rows in Greek lexica
- Questions, coordination, tense/aspect absent from 2026 grammars; 2015 TTR has +Q and pron_whq but no 'and' row; scope is a two-valued close_witnesses setting over a flat witness tuple (mltt/semantics.py:138-151)
- Dialogue: MAX_REPAIR_DEPTH=1 (icp:64), grounding only via 'uhu' ack (icp:416-419), speech-act rules never loaded (speech_act_inference_grammar.py:17-23)
- Semantics: coq.py raises on multi-parent hierarchy (:47), hard-codes Parameter quickly (:60), exports only Check meaning (no proof terms, grep proof = 0); to_latex(kind='semantics') on an mltt parse raises AttributeError (SemanticFormula has no to_latex)
- Strict grammar validation is only on DAGParser.from_resource_dir (dag_parser.py:63-73); InteractiveContextParser._apply_resource_dir (:233-234) and workbench icp(grammar) never use it; dialect gates are compile-time strings pasted by build_greek_fragments.py:42-46
- Scaling: 2026-english-mltt 10 sentences parse in 1.7 to 10.7 ms, tuples = tokens + 2, exactly 1 child per word, zero backtracks; 2015 TTR 4 sentences 11.9 to 23.7 ms, max 4 children per word (from optional rules, not lexicon), top_n unchanged results at top_n=0; Greek CASES all under 5 ms, excluded strings fail with 0 children at the misplaced clitic
- top_n=3 hides entries for 14 loaded 2015 forms (arrest, begin 6, can, fly, go, hate, leave, like, read 6, start 6, stay, think, travel, want); no other cap (50_000 pairs, 10_000 passes, 64 IF attempts) was hit in any run
- Synthetic scaling on scratchpad grammar copies: k lexicon rows per word gives tuples linear in k (10->38 tuples at k=8) with traversal constant (8); m extra optional rules give ca and time linear in m (147->335 ca, 4.7->13.3 ms at +12 rules); combined k=4,m=6 yields 12 children per word and 108 tuples for a 9-token sentence, traversal still 13
- Lever assignment: engine fixes first (top_n exposure, lazy per-child semantics at icp:436/485, real MERGE and star guards, static rule pre-filter for the optional BFS at icp:464); prior-ordered DFS (Jev ideas 1 and 2) has nothing to order today and pays only once k x m fan-out exceeds about 4 and the first child stops winning
- Debts with lines: bare return 1 tie-break word_level_context_dag.py:115; alphabetical rule order dag_parser.py:126,156 and icp:464; silent top_n lexicon.py:370-373; generated Greek grammars; merge_unfixed; empty SA rules; hard-coded quickly; coq.py:47/:60; LaTeX AttributeError; strict not plumbed; _repoint_for_verb_lexical icp:41-60; hard-coded completion names icp:527-534; meta reset hack if_then_else.py:229-233; three byte-identical copies of 2015-english-ttr (md5 8e0684936553a67d0d18ab0bec124aa7); epsilon_term.py used only by induction

OPEN:
- Whether ?<u0>Ty(...) case-filter requirements actually block completion in the native backend was reasoned from Requirement handling (tree.py:626-636), not executed; needs a two-line probe before a case-bearing DP template is written
- The 64-attempt IF backtracking cap (if_then_else.py:240) cannot be observed without an edit; asserted unreachable because current rules bind at most one modality meta
- Timings are single warm-process runs; repeat 5x before quoting them in a doc
- How many children a real thesis grammar produces per word (clusters, VSO subjects via LATE *ADJUNCTION) is unknown until such a grammar exists; the synthetic k x m experiment is a proxy only
- LaTeX rendering of MLTT terms (design section 4) is absent; decide whether to add SemanticFormula.to_latex or route the workbench's unicode rendering into semantics_tex
- Whether to keep dialect as a grammar id (compile-time GATES) or introduce a runtime dialect parameter when hand-writing the thesis SMG grammar