# M4a: case-marked names and a Grico PCC verb

Stergios approved this batch in the conversation on 2026-09-28: 13 SMG surface forms and one Grico form, giving 28 lexical readings across classical and constructive modes. All rows are merged. Existing clitic readings of `to`, `ton` and `τον` remain; their additional readings let these forms introduce an accusative proper name.

| Variety | Forms | Reading | Source, physical PDF page |
| --- | --- | --- | --- |
| SMG | o, ο | Nominative masculine article before a proper name | (2.50)-(2.52), p.57 |
| SMG | to, ton, τον | Accusative masculine article before a proper name | (2.50)-(2.52), p.57 |
| SMG | γiorγos, giorgos, γιώργος | Nominative Giorgos | (2.50)-(2.52), p.57 |
| SMG | γiani, giani, γιάννη | Accusative Giannis | (2.50)-(2.52), p.57 |
| SMG | xtipise, χτύπησε | Transitive hit, third-person singular | (2.50)-(2.51), p.57 |
| Grico | edika | Ditransitive give, third-person singular | (6.52), (6.54), (6.56), p.281 |

The source writes initial capitals and mixed-script transcriptions. Entries use the tokenizer's lower-case forms; ASCII and modern Greek spellings are disclosed aliases. The `to`/`ton` alternation is retained in the article reading. Verb meanings currently express the relation without temporal quantification.

The introductory analysis on p.57 explicitly treats the proper-name NP as an entity while setting determiner semantics aside. Accordingly, this batch models the article's case and gender constraints plus its requirement for a following name. It does not claim to implement common-noun definites, article uniqueness or their CN subtrees. Those remain M4 work; classical English common-noun DPs retain their existing CN structure.

Validated previews cover SVO, VSO and OVS with the same meaning `hit(giorgos, giannis)`, in source transcription and Greek script. Object-fronting, a following coreferential name and a preceding coreferential name exercise the tree operations needed for doubling and CLLD. These adaptations test structural coreference; discourse, prosody and the full distribution of doubling/CLLD are not yet modeled. Case mismatches, missing nominal heads and repeated full NPs cannot erase outstanding requirements. Names contribute third-person singular features; MERGE rejects a conflicting first-person subject slot. The three Grico controls retain the source's stars.

All four previews passed strict loading and 38 sentence checks; constructive meanings compiled in Coq. Approved candidates and content hashes are in `data/greek-clitics/m4a-lexicon-candidates.jsonl`.
