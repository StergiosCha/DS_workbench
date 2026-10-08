# M2 clitic cluster vocabulary for review

Stergios approved these 19 SMG forms and eight Grico forms, each in classical and constructive mode (54 lexical rows), in the conversation on 2026-09-27. All four grammars passed strict loading and 24 sourced sentence checks before approval. The reviewed rows are now merged into the shipped lexicons.

| Variety | Forms | Entry | Thesis source, physical PDF page |
| --- | --- | --- | --- |
| SMG | μου mu, σου su, του tu, της tis | Singular genitive clitics | (3.1), p.90 |
| SMG | δος dos δos ∆os | Ditransitive imperative, give | (3.87)-(3.88), p.131 |
| SMG | έδωσα edosa eδosa | Ditransitive, give, first-person singular | (3.20)-(3.21), p.93 |
| SMG | μιλώ milo | Talk, with one internal argument | (3.91), p.132 |
| SMG | τηλεφώνησα tilefonisa | Telephone, with one internal argument | (3.92), p.132 |
| Grico | mu tu | Genitive clitics | (3.2), p.90 |
| Grico | to ton tin | Accusative clitics | (3.2), p.90 |
| Grico | do | Ditransitive imperative, give | (3.89)-(3.90), p.132 |
| Grico | doka | Ditransitive, give, first-person singular | (3.22)-(3.23), p.93 |
| Grico | milo | Talk, with one internal argument | (3.91), p.132 |

Greek spellings and delta variants are aliases of the cited transcriptions. Past forms currently contribute the verb's relation; tense quantification is not implemented. The Grico vocabulary uses the source's Latin transcription.

Genitives introduce a locally unfixed node with a formula requirement. MERGE fixes its position, and SUBSTITUTION resolves its reference. The SMG imperative permits both orders. The Grico genitive entry requires every object position below the functor spine still to require a type, blocking an already parsed accusative.

Validation uses isolated copies and the ordinary parser, without adding source judgments. The queue is `data/greek-clitics/m2-lexicon-candidates.jsonl`; approval binds to each candidate's content hash. `scripts/merge_approved_rows.py` validates all affected grammars before a reviewed merge.
