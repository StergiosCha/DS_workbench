"""Arithmetic cannot reward a search failure, missing lexicon or unknown judgment."""

import subprocess
from dylan.corpus import agrees, check_lock, lock_counts, read_rows, run_row, summarize, CORPORA


def record(identity, status, **options):
    row = {
        "id": identity,
        "grammar": "test",
        "phenomena": ["placement"],
        "judgment": {"status": status},
        "expected": {},
        "ok": False,
        "complete": False,
        "executable": True,
        "failure": None,
        "cap_hit": None,
        "stats": {},
        "ms": None,
        "backend": "mltt",
        "coq": "not_applicable",
        "semantics": None,
    }
    row.update(options)
    return row


def test_four_rates_keep_unknowns_and_search_failures_out_of_agreement():
    rows = [
        record(
            "good",
            "licensed",
            ok=True,
            complete=True,
            semantics="walk(john)",
            expected={"semantics_substrings": ["walk("]},
            coq="passed",
        ),
        record("bad", "starred"),
        record("cap", "starred", cap_hit="limit"),
        record("timeout", "starred", failure={"kind": "time_limit"}),
        record("missing", "licensed", executable=False),
        record("unknown", "not_stated", ok=True, complete=True),
    ]
    result = summarize(rows)["test:all"]
    assert result["vocabulary"] == [4, 5]
    assert result["agreement"] == [2, 4]
    assert result["semantic"] == [1, 1]
    assert result["not_stated"] == 1
    assert result["execution_errors"] == ["timeout"]
    assert not agrees(rows[2]) and not agrees(rows[3])
    assert check_lock({"test:all": result}, {})


def test_overgeneration_and_disappearing_groups_fail_the_lock():
    baseline = summarize([record("negative", "starred")])
    lock = lock_counts(baseline)
    changed = summarize([record("negative", "starred", ok=True, complete=True)])
    assert any("overgeneration" in error for error in check_lock(changed, lock))
    assert any("disappeared" in error for error in check_lock({}, lock))


def test_variable_needs_distinct_complete_strategies():
    row = record("variable", "variable", readings=[{"complete": True, "strategy": "unfixed"}] * 2)
    assert not agrees(row)
    row["readings"].append({"complete": True, "strategy": "link"})
    assert agrees(row)


def test_worker_timeout_is_inconclusive(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 1)

    monkeypatch.setattr(subprocess, "run", timeout)
    row = read_rows(CORPORA[0])[1]
    result = run_row(row, row["grammars"][0], timeout=1)
    assert result["failure"]["kind"] == "time_limit"
    assert not agrees(result)


def test_isolated_and_in_process_workers_agree():
    row = read_rows(CORPORA[0])[0]
    isolated = run_row(row, row["grammars"][0])
    direct = run_row(row, row["grammars"][0], isolate=False)
    for key in ("ok", "complete", "failure", "cap_hit", "stats", "semantics", "templates"):
        assert isolated[key] == direct[key]
