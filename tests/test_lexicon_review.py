"""Approval binds to exact lexical content; strict validation precedes any writes."""

import json
from pathlib import Path
import shutil

import pytest

from dylan.lexicon_review import candidate_hash, prepare_candidates

ROOT = Path(__file__).parents[1]


def candidate():
    return {"id": "fixture", "grammar": "english", "row": "jane proper jane human",
            "source": {"file": "test fixture", "line": 1},
            "declarations": {"constants": {"jane": "human"}},
            "review": {"status": "pending"}}


@pytest.fixture
def grammars(tmp_path):
    shutil.copytree(ROOT / "src/dynamicsyntax/grammars/2026-english-mltt", tmp_path / "english")
    return tmp_path


def test_pending_preview_is_strict_and_cannot_change_shipped_files(grammars):
    entry = candidate()
    before = (grammars / "english/lexicon.txt").read_text()
    assert prepare_candidates([entry], grammars) == {}
    preview = prepare_candidates([entry], grammars, include_pending=True)
    assert "jane proper" in preview[grammars / "english/lexicon.txt"]
    assert (grammars / "english/lexicon.txt").read_text() == before
    entry["row"] = "jane nonexistent jane"
    with pytest.raises(ValueError):
        prepare_candidates([entry], grammars, include_pending=True)


def test_approval_is_invalid_after_content_changes(grammars):
    entry = candidate()
    entry["review"] = {"status": "approved", "reviewer": "fixture reviewer", "hash": candidate_hash(entry)}
    assert prepare_candidates([entry], grammars)
    entry["row"] = "jane proper mary human"
    with pytest.raises(ValueError, match="does not match"):
        prepare_candidates([entry], grammars)


def test_proposed_declarations_cannot_redefine_existing_symbols(grammars):
    entry = candidate()
    entry["declarations"] = {"constants": {"john": "dog"}}
    with pytest.raises(ValueError, match="Conflicting"):
        prepare_candidates([entry], grammars, include_pending=True)


def test_m1_candidate_queue_loads_strictly():
    entries = list(map(json.loads, (ROOT / "data/greek-clitics/lexicon_candidates.jsonl").read_text().splitlines()))
    assert entries and all(e["proposal_hash"] == candidate_hash(e) for e in entries)
    assert len(prepare_candidates(entries, ROOT / "src/dynamicsyntax/grammars", include_pending=True)) == 4
