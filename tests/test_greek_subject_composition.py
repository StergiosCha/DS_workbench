"""An overt complex Greek subject must survive MERGE and semantic composition."""

import shutil
import subprocess

import pytest

from dylan import lexical_provider
from dylan.workbench_api import parse_request


CASES = [
    ("ο μεγάλος άνθρωπος περπατάει", "person"),
    ("η μεγάλη γυναίκα περπατάει", "woman"),
    ("το μεγάλο παιδί περπατάει", "child"),
    ("περπατάει ο μεγάλος άνθρωπος", "person"),
    ("ο μεγάλος άνθρωπος τον αγαπά", "person"),
    ("τον αγαπά ο μεγάλος άνθρωπος", "person"),
    ("ο μεγάλος άνθρωπος είναι γιατρός", "person"),
    ("ένας μεγάλος άνθρωπος περπατάει", "person"),
    # Repeated adjective is an authored recursion probe, not a corpus judgment.
    ("ο μεγάλος μεγάλος άνθρωπος περπατάει", "person"),
]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("sentence,noun", CASES)
def test_modified_overt_subject_is_the_predicate_argument(backend, sentence, noun, tmp_path):
    result = parse_request(
        {
            "sentence": sentence,
            "grammar": f"2026-smg-{backend}",
            "lexical_mode": "corpus",
            "allow_model_fallback": False,
        }
    )
    assert result["complete"], result["failure"]
    final = result["words"][-1]
    subject = next(n for n in final["nodes"] if n["id"] == "00")
    assert subject["formula"] and subject["formula"] not in {"pro", "U_pro"}
    assert "pro" not in final["normalized"]
    meaning_and_assumptions = final["normalized"] + str(final["context_assumptions"])
    assert noun in meaning_and_assumptions and "big" in meaning_and_assumptions
    if sentence == "ο μεγάλος άνθρωπος περπατάει":
        assert final["normalized"] == (
            "walk(π₁(definite_00))" if backend == "mltt" else "walk(ι x0:e. (person(x0) ∧ big(x0)))"
        )
    if backend == "mltt" and shutil.which("coqc"):
        path = tmp_path / "Subject.v"
        path.write_text(result["coq"])
        checked = subprocess.run(["coqc", str(path)], capture_output=True, text=True, timeout=15)
        assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_reported_sentence_with_model_supplied_verb_preserves_the_overt_subject(
    backend, monkeypatch
):
    calls = []

    def provider(context, schema, **kwargs):
        calls.append(context)
        return {
            "entries": [
                {
                    "surface": "ήρθε",
                    "lemma": "έρχομαι",
                    "template": "intransitive",
                    "domains": ["object"],
                    "case": "none",
                    "gender": "none",
                    "person": "3",
                    "number": "sg",
                    "verb_form": "finite",
                    "evidence": "Fixture finite verb analysis.",
                }
            ]
        }, {"model": "fixture"}

    monkeypatch.setenv("DS_EPHEMERAL_MODELS", "1")
    monkeypatch.setattr(lexical_provider, "propose", provider)
    result = parse_request(
        {
            "sentence": "ο μεγάλος άνθρωπος ήρθε",
            "grammar": f"2026-smg-{backend}",
            "lexical_mode": "assisted",
        }
    )
    assert result["complete"], result["failure"]
    assert len(calls) == 1
    final = result["words"][-1]
    assert "pro" not in final["normalized"]
    assert "el_erchomai" in final["normalized"]
    assert "big" in final["normalized"] + str(final["context_assumptions"])


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_implicit_subject_remains_available(backend):
    result = parse_request({"sentence": "περπατάει", "grammar": f"2026-smg-{backend}"})
    assert result["complete"]
    assert result["words"][-1]["normalized"] == "walk(pro)"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "sentence",
    [
        "ο μεγάλος άνθρωπος περπατάω",
        "ο μεγάλος γυναίκα περπατάει",
        "ο μεγάλος περπατάει",
        "του με έδωσε",
    ],
)
def test_person_gender_missing_head_and_pcc_boundaries(backend, sentence):
    assert not parse_request(
        {
            "sentence": sentence,
            "grammar": f"2026-smg-{backend}",
            "lexical_mode": "corpus",
            "allow_model_fallback": False,
        }
    )["complete"]
