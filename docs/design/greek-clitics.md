# Small Greek clitic grammars and the historical comparison

The workbench now ships Standard Modern Greek, Cypriot and Pontic fragments in
both classical and constructive semantics (`2026-{smg,cypriot,pontic}-{classical,mltt}`).
They are ordinary DyLan grammars: `icp(grammar)` runs them independently of the
workbench. The browser animates the same executed `make`, `go`, `put`, thinning
and elimination operations as for English. `scripts/build_greek_fragments.py`
is the shared, editable source; run it to regenerate the packaged grammar files.

## Executable scope

| Environment | Standard | Cypriot | Pontic |
| --- | --- | --- | --- |
| Bare finite clause | τον αγαπά | ιξέρω τον | ekser aton |
| Negation | δεν τον ξέρω | εν τον ιξέρω | ci kser aton |
| Imperative | γράφε το | γράφε το | Described in source, not in this lexicon |
| `na` | να το γράψει | να το γράψει | Not in this lexicon |

These are illustrations of the cited **weak object clitic** placement patterns,
with adaptations of spelling and vocabulary, not a new edition of source examples.
Greek and listed ASCII aliases are accepted; Pontic defaults to ASCII to keep the
source’s dialect forms distinct. NFC normalization preserves accents and combines
decomposed Greek characters. Greek question-mark punctuation is tokenized, but the
fragment has no separate interrogative speech-act semantics.

The small vocabulary contains third-person accusatives and pro-drop transitive
verbs. A clitic builds `01/010` (the fixed object argument), decorates it with an
entity formula, and returns the pointer to the clause root. A verb projects the
subject, predicate and object template. Consequently a preverbal clitic creates
the object before a verb exists; a postverbal clitic fills the verb’s open object
slot. No frontend word-order filter decides acceptance.

Placement is checked inside lexical IF conditions:

* Standard: `[↓₁⁺]?Ty(x) ∨ Mood(Imp)`.
* Cypriot: `(PROCL ∧ [↓₁⁺]?Ty(x)) ∨ (¬PROCL ∧ ⟨↓₁⁺⟩Ty(x))`.
* Pontic: `⟨↓₁⁺⟩Ty(x)`.

The imperative checks `[↓⁺]?∃x.Tn(x)` and absence of the particle trigger before
building fixed structure. A preceding accusative clitic therefore blocks it.
The dependent perfective nonpast `γράψει` is licensed after `na` here; it is not
conflated with the imperative `γράψε`.

**Explicit reductions from the thesis:** this is a positioning demo, not the full
situation-node system. Negation/`na` record a root `PROCL` feature and build an open
fixed subject slot. This stands in for the situation projection when testing the
imperative’s fixed-node restriction. Cypriot fronting/unfixed versus LINK strategies,
the full situation spine, tense/aspect, auxiliaries/climbing, relatives, full DPs,
doubling, gerunds and clusters/PCC are outside this grammar. Existing low-level PCC
tests elsewhere in the engine do not make those phenomena implemented here. The
extra `CLITIC` feature enforces this fragment’s one-clitic limit, not a linguistic
ban on clusters. A cluster failure is reported as a construction gap.

Context is deliberately fixed: `speaker`, `hearer`, pro-drop `pro`, `him`, and
`theme`. There is no native anaphoric substitution/context search in these entries.
Classical nodes carry `e/t` and lambda terms; constructive nodes carry `object/Prop`
and the native nominal theory. No TTR projection is involved. This pronoun-only
fragment introduces no quantifiers, so the resulting proposition can look the same
in both modes. Negative propositions retain `not`; `na` introduces an uninterpreted
`potential : Prop → Prop`. Imperative force and tense/aspect are not interpreted.
Constructive Coq exports are compiled in tests when `coqc` is installed.

## Failure is not grammaticality

Every result now supplies independent `diagnostics`:

1. **Parser result:** complete, accepted but incomplete, or stopped. The last
   accepted tree remains available on failure.
2. **Lexical coverage:** a per-token lookup for the entire input, including tokens
   after the first failure. This is vocabulary evidence, not an alternative parse.
3. **Linguistic evidence:** a sourced judgment for an identified comparison case,
   or `not_assessed`. Both arbitrary successes and arbitrary failures default to
   `not_assessed`.

`failure.kind` separates `lexicon_gap`, `construction_gap`,
`constraint_violation`, `semantic_type_mismatch` and `unresolved_parse_failure`.
Known words with no derivation do not automatically count as ungrammatical.
`constraint_violation` is used only when the parser fails on a negative member of
the bounded sourced comparison corpus. Judgment matching ignores terminal
punctuation and recognizes the listed aliases; it does not extrapolate to new
sentences. The annotation never influences the parser. If a model unexpectedly
accepted a recorded negative example, the independent fields would reveal the
disagreement, and the contrast tests would fail.

Examples:

* `το ζουζουνίζει.`: missing lexical entry; no grammaticality judgment.
* `το τον ξέρω.`: all entries known, but multiple clitics exceed this fragment;
  no PCC or grammaticality judgment.
* `ξέρω ξέρω.`: known-word parse failure with no recorded judgment.
* `τον`: accepted prefix with open requirements.
* `αγαπά τον.`: modeled Standard weak-clitic placement violation in this context.

## Historical explanation and sources

The Greek lab has four selectable historical panels: Koine/Hellenistic–Roman
evidence, medieval mainland → Standard, medieval Cypriot → Cypriot, and medieval
Pontic → Pontic. They are **explanatory panels, not executable historical grammars**.
They separate corpus evidence from the proposed DS explanation. Selected
Oxyrhynchus counts can be expanded; token counts remain observations, not rules.

The account presented is Chatzikyriakidis’s routinization proposal: pragmatic
placement preferences become lexical restrictions; generalization and possible
speaker/hearer mismatches between unfixed and LINK strategies expand proclisis in
the mainland trajectory. Cypriot broadens a more restricted unfixed trigger while
retaining the contrast with default enclisis. The Pontic trajectory instead loses
item-specific proclitic triggers and retains the generalized verb-parsed trigger.
This is not a demonstrated single cause of change. Corpus limitations, register,
chronology, regional Koine variation and disagreement between analyses matter.
The manuscript itself notes regional and evidential limits. No claims about all
modern Pontic/Romeyka varieties are inferred from the described Pontic fragment.

Sources consulted:

* Stergios Chatzikyriakidis, **The Historical Development of the clitic systems of
  Standard Modern, Cypriot and Pontic Greek**, local chapter manuscript
  `/Users/graogro/Dropbox/TEX/benjaminsvolume.tex`. Introduction: three modern
  placement systems and examples (lines 125–237); Koine variation, Oxyrhynchus
  counts and the pragmatic DS proposal (lines 239–328); medieval systems
  (lines 329–520); transitions and qualifications (lines 521–657). The executable
  corpus adapts the modern examples/patterns; no claim that all Greek spellings
  are verbatim in the phonologically transcribed source.
* Pappas (2006:323), Oxyrhynchus counts **as reproduced in that chapter**; the
  original publication was not independently consulted for this implementation.
* The existing extraction in `thesis-clitic-system.md`, especially entries
  (3.64), (3.73), (3.82), (3.102)/(3.104), for Standard/Grico triggers and the
  imperative cluster-order comparison. The source PDF was not reopened here.
* Further reading identified in the chapter: Chatzikyriakidis (2012), “A Dynamic
  Account of the Cypriot Greek Clitic Positioning System”, *Lingua* 122(6), 642–672;
  Chatzikyriakidis & Kempson (2011), Standard/Pontic person restrictions.

Grico and Cretan are discussed as further comparisons, with no executable
grammars claimed. The Salentino/Standard imperative cluster contrast is included
as a next extension. Cypriot focus/topic/prosody needs explicit readings and
source examples before it can be turned into categorical diagnostics.

## Verification

`tests/test_greek_workbench.py` checks ten positive/negative placement pairs in
both backends, direct engine parsing independently of diagnostics, strict grammar
loads, object creation/pointer movement, semantic negation, Unicode/aliases, Na
versus imperative, failure classifications and real Coq compilation. The browser
check covers comparison buttons, mode preservation, source panels, all diagnostic
categories, exports and mobile layout.
