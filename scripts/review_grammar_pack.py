"""Check an exported personal grammar pack; optionally build a standalone grammar.

No model calls. The output is a candidate for shared review, not an automatic
change to the maintained grammar. Existing directories are never overwritten.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dylan.grammar_workshop import check_pack, export_grammar


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pack", type=Path)
    ap.add_argument(
        "--output", type=Path, help="Create a new standalone grammar directory after passing checks"
    )
    args = ap.parse_args()
    document = json.loads(args.pack.read_text())
    pack = document.get("pack", document)
    report = export_grammar(pack, args.output) if args.output else check_pack(pack)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report.get("compiles") or not report["all_matched"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
