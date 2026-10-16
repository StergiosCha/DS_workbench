# Grammar workshop: from a proposal to a reusable grammar

Experimental results now have **Edit & keep rules**. The workshop lets a user
edit lexical conditions, actions and semantic declarations, add regression
examples, and save the resulting pack in the browser. **My grammars** reopens
saved packs. This is available for native English and Standard Modern Greek,
separately for Classical and Constructive DS. TTR, paragraph and dialogue packs
are not supported.

## Use and review

1. Generate an experimental proposal or import a contribution JSON file.
2. Edit the word-triggered programs and their explanations. Record the intended
   analysis, source evidence and changes in the notes.
3. Add positive examples and counterexamples. Optionally require an exact
   normalized meaning for a positive example. Change this expectation explicitly
   when changing the intended semantics; the app does not rewrite it to agree
   with an edited rule.
4. **Check with DS · no AI** compiles the edited programs and runs every example.
   Unknown words, timeouts and search limits cannot establish a passing negative
   result. Editing anything invalidates the previous check report.
5. **Save to my grammars** stores a compilable pack, including failing examples
   if further work is needed. It does not certify the analysis. Close the workshop,
   select the pack and tick **Use my rules**. This disables both models and uses
   the saved rules on the next sentence. Refreshing retains saved packs but turns
   their use off. Export a copy for backup or community review.

The personal result shows the original grammar's result, the selected personal
rules and their programs. A complete personal derivation is labelled as such;
it is not counted as acceptance by the maintained grammar. A diagnosed PCC or
other explicit constraint violation prevents an overlay from being applied.

Storage is local to the browser and site, not a server account. Up to ten packs
can be saved; each contains at most eight regression examples and 24 KB of data.
A pack is tied to a grammar/backend and its file hash. A changed base grammar
requires review and an explicit rebase; there is no automatic migration that
silently accepts changed assumptions. The current UI does not perform rebasing.
Imported check reports are discarded and checked again before saving.

## Backend and standalone contributions

`workbench/grammar-workshop.js` owns the editor, local storage and request controls.
`dylan.grammar_workshop` validates the pack and uses the same bounded compiler as
experimental proposals. It accepts new lexical programs, not Python, new atomic
operations or changes to computational rules. Request isolation remains the
ordinary server worker boundary.

Each replay starts with a fresh parser and a model-free dictionary/corpus baseline.
The pack's programs are tried before the original alternatives. Original seed
words seed vocabulary declarations only; they do not inject words into the new
sentence or establish discourse context. The semantic profile and action language
are those of the selected backend. All input and tree requirements still matter.

Download the contribution pack, then run from a source checkout with the pinned
WordNet index installed for English:

```sh
uv run python scripts/review_grammar_pack.py ds-grammar-contribution.json
uv run python scripts/review_grammar_pack.py ds-grammar-contribution.json --output /tmp/my-ds-grammar
```

The second command requires passing positive and negative checks. It creates a
new standalone grammar directory, including lexical support declarations, the
pack and review results. It then loads the serialized grammar through the public
API and checks the examples again. Existing directories are never overwritten.
If that final check fails, the output is an unfinished artifact to inspect, not
a successful contribution. Load a successful build with
`dynamicsyntax.parse(sentence, Path('/tmp/my-ds-grammar'), strict=True, top_n=0)`.

Shared incorporation is a normal reviewed source change: justify the DS analysis,
check meanings and overgeneration, test relevant backend and construction
interactions, and add the family to the maintained regression suite. Passing a
user-supplied example set is evidence, not independent linguistic validation.

## Verification

`tests/test_grammar_workshop.py` checks real replay, isolation, invalid programs,
stale grammar hashes, mismatched meanings, inconclusive negatives and standalone
serialization in both backends. `scripts/check_grammar_workshop_browser.py` uses
a fixture proposal but real backend checks: edit, save, export, reuse on new
sentences, refresh, disable, invalidate a report, remove a pack and mobile layout.
It asserts that these requests carry no model authorization.
