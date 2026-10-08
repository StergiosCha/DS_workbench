"""Compare neutral decision logging with decisions off over the sourced corpora."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from dynamicsyntax import get_grammars, icp
from dylan.action.lexical_action import LexicalAction
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import CORPORA, deadline, read_rows
from dylan.decision import DecisionClient
from dynamicsyntax._parse import _active_path_edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/decision/entry-replay.json"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    log = args.output.with_suffix(".jsonl")
    log.write_text("")
    available = set(get_grammars())
    tasks = [(row, grammar) for corpus in CORPORA for row in read_rows(corpus)
             for grammar in row["grammars"] if grammar in available]
    if args.limit is not None:
        tasks = tasks[:args.limit]
    mismatches, errors, winning_entries = [], [], []
    for row, grammar in tasks:
        outcomes = []
        for mode in ("off", "stub"):
            reset_all_meta_bindings()
            engine = icp(grammar)
            engine.decision_client = DecisionClient(mode, log_path=log)
            try:
                with deadline(30):
                    result = engine.parse(row["surface"])
                outcomes.append({"ok": result.ok, "complete": result.tree.is_complete(),
                                 "semantics": str(result.semantics), "cap_hit": result.cap_hit,
                                 "stats": asdict(result.stats)})
                if mode == "stub" and result.ok:
                    for edge in _active_path_edges(engine):
                        for action in edge.get_actions():
                            if isinstance(action, LexicalAction) and len(engine.lexicon.lookup_all(action.word)) > 1:
                                winning_entries.append({"id": row["id"], "grammar": grammar,
                                                        "word": action.word, "template": action.action_type,
                                                        "parameters": action.parameters})
            except (TimeoutError, ValueError, TypeError, RuntimeError, RecursionError) as error:
                outcomes.append({"error": type(error).__name__})
                errors.append({"id": row["id"], "grammar": grammar, "mode": mode, "error": type(error).__name__})
            finally:
                engine.close()
        if outcomes[0] != outcomes[1]:
            mismatches.append({"id": row["id"], "grammar": grammar, "outcomes": outcomes})
    report = {"runs_compared": len(tasks), "mismatches": mismatches, "errors": errors,
              "winning_entries": winning_entries, "live_calls": 0,
              "calibration": "unmeasured", "log": str(log)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("runs_compared", "live_calls", "calibration")}))
    print(f"mismatches={len(mismatches)}, errors={len(errors)}, labelled_entries={len(winning_entries)}")
    if mismatches or errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
