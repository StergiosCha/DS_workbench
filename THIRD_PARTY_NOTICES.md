# Software and data provenance

The workbench extends the `dynamicsyntax` Python package, a port of the
Java DyLan parser. The software repositories are
<https://github.com/incrementaliser/DynamicSyntax> and
<https://github.com/Dynamics-of-Language/DyLan>. Neither URL is a claim
that the current workbench changes have been released by those projects.
Original source/history attribution must be retained when redistributing.
See `LICENSE` for the upstream licence evidence and the unresolved metadata
conflict; this file does not grant additional rights.

| Material | Source and terms |
| --- | --- |
| Ported DyLan engine | Referenced upstream LICENSE.txt is LGPLv3, with incorporated GPLv3; copies are in `licenses/`. The previous BSD package label was inconsistent with it. |
| GDT lexical export | UD Greek GDT r2.17 training split; CC BY-NC-SA 3.0, <https://creativecommons.org/licenses/by-nc-sa/3.0/>. Attribution: Institute for Language and Speech Processing, Athena Research Center; Prokopis Prokopidis and Haris Papageorgiou. Derived forms/frames, not an unmodified corpus. Source URL and hash are in `data/greek-lexicon/gdt-train.json`; build details in its README. Noncommercial/share-alike terms are not replaced by a software licence. |
| Grammar examples and research fixtures | Source-specific excerpts/adaptations retain their source conditions. Row locators and judgment provenance are in the JSONL data; inclusion is not a declaration that the original publications are openly licensed. Source PDFs are not bundled. |
| WordNet (optional index) | Princeton WordNet 3.0. The builder preserves the archive's complete `wordnet/LICENSE` in SQLite metadata. The index is not included in the wheel. |
| Brown/Gutenberg (optional indexes) | NLTK-distributed corpora, with corpus/book-specific terms; builders preserve archive README and source metadata. Indexes are not included in the wheel. |
| Svarna and Triantafyllidis responses | Retrieved evidence remains subject to the source's access and reuse conditions. The connector does not confer bulk redistribution or training rights. |
| Python dependencies | Independently licensed dependencies; retain their distribution metadata/notices. |

The wheel contains selected runtime evidence (GDT, Greek judgment fixtures
and recorded coverage reports), as declared explicitly in `pyproject.toml`.
It is therefore not accurately described by one software-only licence.
Review or separate these assets when preparing a redistribution for a
different use. `DS_WORKBENCH_DATA` can select an external runtime data tree.
