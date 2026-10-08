"""Build the M1 source-review queue, preserving reviews of unchanged proposals."""

import json
from pathlib import Path

from dylan.lexicon_review import candidate_hash

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data/greek-clitics/lexicon_candidates.jsonl"
INVENTORY = [
    ("γράφοντας grafontas γrafontas", "gerund write", "3.11", 92, {}, "Greek spelling and transliteration aliases of the cited writing gerund."),
    ("μη μην mi min", "min x", "3.83", 130, {}, "Prohibitive marker; μην/min allomorphs also occur in (6.81b)."),
    ("θα tha", "future x", "6.65", 284, {}, "Future particle from a larger clause; template isolates its placement environment."),
    ("την τη tin ti", "clitic her 3 acc", "3.1", 90, {"constants": {"her": "human"}}, "Feminine singular weak pronoun; Greek spelling and final-n aliases of table tin."),
    ("τους τις τες τα tus tis tes ta", "clitic them 3 acc", "3.1", 90, {"constants": {"them": "object"}}, "Third-person plural weak-pronoun forms; reference is a context placeholder pending substitution."),
]


def main():
    previous = {r["id"]: r for r in map(json.loads, TARGET.read_text().splitlines())} if TARGET.exists() else {}
    result = []
    for backend in ("mltt", "classical"):
        for forms, action, label, page, declarations, note in INVENTORY:
            for form in forms.split():
                row = {"id": f"m1:{backend}:{form}", "grammar": f"2026-smg-{backend}",
                       "row": f"{form} {action}", "source": {"file": "chatzikyriakidis-phdthesis.pdf",
                       "label": f"({label})", "page": page, "page_kind": "PDF page (1-based)"},
                       "declarations": declarations, "notes": note,
                       "review": {"status": "pending", "reviewer": None, "hash": None}}
                row["proposal_hash"] = candidate_hash(row)
                old = previous.get(row["id"])
                if old and candidate_hash(old) == row["proposal_hash"]:
                    row["review"] = old["review"]
                result.append(row)
    TARGET.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in result))


if __name__ == "__main__":
    main()
