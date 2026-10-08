# M4c: a common-noun indefinite DP in SMG

Stergios approved these additions in the conversation on 2026-09-29: seven SMG surface forms, 14 lexical readings across classical and constructive modes. All rows and their semantic declarations are merged into the shipped grammars. The candidate file is `data/greek-clitics/m4c-lexicon-candidates.jsonl`; each reading records the source locator, approval and matching content hash.

| Forms | Reading | Source, physical PDF page |
| --- | --- | --- |
| ena, ένα | Singular neuter accusative indefinite determiner | Thesis (B.4), p.395 |
| vivlio, βιβλίο | Singular neuter accusative common noun, book | Thesis (B.4), p.395 |
| δiavasa, diavasa, διάβασα | Transitive read, first-person singular | Thesis (B.4), p.395 |

Appendix B gives `∆en ksero esis ti kanate xtes, pados eγo to δiavasa ena vivlio`, translated “I do not know what you did yesterday, but I read a book.” Its gloss labels the article `a.ACC` and contains the apparent typo `book.BOOK`. The Greek-script and ASCII entries above are disclosed spelling aliases of the source transcription.

The short test `to diavasa ena vivlio` omits the preceding discourse and explicit `eγo`; the finite verb supplies the first-person subject. The variants without a clitic and with a preceding object are adaptations for testing tree growth and coreference, not additional quoted source judgments. They do not establish the discourse conditions, prosody, scope or full distribution of indefinite doubling and CLLD. The verb supplies the read relation without an interpretation of past tense.

Classical DPs follow the five-node structure in thesis (2.70)-(2.77), pp.67-71: the entity DP has a `cn` daughter and a `cn → e` determiner daughter; the CN has an entity variable and an `e → cn` restrictor. The resulting clause means `read(speaker, ε x0:e. book(x0))`. Constructive DPs keep the separate CN/type analysis and introduce a fresh witness, yielding `Σ x:book. read(speaker, x)`. The witness remains valid after its unfixed node merges into the object position. Neither analysis adds common-noun definites or uniqueness conditions.

Both previews passed strict loading and 36 checks: 16 positive sentence parses, 16 negative controls, two incomplete nominal checks and two workbench operation-trace checks. The controls cover missing heads, wrong nominal categories, incompatible clitic gender and extra full DPs. Constructive positive meanings compiled with `coqc`. Workbench traces expose the noun's individual node-building and pointer operations, local reductions and the subsequent subtree MERGE.

After approval, strict loading passed for both merged grammars. The DP tests now run directly against the shipped grammars; the combined DP, proper-name and lexical-review suite passed 92 checks, including constructive Coq compilation. The source spelling `δiavasa` also completed through the workbench API in both modes.

The full corpus rerun covered 515 Greek runs and 215 English runs. Coverage checks passed with zero overgeneration and unchanged floors; no adapted test sentence was promoted into an independent source judgment.

Approval covers the exact candidate rows and declarations in the candidate file. It does not certify the adapted sentences as independent source judgments or widen the fragment beyond singular accusative indefinite objects.
