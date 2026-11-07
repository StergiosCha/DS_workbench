# Subordination, quotation and dialogue: source comparison and implementation

7 November 2026. This review distinguishes the inspected source passages from
the current code and from proposed extensions. No manuscript `.tex` was edited.

## 1. Conditionals: the current relation template is not the published account

The workbench's native English/SMG clause family currently builds
`condition(main_content, antecedent_content)` through the effects in
`src/dylan/action/atomic/causal_effects.py`. Each clause closes its own content.
Postposed clauses grow a propositional LINK; initial clauses use a separate
curried construction with a comma boundary. This retains two contents and a
declared relation, but supplies no situation quantification, reference-time
relation, modal restriction or cross-clause accessibility theory.

The first source inspected was **Chatzikyriakidis (2010), §4.6.2,
printed pp.184–193, especially (4.47)–(4.53)**. This passage explicitly presents
Gregoromichelaki's conditional analysis and then revises it. It describes:

1. A LINK starting from a situation-argument position, not merely a completed
   proposition. The antecedent supplies a restriction on a situation term.
2. A τ binder with universal force over the antecedent restriction. This is
   choice-term machinery, not an instruction to insert an unrelated `forall`
   lexical constructor into the native Classical grammar.
3. In Gregoromichelaki's account as reported there, a formula-sharing requirement
   connects situation positions in the antecedent and consequent. The chapter
   points to Gregoromichelaki (2006), pp.196, 210 and 214.
4. Chatzikyriakidis changes the analysis so the subordinator leaves `?Ty(es)`
   for the verb to satisfy, making room for tense/aspect structure.
5. His revised LINK evaluation relates the antecedent situation to the
   consequent's reference time `R`, rather than simply identifying their highest
   situation nodes (p.192, (4.52)). The pointer returns to the main clause's
   propositional requirement.

This is a substantive architectural gap. Parsing `if` with the current opaque
binary predicate does not implement these accounts. The immediate prerequisite
is a situation-argument grammar and explicit LINK constraints, with separate
Classical, Constructive and TTR semantic implementations. The recent native
Classical nominal-choice closure is not itself an implementation of conditional
situation quantification.

**Primary-source follow-up:** the user located the 2011 chapter in Downloads as
`Conditionals.pdf` (41-page author copy dated May 2010). Its account was read
directly, including §§8.4.1–8.4.4 and the distinction between `if` and `when`
in (8.79)–(8.84). A separate **Classical conditional beta** now implements the
fixed-position situation/LINK/τ fragment. Its scope, postposed adaptation,
source locators and tests are documented in
[conditional-beta.md](../design/conditional-beta.md). The ordinary clause
templates described above are unchanged. The original 2006 thesis remains
unobtained; the 2011 author copy is not a substitute for auditing that thesis.

The follow-up also inspected the temporal-clause material in Chatzikyriakidis:
§2.2.2.4 (situation/reference-time structure), §4.2.1 (temporal subordinator
data), §4.2.2 (temporal versus contrastive `eno` and clitic order), §4.6.2
(revised situation LINK and pending `?Ty(es)`), and §3.4.3.2 (perfect auxiliary
structure). The beta design document records the exact pages and the remaining
temporal implementation obligations.

## 2. Chatzikyriakidis: subordinators also change local parsing conditions

The thesis's §4.6.2 and conclusion (pp.231–232) connect subordinate and
modality/tense environments with a pending situation argument as a proclitic
trigger. Causal `epiδi/γiati` are explicitly discussed as variation environments;
they cannot be reduced to a single undifferentiated conjunction trigger.

The inspected 2012 MGDLT5 poster **Clitic Positioning in Cypriot Greek Revisited:
Complex subordinators/markers with tze** supplies a particularly useful contrast.
`tze` creates a new propositional domain, so a previously introduced proclitic
trigger is no longer available in the domain where the clitic is parsed. Its
examples compare a simple subordinator with a subordinator-plus-`tze` sequence.
This is a structural locality analysis, not deletion of the previous marker's
meaning. The poster's example (2) has an English gloss inconsistent with its
Greek/transliteration; do not import that gloss as verified data.

Suggested regression family: minimal subordinator / subordinator + `tze`
contrasts, both clitic orders, and the coordinator used independently inside a
subordinate clause. These need the published situation/domain structure before
being claimed as implemented. The current small Cypriot trigger fragment is not
that full construction family.

## 3. Gregoromichelaki on quotation

Verified publication: **Quotation in Dialogue**, in *The Semantics and
Pragmatics of Quotation* (2017), pp.195–255,
[DOI 10.1007/978-3-319-68747-6_8](https://doi.org/10.1007/978-3-319-68747-6_8).
The full author manuscript was subsequently supplied in Downloads as
`Gregoromichelaki160117upload.pdf`: 74 pages, created 16 January 2017.
Its opening argument, §§7.1–7.3.3 and conclusion were inspected; the quotation
macros (95), (98), (117) and (133) were also inspected as rendered figures.
All quotation page locators below refer to this manuscript, not the published
pp.195–255. This supersedes the earlier abstract-only inspection.

A separate local manuscript, **Procedural Syntax and Interactions**, was read
at §2.1, PDF pp.2–4, especially examples (6)–(17) and the discussion of `run`.
It references the quotation chapter as forthcoming. The text proposes:

- word-by-word changes in the invoked utterance context and in which/whose
  grammar is used; quotation may be subsentential, interrupted, or jointly built;
- a higher-order `run` action parameterized by a grammar `g`;
- recording the executed action sequence and construing its demonstration as
  content of an appropriate type;
- keeping the actual utterance event distinct from the quoted/echoed event,
  including the interpretation of indexicals.

For that short manuscript, only the surrounding explanatory text was inspected.
The newly available full chapter supplies the more specific implementation
basis: (95), p.48, creates a demonstrated utterance through `run_g`; (98), p.50,
adds an echoed-event context; (117), pp.55–56, gives a direct-report `say`
macro with an event placeholder and LINK; and (133), p.62, connects the derived
content to the current predicted type. Quoted content and its actions remain
available for anaphora/ellipsis (pp.56–57). Indirect reports and mixed quotation
require independent, incremental changes in context and evaluation parameters
(pp.58–65). Not every quotation requires a fresh LINK: an already produced
utterance can supply the report's object from context ((126), pp.57–58).

**Current gap:** native speaker/addressee evaluation per word supports ordinary
shared dialogue, but there is no quotation-aware event/context representation,
quotation-specific grammar switch, or demonstration object carrying a `run`
action history. A stack alone would not implement the source's word-by-word
shifts. Normalized tokens also need exact source forms retained for citation.

**First quotation implementation to design:** direct quotation with explicit
context switching and restoration, preserving a separate quoted tree and action
trace. Authored target: `Mary said, “I walk.”` — `I` must refer to Mary within
the quote; unquoted `I` afterwards must again use the current participant. An
unclosed quote must leave a pending boundary. Follow-up targets are a quote
continued by a second speaker, mixed quotation, and pure quotation. This bounded
first stage would not be advertised as the entire published account. TTR must
retain its native record/context representation; equivalent native backends
need explicit quotation types, rather than treating quoted actions as ordinary
individual constants without explanation. The source-based derivation outline,
code audit, direct/shared quotation cases and main-grammar integration plan
are now in [quotation.md](../design/quotation.md). Quotation remains planned,
not an implemented feature. The paper supports a shared incremental account;
the initial bounded beta is an engineering staging choice.

## 4. Howes and colleagues: what is already present and what is missing

Sources inspected:

- **Eshghi, Howes, Gregoromichelaki, Hough & Purver (2015)**, *Feedback in
  Conversation as Incremental Semantic Update*, §§2.3–3.1, pp.265–267; §3.2
  and Table 1 as clarification design references.
  [ACL W15-0130](https://aclanthology.org/W15-0130/).
- **Howes & Eshghi (2017)**, *Feedback Relevance Spaces: The Organisation of
  Increments in Conversation*, §§2.3–2.4, pp.4–5, Fig.3.
  [ACL W17-6913](https://aclanthology.org/W17-6913/).
- **Howes & Eshghi (2021)**, *Feedback Relevance Spaces: Interactional
  Constraints on Processing Contexts in Dynamic Syntax*, §3.5, pp.343–345,
  Fig.6, and §§4–5 for the empirical scope.
  [DOI 10.1007/s10849-020-09328-1](https://doi.org/10.1007/s10849-020-09328-1).
- **Howes (2012)**, *Coordinating in dialogue: Using compound contributions to
  join a party*: title, abstract and contents inspected; not a full rereading.

The app already had shared tree completion, participant-sensitive local
reflexives, nearest-word self/other repair, retained earlier trees and polar
yes/no answers. It did not have the source-based `mhm/mm` lexical fragment,
clarification subdialogues, early/late feedback resolution, or the full model
of participant coordination pointers. The inherited `uhu` parser control is
not evidence that all this feedback behaviour was already implemented.

### Implemented now: local completion-based backchannels

The first extension implements the local semantic-unit constraint of HE21 Fig.6
in both native English grammars. `A: the man / B: mhm / A: walks.` continues
the same tree. Before consuming feedback, ordinary DS compilation must complete
the DP. A complete binary sister blocks the feedback action until further
composition has taken place. The action then leaves the completed subtree.
At a complete clause root, our adaptation records feedback without ascending
beyond the tree.

The UI's **Mid-sentence feedback** preset and `feedback_events` make the unit,
speaker and pointer movement visible during replay. This is a checked lexical
contribution, not skipped punctuation and not an LLM paraphrase. It preserves
quantifier composition and never turns a question into a positive answer.

Limits are deliberate and visible: no early/late-feedback recovery, no inferred
agreement, no participant-private coordination DAG, no grounding-based repair
lock, and no TTR lexical resource added in this patch. This is a native adaptation
of the published DS-TTR mechanism. `the / mhm / man` fails in this bounded
fragment, without a claim that every such natural dialogue is impossible.

### Recommended second extension: clarification with return to the pending tree

Use the source's Table 1 sequence:

```
A: the doctor
B: Chorlton?
A: no, Fitzgerald
B: uh-huh
```

The required implementation is a LINK to a trouble-source subtree, a tracked
pending clarification, and repair/confirmation followed by return to the
original open derivation. It must preserve the original contribution and the
candidate interpretation separately. This exceeds our existing `sorry + nearest
word` repair and the polar answer implementation. Start with local nominal
reprise clarification; then add backward search for an earlier completed unit
while retaining the interrupted continuation. Do not classify an arbitrary
question mark as a clarification or silently rewrite the antecedent.

## 5. Order of further work

1. Review the implemented backchannel fragment and its native adaptation against
   the source, then add participant coordination states before claiming grounding.
2. Implement local nominal clarification and resumption as the next dialogue
   feature, using the source examples and negative controls.
3. Review and extend the new fixed-position conditional beta. Add the unfixed
   strategies and use Chatzikyriakidis's reference-time/tense structure as the
   basis for a separately tested temporal fragment.
4. Add direct quotation context switching with inspectable quoted actions, then
   extend to joint and mixed quotation.

For each stage, keep a source/example locator, actual action program, successful
and failing contrasts, semantic output and separate backend status. LLM proposals
can help populate lexical alternatives; they do not substitute for these
mechanisms or establish that the published analysis has been implemented.

## 6. Verification of this patch

- 125 tests passed: backchannels, dialogue workbench, repair and native questions.
- 241 further tests passed: experimental-engine provenance, finite clause
  constructions, causal clauses, native semantics, Classical choice scope and
  workbench API behaviour. The frozen experimental state/action fixtures were
  retained; the grammar revision manifest records the additional lexical rules.
- Browser checks passed in Classical and Constructive: preset, replay visibility,
  source link, mobile overflow and the incomplete-DP failure. The initial browser
  launch was blocked by the macOS sandbox; the successful check ran with approval.
- JavaScript syntax, targeted Python lint, `git diff --check` and library
  consistency passed for the feedback patch (54 works and 9 analysis cards).

Follow-up conditional beta: 177 focused tests passed across the new grammar,
Classical choice scope, clause constructions, API and feedback; the dedicated
browser check also passed. Its limits are in the beta design document.
The subsequent quotation review adds a source-based analysis card and records
the full author manuscript; it does not add parser coverage.

## 7. Two Howes papers: feedback and laughter

The user's publications list led to a second implemented dialogue fragment:
**Maraev, Eshghi, Mazzocconi & Howes (2026), Incremental Processing of Laughter
in Interaction**, DOI 10.3390/languages11020025. The published 22-page PDF was
inspected, particularly §4 and the rule/trees on pp.13–14. Paired with Howes &
Eshghi (2021), it motivates a useful comparison between a backchannel and
laughter about a completed individual or situation.

The separate **TTR laughter beta** now constructs a LINK, preserves its target's
identity and conjoins `laughable(target)` into the TTR record. It supports
shared continuation after nominal laughter and two alternative targets in
`John sees a telescope [laugh].` This is the local backward-looking case only;
forward/distant resolution, participant grounding and interpretation as humour
remain outside the implemented scope. No Classical/Constructive laughter
semantics has been added. The existing native backchannel fragment remains
separate.

[laughter-beta.md](../design/laughter-beta.md) gives the two papers, concrete
dialogues, implementation details, source adaptations and next extensions.
All 23 focused laughter tests and its actual browser check passed. The library
now records 55 works and 11 analysis cards, including the full quotation source
and the bounded laughter implementation. Production deployment is separate.

The implementations, source notes and checks are maintained in `DS_workbench`.
Repository publication does not establish a production deployment.
These are focused regression checks, not a new evaluation of open-text coverage.
