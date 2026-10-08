"""Real DS derivations, backend distinctions, and adversarial proposal controls."""
from copy import deepcopy
import shutil
import subprocess

import pytest

from dynamicsyntax import icp
from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.assisted_parsing import compile_entries, schema
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def entry(surface, lemma, template, domains, case="none", gender="none", person="none"):
    return dict(surface=surface, lemma=lemma, template=template, domains=domains, case=case, gender=gender, person=person,
                number="sg" if case != "none" or person != "none" or template == "noun" else "none",
                verb_form="finite" if template in {"intransitive", "transitive"} else "none",
                evidence="Test lexical hypothesis; independent DS execution is required.")


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,text,meaning", [
    ("english", "A man is here.", "here_location"),
    ("english", "The doctor is behind the library.", "located_behind"),
    ("english", "A woman is outside and a man is upstairs.", "∧"),
    ("english", "A man walks and reads a book.", "∧"),
    ("english", "John walks and Mary walks and Bill walks.", "walk(bill)"),
    ("english", "I can read the book.", "possible(read"),
    ("english", "A doctor will examine a patient.", "future("),
    ("smg", "Ο άντρας είναι εδώ.", "here_location"),
    ("smg", "Η Μαρία είναι στο σπίτι.", "located_at"),
    ("smg", "Ο Γιάννης περπατάει και η Μαρία διαβάζει το βιβλίο.", "∧"),
])
def test_general_construction_families(backend, language, text, meaning, tmp_path):
    result = parse_request({"sentence": text, "grammar": f"2026-{language}-{backend}", "lexical_mode": "dictionary" if language == "english" else "corpus"}, _trace=False)
    assert result["complete"], result["failure"]
    assert meaning in result["words"][-1]["normalized"]
    assert result["derivation"]["actions"]
    if backend == "mltt" and shutil.which("coqc"):
        target = tmp_path / "Meaning.v"
        target.write_text(result["coq"])
        checked = subprocess.run(["coqc", str(target)], capture_output=True, text=True, timeout=15)
        assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,text", [
    ("english", "John is in."), ("english", "John walks and."),
    ("english", "John can."), ("english", "John can walks."),
    ("english", "John cannot walk."), # unsupported scope must not acquire possible(not P)
    ("smg", "Η Μαρία είναι στο."), ("smg", "Ο άντρας είναι εδώ και."),
    ("smg", "Η Μαρία είναι στον σπίτι."),
])
def test_incomplete_or_conflicting_constructions_do_not_complete(backend, language, text):
    result = parse_request({"sentence": text, "grammar": f"2026-{language}-{backend}", "lexical_mode": "dictionary" if language == "english" else "corpus"}, _trace=False)
    assert not result["complete"]


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_greek_model_forms_and_case_checked_adjective(monkeypatch, backend, tmp_path):
    calls = []
    vocabulary = [entry("ερευνήτρια", "ερευνήτρια", "noun", ["human"], "nom", "f"),
                  entry("δείγμα", "δείγμα", "noun", ["object"], "acc", "neut"),
                  entry("μεγάλο", "μεγάλος", "adjective", ["object"], "acc", "neut")]
    def provider(context, spec, **options):
        calls.append(context)
        assert context["backend"] == backend
        assert "grammar" in context and options["instruction"]
        return {"entries": [e for e in vocabulary if e["surface"] in context["requested"]]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse_request({"paragraph": "Η ερευνήτρια εξετάζει το μεγάλο δείγμα. Η Μαρία είναι εδώ.", "grammar": f"2026-smg-{backend}", "lexical_mode": "assisted"})
    assert result["coverage"] == {"complete": 2, "total": 2, "failed": 0, "all_complete": True}
    assert calls and all(s["result"]["derivation"] for s in result["sentences"])
    assert any(e["source"] == "model" for e in result["sentences"][0]["result"]["lexical"]["entries"])
    if backend == "mltt" and shutil.which("coqc"):
        target = tmp_path / "Greek.v"
        target.write_text(result["sentences"][0]["result"]["coq"])
        checked = subprocess.run(["coqc", str(target)], capture_output=True, text=True, timeout=15)
        assert checked.returncode == 0, checked.stderr


def test_failure_drives_additional_sense_then_actual_reparse(monkeypatch):
    calls = []
    def provider(context, spec, **options):
        calls.append(context)
        assert context["failure"] is not None
        return {"entries": [entry("examines", "examine", "transitive", ["human", "object"])]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    events = []
    result = parse_request({"sentence": "The researcher examines a sample.", "grammar": "2026-english-mltt", "lexical_mode": "assisted"}, events.append)
    assert result["complete"]
    attempts = result["assistance"]["derivation_attempts"]
    assert [a["complete"] for a in attempts] == [False, True]
    assert "examine_" in result["words"][-1]["normalized"]
    assert len(calls) == 1
    assert [e["attempt"] for e in events if e["event"] == "start"] == [1, 2]
    second = [e for e in events if e.get("attempt") == 2]
    assert second[0]["initial"]["nodes"] == result["actions"][0]["nodes"]
    assert [e["frame"] for e in second if e["event"] == "frame" and e["channel"] == "actions"] == result["actions"][1:]


def test_rejected_batch_is_atomic_and_closed_classes_cannot_be_names():
    parser = icp("2026-smg-mltt")
    try:
        before = deepcopy(parser.semantic_profile)
        good = entry("ερευνήτρια", "ερευνήτρια", "noun", ["human"], "nom", "f")
        bad = entry("και", "και", "proper", ["human"], "nom", "m")
        with pytest.raises(ValueError):
            compile_entries(parser, {"entries": [good, bad]}, ["ερευνήτρια", "και"], "el")
        assert parser.semantic_profile == before
        assert "ερευνήτρια" not in parser.lexicon
    finally:
        parser.close()


def test_provider_failure_keeps_every_sentence_in_denominator(monkeypatch):
    def unavailable(*args, **kwargs):
        raise lexical_provider.ProposalUnavailable("Fixture outage")
    monkeypatch.setattr(lexical_provider, "propose", unavailable)
    result = parse_request({"paragraph": "Η ερευνήτρια διαβάζει. Ο Γιάννης είναι εδώ.", "grammar": "2026-smg-mltt", "lexical_mode": "assisted"})
    assert result["coverage"]["total"] == 2
    assert not result["complete"]
    assert result["sentences"][1]["complete"]
    assert result["sentences"][1]["context_gaps"] == [0]


def test_schema_and_backend_boundary():
    spec = schema("en", {"subtyping": {}})
    fields = spec["properties"]["entries"]["items"]["properties"]
    assert fields["case"]["enum"] == ["none"]
    with pytest.raises(ValueError, match="TTR"):
        parse_request({"sentence": "john walks", "grammar": "2015-english-ttr", "lexical_mode": "assisted"})


def test_plural_analysis_cannot_be_installed_as_a_singular_greek_noun():
    parser = icp("2026-smg-mltt")
    try:
        plural = entry("ερευνητές", "ερευνητής", "noun", ["human"], "nom", "m")
        plural["number"] = "pl"
        with pytest.raises(ValueError, match="plural"):
            compile_entries(parser, {"entries": [plural]}, ["ερευνητές"], "el")
        assert "ερευνητές" not in parser.lexicon
    finally:
        parser.close()


def test_validation_feedback_can_correct_a_provider_batch(monkeypatch):
    calls = []
    def provider(context, spec, **options):
        calls.append(context)
        noun = entry("ερευνήτρια", "ερευνήτρια", "noun", ["human"], "nom", "f")
        if len(calls) == 1:
            noun["domains"] = ["human", "object"]
        else:
            assert context["failure"]["kind"] == "proposal_validation"
            assert "exactly 1" in context["failure"]["message"]
        return {"entries": [noun]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse_request({"sentence": "Η ερευνήτρια είναι εδώ.", "grammar": "2026-smg-mltt", "lexical_mode": "assisted"})
    assert result["complete"] and len(calls) == 2
    assert [a["status"] for a in result["lexical"]["attempts"]] == ["rejected", "compiled"]
