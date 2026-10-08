"""Validate grammar directories and report static and measured dynamic gaps."""

import argparse
import json
from pathlib import Path
from dylan.corpus import ROOT
from dylan.grammar_tools import lint_grammar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="*", type=Path)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--results", nargs="*", type=Path, default=[])
    parser.add_argument("--json", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directories = args.directories
    if args.all:
        directories = sorted(
            {
                p.parent
                for base in (ROOT / "src/dynamicsyntax/grammars", ROOT / "resources")
                for p in base.glob("*/computational-actions.txt")
            }
        )
    if not directories:
        parser.error("Provide grammar directories or --all")
    results = [
        json.loads(line)
        for p in args.results
        for line in p.read_text().splitlines()
        if line.strip()
    ]
    reports = [lint_grammar(p, results) for p in directories]
    print("Grammar | rows loaded | rows failed | strict errors | disabled rules | generic labels")
    for r in reports:
        print(
            f"{r['grammar']} | {r['load_stats']['word_entries_loaded']} | {r['load_stats']['words_failed']} | {len(r['strict_errors'])} | {len(r['disabled_rules'])} | {len(r['generic_labels'])}"
        )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n")
    if args.check and any(r["strict_errors"] or r["generic_labels"] for r in reports):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
