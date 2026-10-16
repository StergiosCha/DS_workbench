# Frontend review — 16 October 2026

Reviewed the public app at 1440×1000 and 390×1000, including the initial parse,
expanded examples, model drawer and a missing-word failure. Production was
`dpl_BDJW8eMirph6seGykH92HRzoyC3Y`. This is a usability review and proposal,
not a new frontend implementation or a linguistic-coverage evaluation.

The workspace tabs, explicit LLM/Jev switches, grouped evidence and model drawer
are useful foundations. No horizontal page overflow appeared in these checks.
The next changes should make the result easier to reach, understand and share.

## 1. Give the tree a focused view

In the inspected initial state, the tree canvas began roughly 815px down the
desktop page and 1469px down the mobile page. The derivation section starts
earlier; these are canvas coordinates, not the earlier section-height metric.
The input, examples, AI controls, result-use bar, completion banner and replay
controls all precede the actual tree.

Add an explicit **Focus on derivation** action that gives the tree, meaning and
current rule most of the viewport, with a compact sentence/backend strip and
an obvious return to editing. Keep playback controls reachable while scrolling.
Offer fullscreen for teaching. Preserve zoom, selected step and the model
permissions when entering or leaving this view.

## 2. Make the endpoint the resting result

A completed parse can initially sit at the axiom, alongside a complete-result
badge, an earlier-frame explanation and an empty root meaning. Failures also
replay from the axiom rather than initially showing the point where parsing
stopped. The explanations are accurate but demand unnecessary interpretation.

After parsing, settle on the final completed tree or failure state. Keep
**Replay from start** prominent and preserve access to Words, Rules and
Operations. Incremental events can still appear while parsing; an intentional
replay should not obscure the result afterward. Use one compact status area
for the endpoint, current playback position and actual model usage.

## 3. Improve sentence entry and example discovery

Sentence mode uses a single-line input. A longer sentence scrolls horizontally,
particularly at the mobile field's measured 340px width. Use a small textarea
that grows to a few lines, retaining the separate Paragraph mode and its limits.

The English example expansion currently reveals 23 flat buttons. Group examples
by construction: nominals/scope, verb frames, PPs, relatives, clause relations,
and dialogue where applicable. Show the supported backend and offer labelled
contrasts that demonstrate a construction's boundary. Use reviewed existing
examples; this interface work must not invent grammaticality judgments.

## 4. Explain the current computational step

The rule trace already shows `intro-pred`, lexical actions, pointer motion and
changed decorations. Add a short, deterministic explanation alongside the
technical rule: for example, “Create subject and predicate requirements” for
the reviewed introduction/prediction action, or “Move to an unfinished child”
for an applicable anticipation action. Keep the exact program one click away.

Explanations should be tied to actual rule/effect identifiers and their executed
branch. Use a neutral fallback for unknown actions; an LLM is unnecessary for
explaining the rules already in the grammar.

## 5. Turn a failure into a useful community contribution

The missing-word example reports the gap and offers Inspect failure, but a
visitor must work out how to send the result to the project. Add **Report this
result** beside the diagnosis. Prepare an issue with the input, backend/grammar,
settings, source version, failure/limit status and a prompt for the expected
interpretation. Let the user review the text before opening/submitting an issue;
copying the report should work without a GitHub account.

Keep a lexical gap, an open requirement, a diagnosed constraint and a timeout
distinct. Offer actions justified by the diagnosis: inspect the relevant rule,
choose a documented example, or explicitly enable model assistance for an
eligible gap. Enabling AI must remain a deliberate choice and never imply that
the model can invent unsupported grammar.

## 6. Let researchers retain and compare work

The app exports JSON but has no obvious workspace for reopening saved analyses.
An import/view flow would let colleagues inspect a shared result without a fresh
model call. Mark imported results with their grammar/source version and preserve
the original data. A later comparison view could place Classical and Constructive
results side by side; show unequal coverage and different meanings explicitly.
TTR should remain an independently selected and evaluated grammar.

## Recommended implementation order

Start with the focused tree view, endpoint/replay behaviour and multiline
sentence entry. Then add grouped examples, rule explanations and report-a-result.
Saved analyses and backend comparison need a separate design for versions and
state, so they should follow those smaller changes.

For each increment check desktop/mobile, keyboard use, sentence/paragraph/dialogue
state, explicit model permissions, imported/exported data where relevant, and
the distinction between the final result and the selected replay step. No new
grammar coverage is implied by these presentation changes.
