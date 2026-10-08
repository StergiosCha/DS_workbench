# DS Research Library

Open **[the searchable library](index.html)** in a browser. It works offline.
Import **[BibTeX](ds-library.bib)** or **[CSL JSON](ds-library.csl.json)** into
Zotero or another reference manager. These exports contain bibliographic records
and review notes; they do not upload source PDFs.

First edition, 7 October 2026, extended the same evening (see the
[expansion report](../ds-library-expansion-2026-10-07.md)):

| Resource | What it contains |
|---|---|
| 53 selected works | Books, theses, chapters, articles, conference contributions and one supporting formal-logic reference; the evening pass added the complete JoLLI 30(2) DS special issue, nine SemDial anthology papers, the Bouzouita 2008 chapter and four discovery admissions. |
| 30 fingerprinted source versions | The previous 15 plus 15 open-access PDFs located in the evening pass (SemDial, ACL Anthology, Springer OA, Ghent repository). Inspection ranges from first pages/abstracts to selected passages and complete short papers. |
| Reading status | Nine selected-passage inspections, one full overview, one full short paper, 22 abstract/first-page inspections, six metadata-only records, 14 cited works awaiting source review. Most evening admissions are abstract-level; none is a full reading. |
| 18 categories / 91 topics | The existing theory-to-implementation inventory, reused through stable category and topic IDs. Topics include open questions. |
| Eight analysis cards | SMG PCC, English nonrestrictive relatives, ellipsis reuse, the distinct 2013 induction studies, DS–TTR versus TTR-DS, plus three abstract-level reading cards (Spanish clitic diachrony, Greek clitic diachrony, DS vector semantics). Only bounded implementations have test links. |
| 25 discovery matches | A separate Crossref title-search ledger: 12 now in the selected library, eight excluded with recorded reasons (programming-language syntax, LLM frameworks, a Minimalist monograph chapter, a stylistic-syntax article), five awaiting screening (three Tugwell papers that may belong to a homonymous framework, Kułacka 2012, Saavedra 2015). Six non-DOI leads are listed separately. Counts are not added to the selected-work count. |

This is the foundation for a growing DS library. It is a targeted selection,
not an exhaustive bibliography or a claim that every listed analysis has been
read, independently adjudicated or implemented. No Zotero group has been
created by this build; the importable files are ready for one.

## How to categorize a work

Use multiple facets. One paper can discuss several languages and constructions,
and a theoretical account can be adapted to more than one semantic backend.

| Facet | Question answered | Examples |
|---|---|---|
| Phenomenon | What linguistic problem is addressed? | PCC, relatives, ellipsis, conditionals, scrambling, repair. |
| DS mechanism | Which operations or representations do the inspected passages use? | LINK, MERGE, unfixed nodes, case filters, action reuse, record update. |
| Semantic framework | What meaning representation does the source actually use or compare? | Classical term semantics, DS–TTR, Constructive dependent types, vectors, framework-general; unclassified until checked. |
| TTR integration | How is TTR related to DS in this source? | DS–TTR supplies record-type meanings to DS processing; TTR-DS represents DS states and parsing actions themselves in TTR. |
| Language/variety | Which data are being analyzed? | English, SMG, Pontic, Grico, Japanese, Rangi. Tag the relevant varieties separately. |
| Contribution | What kind of work does it contribute? | Foundation, overview, linguistic analysis, computational study, proposal, supporting literature. |
| Review and evidence | How much was inspected, and what does that inspection establish? | Abstract only, selected passages, worked analysis, reported implementation, secondary reference. |
| Implementation | Which bounded analysis is implemented in which backend? | A card may say Classical: tested fragment; Constructive: adaptation; TTR: not audited. |

The bibliographic, theoretical and evidence facets help retrieve papers. The implementation facet belongs to
an **analysis card**, where scope, source passages and tests can be specified.
Neither a paper's publication status nor its semantic-framework tag establishes
coverage in the workbench.

The browser groups the existing 18 topic categories into seven collections:

| Collection | Existing category IDs |
|---|---|
| Foundations and semantic frameworks | C01 core growth; C18 semantic architecture. |
| Reference, predication and modification | C02 nominals; C03 valency/copulas; C06 modification; C08 anaphora/binding. |
| Order, dependencies and information structure | C04 word order/case; C05 relatives/extraction; C14 information structure; C15 agreement/typology. |
| Clitics, PCC and variation | C09 clitic systems; C16 historical development/variation. |
| Clause structure and composition | C07 coordination; C10 auxiliaries/situations; C11 clause linkage. |
| Ellipsis, dialogue and repair | C12 ellipsis; C13 interaction. |
| Parsing, generation and learning | C17 learning/search/generation. |

Mechanism and language tags cross these collections. A LINK paper can appear
under relatives, modification and interaction without copying its bibliography
record into three folders. Classification from a title or secondary citation is
explicitly provisional. “Unclassified” and “not audited” are useful states.

## The unit that connects a paper to code

The library distinguishes four entities:

| Entity | Required information |
|---|---|
| Work | Stable ID, title, authors in order, publication date/venue, DOI or other identifier, metadata provenance. |
| Version | Draft or published version, date, source location, PDF fingerprint, physical page count. |
| Analysis | A bounded claim, language/context, mechanism, source section/example/page, limitations, examples with origins, community review state. |
| Implementation | Backend, grammar scope, adaptation notes, relevant tests and dated verification record. |

For example, `smg-pcc-acc12` links the thesis's entry (6.49) and the 2011
PCC article to the SMG genitive/acc12 clash. Its authored/user-supplied regression
`του με έδωσε` is labeled as a regression, not a quotation from the thesis.
Classical and Constructive have separate implementation rows; the source's
Pontic discussion does not become a claim of the same restriction in Pontic.

Similarly, the nonrestrictive-relative card identifies the **2004 draft's**
physical and printed pages, while citing the **2005 work**. The Constructive
implementation is identified as our adaptation. This preserves the distinction
between the source's analysis and the code built from it.

An evidence level summarizes the cited inspection scope. It is not a score
of paper quality or theoretical consensus. Community review is tracked
separately; none of these imported inspection notes has been marked as a new
community adjudication.

The new `CL25` card matters for the architecture map: Cooper and Larsson (2025)
explicitly distinguish TTR-DS from earlier DS–TTR (§§1–2.2). Their recasting
concentrates on classical e/t contents, with further semantic integrations and
a detailed implemented grammar left as future work (§§3, 4.8–5). It therefore
has its own TTR-integration tag and research card. The app's existing TTR
backend is not presented as an implementation of that proposal.

## Files and rebuild

Editable sources:

- [papers.json](papers.json): selected works, versions, facets and reading steps.
- [analyses.json](analyses.json): source-to-implementation cards.
- [taxonomy.json](taxonomy.json): controlled facet labels, collections and workflow.
- [discovery.json](discovery.json): dated query, metadata candidates, screening decisions and reasons.
- [library-template.html](library-template.html): browser presentation.
- [Existing topic inventory](../ds-theoretical-coverage.json): category/topic IDs; remains the source of the 18/91 taxonomy.

Generated outputs are `index.html`, `ds-library.bib` and `ds-library.csl.json`.
From the repository root:

```sh
.venv/bin/python scripts/build_ds_library.py
.venv/bin/python scripts/build_ds_library.py --check
```

The builder uses Python's standard library. It validates IDs, references,
facet values, DOI uniqueness, original source fingerprints, source locators,
backend states and code paths. `--check` also fails on stale exports. It does
not run the linked semantic tests or certify that an analysis is correct.
Browser verification uses a Python environment with Playwright and Chromium:

```sh
python scripts/check_ds_library_browser.py
```

The standalone HTML embeds metadata and cards. It makes no network or model
requests. Public source links and local code links open only when followed.
The [validation record](validation.json) records the checked file hashes,
11 browser checks and citation-export round trip for this edition; its
`expansion_followup` block records the evening pass (structural check and
Pandoc round trip rerun; browser checks not rerun).

## Building a community library

Use a **shared Zotero group for bibliographic editing and source management**,
and this **versioned repository for analysis cards, grammar links and tests**.
Keep the stable work ID in both. The group can mirror the seven collections
and use namespaced tags such as `DS:categories:C09` and
`DS:frameworks:classical`. Import one export format per batch; importing both
formats would create duplicate records in a reference manager.

At this stage the repository is the maintained source and exports are one-way.
A future Zotero connector should record group/item keys and version numbers,
preview field changes and resolve conflicting edits explicitly. DOI matching
alone does not handle books without DOIs, thesis/article relationships or
publication/draft dates.

Contributors can take distinct, useful roles:

- **Bibliography curation:** verify metadata, author order, identifiers and version relationships; screen discovery candidates.
- **Source reading:** extract precise passages and examples into bounded cards, preserving dialect and discourse conditions.
- **Linguistic review:** assess the interpretation and negative controls; record disagreement and alternative accounts.
- **Implementation:** map a card to grammar actions and backend-specific meanings; add positive, negative and semantic tests.
- **Evaluation:** reproduce the fragment, assess fresh examples and keep development data separate from held-out evaluation.

For every new work:

1. Search by DOI, normalized title and authors before adding a record. Distinct
   theses, articles and conference papers remain distinct works; drafts of one
   work are versions.
2. Record where the metadata came from. A search hit is a lead; a bibliography
   copied from another project may contain errors. The 2001 Kempson/Meyer-Viol/
   Gabbay book and the 2005 Cann/Kempson/Marten book have separate titles and IDs.
3. Identify a readable source version. Preserve its fingerprint and the mapping
   between physical PDF pages and printed pages. Keep source-access and reuse
   conditions with any attachments; bibliographic inclusion does not authorize
   redistribution of a PDF.
4. Apply provisional retrieval tags, then refine them after reading. Do not
   silently give an unread source the mechanisms of the paper citing it.
5. Create analysis cards with exact source locators. Record example provenance,
   context, expected meaning and excluded cases. Several competing analyses of
   the same phenomenon can coexist and be linked as alternatives.
6. Review and implement each bounded card. Record changes in the contribution
   history and run the library validator when changing records.

LLMs can propose tags, deduplicate candidate titles, draft summaries and locate
candidate passages. Those outputs remain proposals until checked against the
identified source. Jev could rank a reading queue or flag inconsistent labels;
neither should certify the paper's claim or infer implemented coverage. This
library currently needs neither service.

## Next reading and implementation batches

| Priority | Source batch | Concrete result |
|---|---|---|
| 1. Complete the foundations | KMW01, CKM05, HG21; BMV94 for tree logic; CL25 for the TTR recasting | Source-located definition cards for Introduction, Prediction, LINK, MERGE, requirements and contextual update; a separate TTR-DS prototype specification. |
| 2. Resolve immediate grammar gaps | M02 modification/optional arguments; CA11 auxiliaries; G06 conditionals | Distinct argument/adjunct strategies, situation/tense obligations and conditional composition cards before broadening templates. |
| 3. Strengthen interactive semantics | KE19, CKP07, H14, GK16, PGMC10, E15/HE17/HE21 | Strict/sloppy reuse, repair and participant-sensitive examples with expected meanings. |
| 4. Audit typological transfer | C10/CK11, KK10, GI12/GI16, SG16, SE13/SE21, NC21, B08 | Separate language/variety cards and negative controls; shared mechanisms identified explicitly. |
| 5. Reproduce computational work | PEH11, EPH13, ECH13, C25, SPHK18 | Preserve semantic-framework differences; record datasets, splits, exclusions and reported versus reproduced results. |

In parallel, screen the five unresolved discovery matches and six leads and follow references
and forward citations from the selected works. The bounded Crossref query
returned 150 records, of which 25 contained the exact title phrase. This search
misses DS work without that phrase, so it cannot define the library's scope.
The original DS website returned an upstream error during this pass; no claim
of an exhaustive website bibliography is made.

The next software milestone is a read-only library entry point in the public
workbench, followed by a reviewed Zotero synchronization workflow. The current
deliverable is the offline library and portable exports; the live parser has
not been changed by this library build.
