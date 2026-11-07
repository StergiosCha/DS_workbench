# Laughter and feedback: two dialogue papers put to work

7 November 2026. Use **Try laughter in dialogue · TTR Beta** in the app.
This selects `2026-english-laughter-beta-ttr` and an executable dialogue.
The ordinary native English grammars separately provide the **Mid-sentence
feedback** preset. No model account is needed for either fragment.

## The two sources

1. **Howes & Eshghi (2021), Feedback Relevance Spaces: Interactional Constraints
   on Processing Contexts in Dynamic Syntax**, *Journal of Logic, Language and
   Information* 30(2), 331–362.
   [DOI](https://doi.org/10.1007/s10849-020-09328-1).
   Inspected §3.5, pp.343–345 and Fig.6, with the early/late distinctions and
   examples in §§5–6. Backchannels can occur after a completed semantic unit
   while the larger sentence remains unfinished. The broader account also
   addresses prediction, clarification, coordination and repair.
2. **Maraev, Eshghi, Mazzocconi & Howes (2026), Incremental Processing of
   Laughter in Interaction**, *Languages* 11(2), 25.
   [DOI](https://doi.org/10.3390/languages11020025).
   Retrieved via the publisher's PDF host after the article page returned 403.
   Inspected §§1–2.3, relevant DS-TTR background in §2.5, §§4–5; lexical rule
   (6) and Figs.6–7 were visually inspected on pp.13–14. The formal proposal
   treats laughter as pointing to a laughable and supplies `laughable(head)`
   on a LINKed tree. It covers several resolution strategies using shared DS
   machinery. The paper explicitly calls its treatment theoretical (§2.5.2).

These are complementary DS-TTR analyses. The feedback implementation in the
workbench is a native Classical/Constructive adaptation. The new laughter
fragment uses TTR directly. Neither establishes implementation parity across
all three semantic systems.

## What to try

All examples here are authored implementation controls, not corpus quotations.

### Feedback without agreement

In either ordinary native English grammar:

```
A: the man
B: mhm
A: walks.
```

DS composes the determiner and noun before accepting `mhm`, records B's feedback
on that unit, and continues the same tree. The whole sentence is still
incomplete at the feedback point. Compare:

```
A: Did John walk?
B: mhm
A: No
```

The backchannel does not turn the query into an assertion or a positive answer.
The final `No` provides the negative answer. Our implementation records an overt
backchannel; it does not implement the source's participant coordination DAGs,
grounding-based pruning or a proof that B understood. Early feedback such as
`the / mhm / man` remains outside the fragment, although the source discusses
predictive feedback and does not generally prohibit such conversational cases.

### Laugh at what was said

In the TTR laughter beta:

```
A: John likes Mary.
B: [laugh]
```

After the clause has been compiled, its record identifies a liking situation
`e0` with John as subject and Mary as object. Laughter creates a LINK carrying
`laughable(e0)` and a requirement to evaluate that LINK. The existing
`link-evaluation` rule conjoins this into the record. John, Mary and the liking
situation retain their identities. B's actual contribution remains visible in
the dialogue trace. The predicate leaves the social interpretation open:
embarrassment, amusement, mockery or something else is not inferred.

### Laugh, then let the other person finish

```
A: a man
B: [laugh]
A: arrives.
```

Here the target is the completed nominal record's head, `x0`, so the LINK
contributes `laughable(x0)`. A then supplies the predicate. The arriving event
and its subject are composed normally, retaining the laughter information.
`a man [laugh]` alone remains an incomplete sentence.

### Two readings without changing the words

In Sentence mode enter:

```
John sees a telescope [laugh].
```

Request **Up to 3 analyses**. Two complete analyses are available:

- After composing the object DP, laughter targets the telescope: `laughable(x1)`.
- After composing the clause, laughter targets the seeing situation:
  `laughable(e0)`.

Both retain `subj(e0,x0)`, `obj(e0,x1)` and `telescope(x1)`. The first result
is not labelled the intended reading. Resolving that ambiguity requires more
context; grammar completion alone does not settle it. Dialogue mode currently
returns only the first complete analysis, as in the rest of the workbench.

## How the beta differs from the full source

The new effect resolves **only the immediately pointed, complete record**.
It copies that record onto a LINK with the same head and a fresh laughter field;
copying the dependencies keeps its referent bound. Ordinary record conjunction
then incorporates the contribution. It does not freshen John, the telescope,
or the event when copying them. The LINK type follows the semantic head:
individual `e` or situation `es`, even when the containing clause is `Ty(t)`.

This is a direct local-resolution adaptation of §4.2/Fig.7, not an executable
transcription of the general rule (6). In particular, we have not added the
unresolved anaphoric/cataphoric placeholder, Late-*Adjunction, MERGE and distant
SUBSTITUTION routes described in §§4.1–4.3. Laughter before its target therefore
does not parse in this beta. Existing LINKs cannot be overwritten, and repeated
laughter at the same already linked position is outside its bounds.

The small English grammar builds TTR records with the inherited interpreter,
freshening, Introduction/Prediction, function application and LINK evaluation.
It does not import the entire 2015 lexicon or silently supply tense, agreement,
definite descriptions, questions, quotation or discourse resolution. Explicit
`[laugh]` is a transcript token, not audio recognition. Speech-laughter overlap
and nonlinguistic laughables are not represented. AI and personal-rule expansion
are disabled; paragraph segmentation is not part of this beta.

The paper's coverage numbers describe categories of annotated laughter, not
parser accuracy. Its abstract says approximately 87%; §4 prints 88.07%, while
Table 5's included counts give (696 + 475) / 1345 ≈ 87.06%. We do not repeat
those figures as workbench performance or claim to have reproduced the corpus
analysis. The authors also state that the interpretation of `laughable` and
laughter relevance spaces require further work (§5).

## Next extensions justified by these sources

1. **Forward laughter:** the source's `… [laugh] a telescope` example
   (§4.1/Fig.6). Introduce a pending referent and LINK, parse the following NP
   on a late unfixed node, then MERGE and evaluate. It must stay unresolved
   if the NP never arrives; skipping `[laugh]` is not an implementation.
2. **Earlier targets:** retain alternative completed units in context and use
   typed SUBSTITUTION for distant laughter (§4.3), or for late feedback in the
   Howes–Eshghi account. Record the selected antecedent and preserve ambiguity.
3. **Clarification and return:** LINK to a trouble source, accept a confirmation
   or correction, then return to the interrupted derivation. `mhm` and a
   clarification must have different effects. The existing nearest-word repair
   and simple polarity answers do not yet provide this whole mechanism.
4. **Connect to quotation:** laughter at words, a manner of speaking or a quoted
   performance needs the demonstrated utterance/action representation described
   in [quotation.md](quotation.md), not just an individual or event head.

## Code and checks

- `src/dylan/action/atomic/ttr_laughter.py`: complete-target guard, shared
  referent/event identity, fresh laughter field and atomic LINK operations.
- `src/dynamicsyntax/grammars/2026-english-laughter-beta-ttr/`: explicit small
  TTR grammar; all declared lexical rows must load successfully.
- `tests/test_ttr_laughter.py`: 23 checks of composition, target ambiguity,
  incomplete/unsupported cases, multiple fields, actual dialogue participants,
  streamed rule execution, backend isolation and request restrictions.
- `scripts/check_laughter_beta_browser.py`: actual beta button, presets, model
  controls off, alternative readings, mobile layout, failure and return to the
  ordinary grammar. Passed; Chromium required the approved sandbox exception.
- `tests/test_backchannels.py`: the native feedback contrasts above, including
  preserving a question until its separate negative answer.

These checks validate the bounded fragments, not general coverage. Production
deployment is tracked separately from the repository implementation.
