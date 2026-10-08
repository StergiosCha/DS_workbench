# DS library expansion: search, screening and reading queue (7 October 2026, evening)

Scope agreed with the user: research and library work only (sections 2 to 5 and 10 to 11 of the
7 October brief as they apply to the bibliography). No parser, grammar, UI or deployment change was
made. The run was cut short at the user's request; this report preserves what was verified, what
failed, and what remains open. It is the written counterpart of the record changes in
`library/papers.json`, `library/analyses.json`, `library/discovery.json` and `library/validation.json`.

Snapshot inspected: the working tree at `/Users/graogro/Dropbox/revisiting-formal-semantics/DynamicSyntax`
on branch `constructive-ds` with 203 modified or untracked entries, all preserved. The public
application was not inspected in this pass.

## 1. What changed, in numbers

| Measure | Before | After |
| --- | --- | --- |
| Selected works | 35 | 53 |
| Fingerprinted PDF versions | 15 | 30 |
| Analysis cards | 5 | 8 (three new cards are abstract-level reading cards, labelled as such) |
| Review statuses | 9 selected passages, 1 overview, 1 full short paper, 6 abstract, 1 metadata only, 17 citation only | 9 selected passages, 1 overview, 1 full short paper, 22 abstract/first page, 6 metadata only, 14 citation only |
| Crossref discovery queue (25 records) | 8 catalogued, 4 excluded, 13 needing screening | 12 catalogued, 8 excluded, 5 needing screening |
| Non-DOI leads | 0 | 6 |

Reading depth is the honest limit of this pass. Eighteen works were admitted: 12 have fingerprinted
PDFs, five are metadata-only, and PSHK21 has an inspected deposited abstract but no PDF. The other
three new fingerprints belong to existing PGMC10, SPHK18 and HE17 records. No
new work was read in full. No existing citation-only work was upgraded to a selected-passage reading.
The 91-topic catalogue in `ds-theoretical-coverage.json` was not changed.

## 2. Search services actually used, and failures

| Service | Use | Outcome |
| --- | --- | --- |
| Crossref works API | DOI records with deposited abstracts for the 13 queued candidates and new works; journal listing for ISSN 0925-8531 | All records retrieved; the complete JoLLI 30(2) (2021) Dynamic Syntax special issue was identified (eight articles, pp.263–449) |
| OpenAlex works API | Title/abstract phrase searches, author-name searches, forward citations (`cites:`) and referenced works of 12 core DOIs | 134 requests, 83 non-200 (rate limiting and timeouts), 2,033 raw candidate records; the sweep was stopped before completion and the raw files were kept outside the repository. Nothing from it was promoted; it remains an unscreened pool |
| Semantic Scholar graph API | Paper search by title for 14 citation-only works | Empty results for 13 queries (probably rate limiting); one hit supplied the Lingua DOI for GI16 and a SOAS repository URL |
| SemDial anthology (semdial.org) | Author pages for Kempson, Cann, Gregoromichelaki, Eshghi, Purver; PDFs | Pages fetched; 11 PDFs downloaded; two older files (2004, 2006) returned 404 |
| ACL Anthology | W17-6913 PDF and BibTeX; W19-09 workshop volume | Retrieved |
| Springer | OA PDFs for K20, C20, NC21, HE21, HG21 | Retrieved; SE21, YW21 and PSHK21 returned HTML (subscription) |
| MDPI | C25, CL25 PDFs | Retrieved (already fingerprinted in the first edition) |
| Ghent University repository | Bouzouita 2008 chapter | Retrieved (41-page author copy with citation cover page) |
| QMRO (Hough 2014 thesis) | Record 123456789/9094 | Metadata confirmed via a web fetch; no file attached; direct requests returned 403 or empty replies |
| SOAS Research Online / Worktribe (Gibson 2012, 2016) | Author listing; thesis DOI 10.25501/SOAS.00016637 | Listing fetched; repository records and PDFs returned 403 |
| UCL Discovery (Purver et al. 2021 accepted manuscript) | PDF | 403 |
| Edinburgh ERA | Tugwell 1999 thesis record | Metadata only; no file |

The original DS website was not retried. Web search engines were used only to locate repository
pages. No model calls were made for research; no credentials were used.

## 3. Admitted works

JoLLI 30(2), 2021, the Dynamic Syntax special issue. Four of its eight articles were already catalogued
(HG21, NC21, HE21, SE21). The other four are now records:

- **PSHK21** Purver, Sadrzadeh, Kempson, Wijnholds and Hough, *Incremental Composition in Distributional Semantics*, pp.379–406. Abstract read (Crossref). Successor to SPHK18.
- **K20** Kiaer, *Left-to-Right Asymmetry and Early Association in Korean*, pp.363–378, published online 7 October 2020. OA PDF fingerprinted; abstract read.
- **C20** Chatzikyriakidis, *Underspecification, Parsing Mismatches and Routinisation: The Historical Development of the Clitic Systems of Greek Dialects*, pp.277–304, published online 20 August 2020, CC BY 4.0. OA PDF fingerprinted; abstract read.
- **YW21** Yang and Wu, *A Dynamic Analysis of Minimizers in Chinese lian…dou Construction*, pp.429–449. Metadata only (no abstract deposited; subscription PDF).

SemDial anthology works, each with a fingerprinted PDF and a first-page/abstract inspection:
**E15b** Eshghi 2015 (DS-TTR parser demo); **HP12** Hough and Purver 2012 (self-repairs in an incremental
type-theoretic system); **KGG07** Kempson, Gargett and Gregoromichelaki 2007 (clarification requests;
printed pp.65–72); **GGHS08** Gargett, Gregoromichelaki, Howes and Sato 2008 (dialogue-grammar
correspondence); **KGP09** Kempson et al. 2009 (how mechanistic can accounts of interaction be);
**KCC15** Chatzikyriakidis, Kempson and Cann 2015 (interactive building of names); **G19**
Gregoromichelaki et al. 2019 (vector space semantics, position abstract); **G20** Gregoromichelaki et
al. 2020 (affordance competition and syntactic universals); **K21** Kempson 2021 (invited-talk abstract).

Other admissions: **B08b** Bouzouita 2008, *At the Syntax-Pragmatics Interface: Clitics in the History
of Spanish*, in Cooper and Kempson (eds), *Language in Flux*, College Publications, pp.221–263 (OA
repository copy; introduction read; distinct from the thesis B08, whose title as cited in KC16 is
confirmed). From the discovery queue, by metadata only: **MK06** Marten and Kempson 2006 encyclopedia
entry; **W17** White 2017, *Dynamic Syntax and Proof Theory*, Theoretical Linguistics 43(1–2):135–140;
**G16** Galery 2016 on deferred pronouns; **N09** Nakamura, Yoshimoto, Mori and Kobayashi 2009 on Japanese
multiple-subject constructions.

## 4. Corrections and upgrades to existing records

- **PGMC10**, **SPHK18**, **HE17**: readable published versions located and fingerprinted (SemDial 2010,
  SemDial 2018, ACL Anthology W17-6913); status raised from citation-only to abstract read; venue strings
  made precise. HE17's BibTeX gives no page range; the record does not invent one.
- **GI16**: DOI 10.1016/j.lingua.2016.06.003 added (Crossref verified: Lingua 184:79–103).
- **GI12**: SOAS thesis DOI 10.25501/SOAS.00016637 added; no PDF inspected.
- **H14**: QMRO handle added; the record has no file attached.
- **B08**: note added separating the thesis from the 2008 chapter.
- **SE21**, **HG21**, **NC21**, **HE21**: special-issue placement recorded.
- Title discrepancy recorded: the SemDial index lists Z07-3013 as "Incremental Fragment Construal"; the
  PDF's printed title is "Clarification Requests: An Incremental Account". The printed title is used.
- Author-order discrepancy recorded for KCC15 (index lists Kempson first; the PDF byline is
  Chatzikyriakidis, Kempson, Cann; byline used).

## 5. Discovery screening decisions

Excluded with reasons: Grohmann 2003, chapter 8 of *Prolific Domains* (Minimalist monograph; "dynamic
syntax" is the author's derivational notion); Amizern et al. 2024 and Aciar et al. 2024 (LLM syntax
frameworks, abstracts verified); Piriyeva 2021 (stylistic-syntax tradition; provisional, no abstract
read). Still needing screening: the three Tugwell papers (2000, 2006, 2009), because an Edinburgh PhD
thesis titled *Dynamic syntax* by David Tugwell (1999) predates KMW01 and the 2009 abstract calls DS a
"newly-emerging paradigm", so these may belong to a homonymous, independent incremental formalism;
Kułacka 2012 (*Defining Linear Dynamic Syntax*); Saavedra 2015 (Logos 25(1):87–97). Six non-DOI leads
were added to `discovery.json`, including the *Language in Flux* volume and recent DS-TTR generation and
repair work (Eshghi and Ashrafzadeh 2023).

## 6. What the admissions mean for the catalogue, and what they do not

What the literature says, at abstract level: the 2021 special issue extends DS to Korean incremental
structure building (K20), Chinese minimizers (YW21), Kazakh differential object marking (NC21), Greek
clitic diachrony (C20) and a compositional distributional semantics (PSHK21). The SemDial lineage shows
a continuous line of dialogue work from 2007 clarification requests through 2008 fragment typology, 2012
self-repair in DS-TTR, 2015 parser demonstration, to 2019–2021 position papers on vector semantics and
affordances. These confirm the existing catalogue topics C15.04, C15.05, C15.06, C16.02, C16.03,
C12–C13 and C18.04 as sourced topics rather than open leads, but every one of them remains at abstract
level in this library and none has been adjudicated.

What this code does: unchanged. The three new cards state `not_implemented` or
`partial_infrastructure` for every backend and link only to existing design documents and tests for
the synchronic Greek clitic fragments. A successful synchronic parse of an SMG clitic cluster says nothing
about the diachronic argument of C20, and the workbench's Jev lexical preferences and OpenRouter
vocabulary proposals are unrelated to the tensor-contraction semantics of SPHK18/PSHK21.

What was tested: `scripts/build_ds_library.py` and `--check` in a scratch Python 3.12 environment on the
Mac (the repository's macOS `.venv` cannot run in the Linux shell used here and was left untouched);
Pandoc 3.1.3 round trip of all 53 BibTeX records with IDs, titles, author order and dates preserved;
`git diff --check`. Not tested: `check_ds_library_browser.py` (no Playwright in the scratch environment);
no pytest run, because no code changed.

## 7. Recommended next steps for the library

1. Read C20 in full (OA, 28 pages) and align its stages with the synchronic SMG/Cypriot/Pontic templates;
   this is the closest source to work already in the workbench and the author is the maintainer.
2. Read K20 and NC21 in full for the typology family (C15); both are OA and fingerprinted.
3. Settle the Tugwell question by reading one of the three papers; if it is a homonymous formalism, record
   it as such with a one-line comparison rather than excluding it silently.
4. Obtain PSHK21 (an accepted manuscript exists at QMRO/UCL) and SE21; both are blocked for direct download
   from this environment.
5. Screen the OpenAlex pool by restricting to records whose title or abstract contains "dynamic syntax"
   plus a DS author name. The exact query list, script and raw pool were retained in the cloud
   session's scratch space and are not available in this repository; retrieve those artifacts
   before claiming that the reported sweep is reproducible here.
6. Only after reading: promote any of the three abstract-level cards to a bounded analysis card with
   locators, or delete it.

Generated outputs (`index.html`, `ds-library.bib`, `ds-library.csl.json`) were rebuilt from the edited
records and their hashes are in `library/validation.json` under `expansion_followup`.
