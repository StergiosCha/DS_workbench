"""Report four independent rates and enforce committed coverage floors."""

import argparse
import json
from pathlib import Path
from dylan.corpus import CORPORA, ROOT, check_lock, lock_counts, markdown, summarize, read_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", "--lock-check", action="store_true")
    parser.add_argument("--write-lock", action="store_true")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "build/coverage")
    args = parser.parse_args()
    all_reports = {}
    errors = []
    pending_locks = []
    for corpus in CORPORA:
        source = args.results_dir / f"{corpus.parent.name}-top{args.top_n}.jsonl"
        rows = [json.loads(line) for line in source.read_text().splitlines() if line.strip()]
        expected = {(r["id"], g) for r in read_rows(corpus) for g in r["grammars"]}
        actual = {(r["id"], r["grammar"]) for r in rows}
        if expected != actual or len(actual) != len(rows):
            raise SystemExit(
                f"{source}: results do not match the current corpus; rerun corpus_run.py"
            )
        report = summarize(rows)
        all_reports.update(report)
        lock = corpus.parent / "coverage.lock"
        if args.check:
            errors.extend(check_lock(report, json.loads(lock.read_text())))
        if args.write_lock:
            errors.extend(check_lock(report, {}))
            pending_locks.append((lock, lock_counts(report)))
    if not errors:
        for lock, counts in pending_locks:
            lock.write_text(json.dumps(counts, ensure_ascii=False, indent=2) + "\n")
    output = ROOT / "docs/coverage/coverage.md"
    output.write_text(markdown(all_reports))
    print(f"{output}: {len(all_reports)} groups")
    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
