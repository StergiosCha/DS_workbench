"""Cited source data and real parser outcomes gate the coverage floors."""

import json
import pytest
from dylan.corpus import CORPORA, check_lock, read_rows, run_row, summarize
from dylan.greek_workbench import CASES


@pytest.fixture(scope="session")
def corpus_results():
    cache = {}
    return {
        str(path): [
            run_row(row, grammar, isolate=False, coq_cache=cache)
            for row in read_rows(path)
            for grammar in row["grammars"]
        ]
        for path in CORPORA
    }


def test_corpus_rows_have_source_and_judgment():
    rows = read_rows(CORPORA[0])
    assert len(rows) >= 150
    assert sum(r["judgment"]["status"] == "starred" for r in rows) >= 40
    assert len({r["id"] for r in rows}) == len(rows)
    for row in rows:
        assert row["judgment"]["source"] == row["source"]
        assert (row["human_labels"]["annotator"] is None) == (row["human_labels"]["date"] is None)
        assert "*" not in row["surface"]
    assert len(read_rows(CORPORA[1])) >= 100


def test_cases_rows_agree_with_greek_workbench(corpus_results):
    rows = {r["id"]: r for r in read_rows(CORPORA[0])}
    results = {(r["id"], r["grammar"]): r for r in corpus_results[str(CORPORA[0])]}
    for case in CASES:
        for key, accepted in [
            ("sentence", True),
            ("reverse", False),
            ("ascii", True),
            ("reverse_ascii", False),
        ]:
            row = rows[f"cases:{case['id']}:{key}"]
            assert row["surface"] == case[key]
            for grammar in row["grammars"]:
                result = results[row["id"], grammar]
                assert result["ok"] == result["complete"] == accepted
                assert result["executable"] and not result["cap_hit"]


def test_coverage_lock_does_not_regress(corpus_results):
    for path in CORPORA:
        report = summarize(corpus_results[str(path)])
        assert not check_lock(report, json.loads((path.parent / "coverage.lock").read_text()))


def test_recorded_expected_outcomes(corpus_results):
    for results in corpus_results.values():
        for row in results:
            expected = row["expected"]
            for name in ("ok", "complete"):
                if expected.get(name) is not None:
                    assert row[name] == expected[name], (row["id"], row["grammar"], name)
            if expected.get("failure_kind"):
                assert row["failure"]["kind"] == expected["failure_kind"]
            if row["complete"]:
                assert all(
                    s in (row["semantics"] or "") for s in expected.get("semantics_substrings", [])
                )
