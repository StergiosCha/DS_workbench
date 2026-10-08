"""End-to-end dialect contrasts and evidence-aware failure reporting."""

from pathlib import Path
import shutil
import subprocess
import unicodedata

import pytest

from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.greek_workbench import CASES
from dylan.workbench_api import configuration, parse_request
from dynamicsyntax import icp


@pytest.fixture(autouse=True)
def clean_metas():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_source_placement_pairs_in_both_backends(case, backend):
    grammar = f"2026-{case['dialect']}-{backend}"
    good = parse_request({"sentence": case["sentence"], "grammar": grammar})
    assert good["complete"] and good["backend"] == backend
    assert good["diagnostics"]["judgment"]["status"] == "licensed_pattern"
    assert good["words"][-1]["requirement_count"] == 0
    assert len(good["words"][-1]["nodes"]) == case.get("nodes", 5)
    bad = parse_request({"sentence": case["reverse"], "grammar": grammar})
    assert not bad["ok"] and not bad["complete"]
    assert bad["failure"]["kind"] == "constraint_violation"
    assert bad["diagnostics"]["judgment"]["source"]["id"] == case.get("source", {"id": "historical-chapter"})["id"]
    assert all(word["known"] for word in bad["diagnostics"]["lexical_coverage"])


@pytest.mark.parametrize("grammar", configuration()["greek"]["grammars"])
def test_fragments_load_strictly_and_run_without_workbench(grammar):
    path = Path(__file__).resolve().parents[1] / "src/dynamicsyntax/grammars" / grammar
    assert Grammar(path, strict=True)
    assert Lexicon(path, strict=True).load_stats.words_failed == 0
    # The accepted/rejected placement comes from the DS engine alone, not the
    # comparison annotations in greek_workbench.assessment.
    case = next(c for c in CASES if f"-{c['dialect']}-" in grammar)
    from dylan.nlp.types import utterance_from_text

    for sentence, expected in ((case["sentence"], True), (case["reverse"], False)):
        parser = icp(grammar)
        try:
            parser.init()
            parser.new_sentence()
            accepted = all(
                parser.parse_word(w) is not None for w in utterance_from_text("test", sentence)
            )
            assert accepted is expected
        finally:
            parser.close()


def test_clitic_really_builds_the_object_before_the_verb_and_pointer_moves():
    result = parse_request({"sentence": "τον αγαπά.", "grammar": "2026-smg-classical"})
    assert result["complete"]
    # τον can start either a definite DP or a clitic. The provisional word
    # state may be an article; inspect the selected clitic action after search.
    first = next(frame for frame in result["actions"]
                 if frame["label"] == "τον" and frame["pointer"] == "0"
                 and {n["id"] for n in frame["nodes"]} == {"0", "01", "010"})
    if result["words"][1]["pointer"] != "0":
        assert any(frame["kind"] == "backtrack" for frame in result["operations"])
    assert first["pointer"] == "0"
    assert {node["id"] for node in first["nodes"]} == {"0", "01", "010"}
    assert next(n for n in first["nodes"] if n["id"] == "010")["formula"] == "U_him"
    assert next(n for n in result["words"][-1]["nodes"] if n["id"] == "010")["formula"] == "him"
    assert any(o.get("rule") == "substitution" and o["label"] == "put(Fo(him))"
               for o in result["operations"])
    make = next(o for o in result["operations"] if o["label"] == r"make(\/1)" and o["pointer_before"] == "0")
    assert make["pointer"] == make["pointer_before"] == "0"
    assert make["delta"]["created"] == ["01"]
    go = next(
        o
        for o in result["operations"]
        if o["label"].startswith("go(") and o["pointer_before"] == "0" and o["pointer"] == "01"
    )
    assert go["pointer_before"] == "0" and go["pointer"] == "01"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_negation_is_preserved_and_na_is_not_confused_with_imperative(backend):
    def parse(sentence, dialect="smg"):
        return parse_request({"sentence": sentence, "grammar": f"2026-{dialect}-{backend}"})

    assert parse("εν τον ιξέρω.", "cypriot")["words"][-1]["semantics"] == "not(know(speaker, him))"
    assert parse("na to grapsi.")["words"][-1]["semantics"] == "potential(write(pro, theme))"
    assert not parse("na grapse to.")["ok"]
    assert not parse("to grapsi.")["ok"]


def test_missing_vocabulary_is_not_a_grammaticality_judgment():
    result = parse_request({"sentence": "το ζουζουνίζει μπλα.", "grammar": "2026-smg-classical"})
    assert result["failure"]["kind"] == "lexicon_gap"
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    assert [
        word["token"] for word in result["diagnostics"]["lexical_coverage"] if not word["known"]
    ] == ["ζουζουνίζει", "μπλα"]


def test_known_but_unimplemented_cluster_does_not_claim_to_test_pcc():
    result = parse_request({"sentence": "το τον ιξέρω.", "grammar": "2026-cypriot-classical"})
    assert result["failure"]["kind"] == "construction_gap"
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    assert all(word["known"] for word in result["diagnostics"]["lexical_coverage"])


def test_other_known_word_failure_remains_unassessed():
    result = parse_request({"sentence": "ξέρω ξέρω.", "grammar": "2026-smg-classical"})
    assert result["failure"]["kind"] == "unresolved_parse_failure"
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_incomplete_clitic_prefix_and_unregistered_success_are_not_judgments():
    prefix = parse_request({"sentence": "τον", "grammar": "2026-smg-classical"})
    assert prefix["ok"] and not prefix["complete"]
    assert prefix["diagnostics"]["parse_status"] == "incomplete"
    assert prefix["failure"] is None
    result = parse_request({"sentence": "το γράφει.", "grammar": "2026-smg-classical"})
    assert result["complete"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_greek_unicode_and_transliteration_aliases():
    for sentence in (unicodedata.normalize("NFD", "Τον αγαπά."), "ton agapa."):
        result = parse_request({"sentence": sentence, "grammar": "2026-smg-classical"})
        assert result["complete"]
        assert result["words"][-1]["semantics"] == "love(pro, him)"
    from dylan.nlp.types import whitespace_tokenize

    assert whitespace_tokenize("ξέρ ατον;") == ["ξέρ", "ατον", ";"]


@pytest.mark.skipif(not shutil.which("coqc"), reason="Coq not installed")
def test_greek_constructive_exports_compile(tmp_path):
    for index, sentence in enumerate(("τον αγαπά.", "δεν τον ξέρω.", "να το γράψει.")):
        result = parse_request({"sentence": sentence, "grammar": "2026-smg-mltt"})
        source = tmp_path / f"Greek{index}.v"
        source.write_text(result["coq"])
        subprocess.run(
            ["coqc", str(source)], check=True, capture_output=True, text=True, timeout=15
        )


def test_thesis_grammar_cluster_failure_is_not_a_blanket_construction_gap():
    result = parse_request({"sentence": "το τον ξέρω.", "grammar": "2026-smg-classical"})
    assert not result["complete"]
    assert result["failure"]["kind"] == "unresolved_parse_failure"
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


def test_source_corpus_judgment_is_available_beyond_the_ten_cases():
    from dylan.greek_workbench import matched_case

    evidence = matched_case("2026-smg-mltt", ["to", "grafontas", "."])
    assert evidence["status"] == "excluded_in_described_variety"
    assert evidence["source"]["label"] == "(3.12)"
    assert evidence["human_labels"]["annotator"] is None


def test_corpus_judgment_does_not_hide_an_unknown_word():
    result = parse_request({"sentence": "to grafontas.", "grammar": "2026-smg-mltt"})
    if not all(row["known"] for row in result["diagnostics"]["lexical_coverage"]):
        assert result["failure"]["kind"] == "lexicon_gap"
    else:
        assert result["failure"]["kind"] == "constraint_violation"
    assert result["diagnostics"]["judgment"]["status"] == "excluded_in_described_variety"
