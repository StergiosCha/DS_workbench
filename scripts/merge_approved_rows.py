"""Preview reviewed lexical additions; --include-pending validates candidates without merging."""

import argparse
import difflib
import json
from pathlib import Path

from dylan.lexicon_review import prepare_candidates

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--include-pending", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write and args.include_pending:
        parser.error("Pending candidates can only be previewed, not written")
    candidates = [json.loads(line) for line in args.candidates.read_text().splitlines() if line.strip()]
    replacements = prepare_candidates(
        candidates, ROOT / "src/dynamicsyntax/grammars", include_pending=args.include_pending
    )
    for path, content in replacements.items():
        print("".join(difflib.unified_diff(path.read_text().splitlines(True), content.splitlines(True),
                                        fromfile=str(path.relative_to(ROOT)), tofile=str(path.relative_to(ROOT)))), end="")
    if args.write:
        for path, content in replacements.items():
            path.write_text(content)
    print(f"Validated {len(replacements) // 2} grammar(s); {'merged' if args.write else 'preview only'}.")


if __name__ == "__main__":
    main()
