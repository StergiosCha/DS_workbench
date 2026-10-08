# Review of Fable's DS library expansion — 8 October 2026

Reviewed the working-tree return described in
[`ds-library-expansion-2026-10-07.md`](ds-library-expansion-2026-10-07.md) and
`.claude/handover/2026-10-07-ds-library-expansion.md`. This review records findings;
it does not change Fable's records or the parser.

Publication follow-up, later on 8 October: findings 1, 2, 3 and 5 below were
corrected while preparing `StergiosCha/DS_workbench`. All 11 library browser
checks now pass. The unavailable OpenAlex artifacts in finding 4 remain open;
the expansion report now states that limit. The original observations below
describe the pre-correction snapshot.

## Repository status

The local Git repository is
`/Users/graogro/Dropbox/revisiting-formal-semantics/DynamicSyntax`, on branch
`constructive-ds`, at commit `84f28d8` (1 October 2026). Its only configured
remote is `origin`, https://github.com/incrementaliser/DynamicSyntax.git.
There is no separate workbench remote configured in this checkout. Recent
application and research work remains modified/untracked, including Fable's
return. This observation does not establish whether another repository exists
elsewhere on GitHub.

## What was delivered

The canonical data contains 53 works, 30 fingerprinted PDF versions and eight
cards: increases of 18 works, 15 versions and three cards. The three new cards
are preliminary readings about Spanish clitic history, Greek clitic history
and distributional semantics. They contain no extracted construction examples
or executable implementation specifications.

The additions include the remaining four articles from the JoLLI 30(2) DS
special issue, nine SemDial contributions, a Spanish clitic-history chapter,
and four discovery admissions. Three existing works gained source versions
and abstract readings. The old discovery queue now has five unresolved items.

The handover explicitly records that the user narrowed the task to research
and library work and then requested wrap-up. It reports no parser changes,
code audit, new implementation, or full readings of new works. Those omissions
should be understood against that narrowed scope, not treated as claimed
completed work.

## Findings needing correction

1. **KCC15 author order is wrong in the canonical record and exports.**
   `papers.json` lists Kempson, Chatzikyriakidis, Cann. The downloaded PDF of
   [The interactive building of names](https://semdial.org/anthology/Z15-Kempson_semdial_0035.pdf)
   has Chatzikyriakidis, Kempson, Cann. Its SHA-256 matches Fable's recorded
   version. The report, lines 88–89, says it followed that byline, but the data
   does not. Correct the canonical author order and regenerate the exports.

2. **The report overcounts new works with PDFs.** Lines 24–25 say 15 of the
   18 additions have PDFs and three are metadata-only. The records actually
   contain **12 new works with PDFs, five metadata-only additions, and one
   abstract-only addition without a PDF (PSHK21)**. The other three new
   fingerprints belong to existing PGMC10, SPHK18 and HE17 records. The total
   of 30 fingerprinted versions is correct.

3. **The browser regression checker fails with the expanded data.**
   `scripts/check_ds_library_browser.py:33` assumes `#C10 .analysis` selects
   one element. C10 now has both the PCC card and the Greek historical card,
   causing a Playwright strict-locator failure. Target the PCC card's existing
   `data-analysis="smg-pcc-acc12"` attribute and rerun the browser checks.
   This is a test assumption exposed by the expansion; the failure does not
   itself show that the browser UI is broken. Fable correctly disclosed that
   it did not run browser verification.

4. **The OpenAlex sweep is not reproducible from this handover alone.**
   The report says the query list is recorded, but the repository contains
   only broad search descriptions. The actual script, exact query list and
   2,033 raw candidate records are reported as held in the cloud session's
   scratch space. Retrieve those artifacts or describe the sweep as a
   reported, unavailable discovery pool. Do not count those records as
   screened or reviewed literature.

5. **The UI's aggregate label is stronger than the new cards' evidence.**
   The template labels all eight cards “bounded analysis cards”; the three
   additions explicitly describe themselves as abstract/introduction-level
   reading cards. A neutral aggregate label or a separate card-stage field
   would preserve that distinction. Their scope notes are already visible.

## Checks performed in this review

- `scripts/build_ds_library.py --check` passes for the 53-work edition.
- All eight recorded expansion artifact hashes match the current files.
- Pandoc round-trips all 53 BibTeX records with identical IDs, titles, full
  author arrays and issued dates relative to the CSL export. This checks
  consistency between exports, not correctness against the publications.
- Independently retrieved four primary PDFs: C20, SPHK18, KGG07 and KCC15.
  All four hashes and page counts match their records. Inspected title pages
  and opening abstracts/introduction; this is a spot check, not a full review
  of all 18 admissions. C20's 2020 online date and 2021 issue are explicit in
  its PDF; SPHK18's abstract supports the tensor-contraction summary.
- The browser checker loads all 53 works, then stops at the ambiguous PCC
  locator above. Its subsequent checks were not reached. Output directory:
  `/tmp/ds-library-review-20261008`.
- No parser tests or live model requests were needed for this bibliographic
  review. No deployment or Git publication was performed.

## Assessment

This is a useful bibliography expansion with explicit reading limits. It is
not yet the deeper source-to-implementation study. Correct the metadata and
reporting issues, then prioritize full readings of C20 and the modification,
auxiliary, conditional and ellipsis sources already queued. The next milestone
should be source-located mechanisms, actual examples and separate semantic
obligations for each backend, rather than another increase in title count.
