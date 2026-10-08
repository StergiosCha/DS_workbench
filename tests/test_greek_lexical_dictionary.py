"""Corpus hypotheses must execute DS programs, preserve provenance and case."""

import shutil
import subprocess

import pytest

from dylan.greek_lexical_dictionary import source
from dylan.workbench_api import parse_request


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_attested_nouns_and_verb_form_compose_and_export(backend, tmp_path):
    result = parse_request({"sentence": "Η επιτροπή εγκρίνει την πρόταση.", "grammar": f"2026-smg-{backend}", "lexical_mode": "corpus"})
    assert result["complete"], result["failure"]
    assert "el_egkrino_" in result["words"][-1]["normalized"]
    entries = result["lexical"]["entries"]
    assert {r["surface"] for r in entries} == {"επιτροπή", "εγκρίνει", "πρόταση"}
    assert all(r["source"] == "corpus" and "training split" in r["evidence"] and r["program"] for r in entries)
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    if backend == "mltt" and shutil.which("coqc"):
        path = tmp_path / "Corpus.v"
        path.write_text(result["coq"])
        checked = subprocess.run(["coqc", str(path)], capture_output=True, text=True, timeout=15)
        assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize("text", ["Η επιτροπή εγκρίνει η πρόταση.", "Ο επιτροπή εγκρίνει την πρόταση."])
def test_corpus_forms_do_not_bypass_case_and_gender(text):
    result = parse_request({"sentence": text, "grammar": "2026-smg-mltt", "lexical_mode": "corpus"})
    assert not result["complete"]


def test_index_is_training_only_and_excludes_closed_classes():
    data = source()
    assert data["source_url"].endswith("el_gdt-ud-train.conllu")
    assert data["license"] == "CC BY-NC-SA 3.0"
    assert all(r["kind"] in {"noun", "adjective", "transitive", "intransitive", "ditransitive"} for rows in data["entries"].values() for r in rows)


def test_corpus_mode_does_not_mutate_original_lexicon():
    original = parse_request({"sentence": "Η επιτροπή εγκρίνει την πρόταση.", "grammar": "2026-smg-mltt"})
    assert not original["complete"] and original["failure"]["kind"] == "lexicon_gap"
