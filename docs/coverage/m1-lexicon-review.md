# M1 lexical additions for review

Stergios approved these 21 surface forms (42 entries across the two native modes) in the conversation on 2026-09-27. They passed strict grammar loading and have been merged into both shipped SMG lexicons. Entries use the maintained SMG action templates. The source is `chatzikyriakidis-phdthesis.pdf`; page numbers below are physical PDF pages.

| Forms | Template and meaning | Source |
| --- | --- | --- |
| γράφοντας, grafontas, γrafontas | Writing gerund; enclisis | (3.11), p.92 |
| μη, μην, mi, min | Prohibitive negator | (3.83), p.130; min also in (6.81b) |
| θα, tha | Future environment; currently potential semantics | (6.65), p.284 |
| την, τη, tin, ti | Third-person feminine accusative clitic, reference `her` | Paradigm (3.1), p.90; spelling/final-n aliases |
| τους, τις, τες, τα, tus, tis, tes, ta | Third-person plural accusative clitic, reference `them` | Paradigm (3.1), p.90 |

The Greek spellings are aliases of the source transcriptions. The approved row parameters now name reference classes: the M2 templates introduce restricted metavariables and SUBSTITUTION resolves them against context, using the declared constants as defaults. This queue does not add a human grammaticality judgment to any corpus row. The future entry isolates the placement environment; full temporal semantics is not claimed.

Review records bind to the exact candidate content hash. After approval, `scripts/merge_approved_rows.py data/greek-clitics/lexicon_candidates.jsonl --write` validates all affected grammars before changing the lexicon and declaration files. `--include-pending` is a read-only preview and cannot be combined with `--write`.
