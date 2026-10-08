"""Run sourced corpora against real parser workers."""

import argparse
import sys
from pathlib import Path
from dylan.corpus import CORPORA, ROOT, read_rows, run_row, write_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--grammar")
    parser.add_argument("--top-n", type=int, default=3, choices=range(21))
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Use bounded in-process parsing with fresh meta bindings per row",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.all and not args.corpus:
        parser.error("Choose --all or --corpus")
    cache = {}
    for corpus in CORPORA if args.all else [args.corpus]:
        output = (
            args.output or ROOT / "build/coverage" / f"{corpus.parent.name}-top{args.top_n}.jsonl"
        )
        results = []
        for row in read_rows(corpus):
            if args.grammar and args.grammar not in row["grammars"]:
                continue
            grammars = [args.grammar] if args.grammar else row["grammars"]
            for grammar in grammars:
                results.append(
                    run_row(
                        row,
                        grammar,
                        top_n=args.top_n,
                        timeout=args.timeout,
                        coq_cache=cache,
                        isolate=not args.in_process,
                    )
                )
                if len(results) % 50 == 0:
                    print(f"{corpus.parent.name}: {len(results)} runs", file=sys.stderr, flush=True)
        write_rows(output, results)
        print(f"{output}: {len(results)} runs", flush=True)


if __name__ == "__main__":
    main()
