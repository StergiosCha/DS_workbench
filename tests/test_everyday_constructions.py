"""Bilingual construction regressions and semantic/case negative controls."""

import shutil
import subprocess

import pytest

from dylan.workbench_api import parse_request
from dylan.action.meta.element import reset_all_meta_bindings


@pytest.fixture(autouse=True)
def clean_bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,text,meaning", [
    ("english", "I don't like the book.", "like(speaker,"),
    ("english", "I'm not a doctor.", "doctor"),
    ("english", "She is very red.", "very(red(her))"),
    ("english", "The black dog walks.", "black"),
    ("english", "You know me.", "know(you, speaker)"),
    ("smg", "Εγώ σε ξέρω.", "know(speaker, hearer)"),
    ("smg", "Εσύ με ξέρεις.", "know(hearer, speaker)"),
    ("smg", "Δεν είμαι γιατρός.", "doctor"),
    ("smg", "Ο γιατρός εξετάζει τον ασθενή.", "examine"),
    ("smg", "Είμαι πολύ μαλάκας.", "very("),
])
def test_everyday_typed_derivations(language, text, meaning, backend, tmp_path):
    result = parse_request({"sentence": text, "grammar": f"2026-{language}-{backend}", "lexical_mode": "bundled" if language == "english" else "off"})
    assert result["complete"], result["failure"]
    if text == "The black dog walks." and backend == "mltt":
        # The refinement is in the type of the presupposed referent.
        assert "black" in str(result["words"][-1]["context_assumptions"])
        assert "walk(π₁(definite_" in result["words"][-1]["normalized"]
    else:
        assert meaning in result["words"][-1]["normalized"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    if backend == "mltt" and shutil.which("coqc"):
        path = tmp_path / "Meaning.v"
        path.write_text(result["coq"])
        checked = subprocess.run(["coqc", str(path)], capture_output=True, text=True, timeout=15)
        assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("language,text", [
    ("english", "Me walks."), ("english", "John knows he."),
    ("english", "I am a."), ("english", "The walks."),
    ("smg", "Εγώ είσαι γιατρός."), ("smg", "Η άντρας περπατάει."),
    ("smg", "Ο γιατρός εξετάζει ο ασθενής."),
])
def test_missing_complements_and_case_person_conflicts_do_not_complete(language, text, backend):
    assert not parse_request({"sentence": text, "grammar": f"2026-{language}-{backend}"})["complete"]


def test_constructive_definite_discloses_contextual_identification():
    result = parse_request({"sentence": "The black dog walks.", "grammar": "2026-english-mltt"})
    assert result["complete"]
    assert result["words"][-1]["context_assumptions"]
    assert "identification is assumed" in str(result["words"][-1]["context_assumptions"])
    assert "Parameter the :" not in result["coq"]
