# Authorized lexical, search and construction expansion

User request, 2026-09-30: add a give template and execute items 1, 2 and 3 of
the wide-coverage proposal. Work inline, in visible commits, with classical
and constructive meanings and operation playback preserved.

## Work items

- [x] Give-family templates: double object and obligatory `to` recipient;
      three-place predication, quantifiers, negatives and Coq tests.
- [x] Initial English morphology-backed lexical candidates and reusable frame inventory;
      retain alternative senses/valencies, source provenance and validation.
- [x] Jev entry and derivation ordering using prefix/tree/dialect state;
      no candidate pruning, caching, offline replay, measured calibration,
      frontend decision controls and audit visibility.
- [x] Optional dictionary-first Jev lexical mode: separate sense/frame choices,
      validated native templates, bounded prefix-only model fallback, durable
      cache, lexical accuracy benchmark and frontend preferred/used distinction.
- [x] Initial PP construction family: postverbal in/at/companion-with modifiers,
      selected on-complements, chained LINKs, scope/negation and both semantic modes.
- [x] Incremental sense reconsideration with bounded DS replay, preserved alternatives
      and visible revision controls. Runtime frame classification is retired; the
      historical factorized benchmark remains available.
- [ ] Further construction growth: PP attachment/polysemy, auxiliaries/passives,
      additional quantifiers, coordination, wh and broader relatives.
- [ ] Greek construction growth: expand the existing scrambling/CLLD
      fragment, relatives/clitic environments, climbing and dialect rules
      using source evidence and morphology rather than spelling analogy.
- [ ] Group uncovered examples by missing family; keep model suggestions
      separate from parse outcomes and independent grammaticality evidence.
- [ ] Full regressions, corpus floors, browser playback, updated handover.

The user supplied an OpenRouter key. Jev's native typed API and DeepSeek Flash
lexical proposals now work through that key; a separate TypeSafe key is not
required. The server loads the ignored `.env`. See `openrouter-jev.md` for
configuration, source documentation, live checks and current limits.
The first 344-case calibration is complete (`jev-calibration-2026-09-30.md`).
It found no reduction in backtracking, so automatic search preferences remain off.
Replay tools, typed answer archives and measured UI status are available.
The separate opt-in lexical mode is documented in `jev-lexical-selection.md`.
Its small development benchmark improved sense selection (30/31 versus 10/31)
but not frame selection (22/26 versus 24/26); no broad accuracy claim is made.
The full construction and Greek expansion requests above remain unfinished.
Current PP and revision limits and validation: `pp-and-revision.md`. General PP
polysemy and NP attachment remain open along with the broader construction track.

## Give checkpoint

The native English grammars now have `ditransitive(PRED,AGENT,RECIPIENT,THEME)`
and `dative-to` templates. Both compose `PRED(giver, recipient, theme)`; the
second surface order requires `to` before the recipient. Base-form variants
also work after do-support. `give/gives/gave` and `book` are executable;
model proposals can instantiate other verbs with their own predicate names.

Quantifier lifting retains every remaining argument of a curried predicate,
so quantified themes and recipients combine compositionally. Classical DPs
retain their CN/epsilon/tau structure; constructive meanings compile in Coq.
Each argument is a real node, visited by the pointer. Tense and agreement
remain separate construction work; the initial give increment does not
claim to distinguish the temporal meanings of give/gave.

Focused give/relatives/native-semantics/lexical-expansion validation: 180
passed (`/tmp/ds-give-focused.log`). Tests include missing arguments,
mandatory preposition, local negation, relative embedding, selectional
types and reusable `lend` meanings. Ruff and diff checks passed.
