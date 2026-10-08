"""Dictionary morphology, candidate preservation and normal DS execution."""

import sqlite3

import pytest

from dylan.lexical_dictionary import ARCHIVE_SHA256, VERSION, candidates
from dylan.workbench_api import parse_request


@pytest.fixture
def dictionary(monkeypatch, tmp_path):
    path = tmp_path / "wordnet.sqlite3"
    monkeypatch.setenv("DS_DICTIONARY_PATH", str(path))
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "lexical.sqlite3"))
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE metadata (key TEXT, value TEXT);
            CREATE TABLE senses (lemma TEXT, pos TEXT, synset TEXT, lexfile INTEGER,
                                 rank INTEGER, frames TEXT, gloss TEXT);
            CREATE TABLE exceptions (surface TEXT, pos TEXT, lemma TEXT);
        """)
        db.executemany("INSERT INTO metadata VALUES (?,?)", [("archive_sha256", ARCHIVE_SHA256), ("version", str(VERSION))])
        db.executemany("INSERT INTO senses VALUES (?,?,?,?,?,?,?)", [
            ("linguist", "n", "10264437", 18, 0, "[]", "a specialist in linguistics"),
            ("research", "v", "00877327", 31, 0, "[8]", "investigate systematically"),
            ("donate", "v", "02263027", 40, 0, "[8,15]", "give to a charity"),
            ("lend", "v", "02324182", 40, 0, "[14,15]", "give temporarily"),
            ("give", "v", "02230772", 40, 0, "[14,15]", "transfer possession"),
            ("consider", "v", "00689344", 31, 0, "[2,26]", "think about"),
            ("child", "n", "09917593", 18, 0, "[]", "a young person"),
            ("happy", "a", "01148283", 0, 0, "[]", "enjoying contentment"),
            ("mere(a)", "a", "01539573", 0, 0, "[]", "being nothing more than specified"),
        ])
        db.executemany("INSERT INTO exceptions VALUES (?,?,?)", [
            ("lent", "v", "lend"), ("given", "v", "give"), ("children", "n", "child"),
        ])
    return path


def test_frames_do_not_invent_dative_alternations(dictionary):
    donate, _ = candidates("donates")
    lend, _ = candidates("lends")
    assert {e["template"] for e in donate} == {"transitive", "dative-to"}
    assert {e["template"] for e in lend} == {"ditransitive", "dative-to"}


def test_inflections_keep_lemma_and_participles_are_not_finite(dictionary):
    entries, analyses = candidates("lent")
    assert entries and all(e["lemma"] == "lend" for e in entries)
    assert {a["inflection"] for a in analyses} == {"past", "past_participle"}
    entries, analyses = candidates("given")
    assert not entries and {a["inflection"] for a in analyses} == {"past_participle"}
    entries, analyses = candidates("children")
    assert entries and {e["template"] for e in entries} == {"plural-noun"}
    assert all(e["morphology"] == "plural" and e["lemma"] == "child" for e in entries)
    assert analyses[0]["lemma"] == "child" and analyses[0]["inflection"] == "plural"


def test_distinct_valencies_have_distinct_semantic_signatures(dictionary):
    entries, _ = candidates("considers")
    assert len({e["symbol"] for e in entries}) == 2


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_dictionary_adjective_has_predicative_use_without_assumed_intersectivity(dictionary, backend):
    options = {"grammar": f"2026-english-{backend}", "lexical_mode": "dictionary"}
    good = parse_request({**options, "sentence": "I am very happy."})
    assert good["complete"]
    assert "very(happy_a01148283(speaker))" == good["words"][-1]["normalized"]
    assert not parse_request({**options, "sentence": "A happy man walks."})["complete"]
    assert not candidates("mere")[0]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence", [
    "a linguist researches a book.", "john donates a book to mary.",
    "john lends mary a book.", "john lent a book to mary.",
])
def test_dictionary_entries_execute_native_programs(dictionary, backend, sentence):
    result = parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}", "lexical_mode": "dictionary"})
    assert result["complete"] and result["cap_hit"] is None
    assert result["lexical"]["entries"] and not result["lexical"]["notices"]
    assert not result["stats"]["top_n_cuts"]
    assert all(e["source"] == "dictionary" for e in result["lexical"]["entries"])
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]


def test_missing_index_falls_back_without_changing_original_lexicon(monkeypatch, tmp_path):
    monkeypatch.setenv("DS_DICTIONARY_PATH", str(tmp_path / "absent.sqlite3"))
    result = parse_request({"sentence": "john walks.", "grammar": "2026-english-mltt", "lexical_mode": "dictionary"})
    assert result["complete"] and result["lexical"]["notices"]


def test_environment_file_is_literal_and_does_not_replace_process_values(monkeypatch, tmp_path):
    from dylan.workbench_environment import load_environment

    source = tmp_path / ".env"
    source.write_text("TYPESAFE_API_KEY='fixture-$NOT_EXPANDED'\nDS_TEST_LABEL=from_file\n")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("DS_TEST_LABEL", "from_process")
    load_environment(source)
    import os
    assert os.getenv("TYPESAFE_API_KEY") == "fixture-$NOT_EXPANDED"
    assert os.getenv("DS_TEST_LABEL") == "from_process"
