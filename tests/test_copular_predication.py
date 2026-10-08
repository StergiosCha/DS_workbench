"""First-person subjects and predicative a/an compose through ordinary DS trees."""

import shutil
import subprocess

import pytest

from dynamicsyntax import parse
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.formula.mltt.terms import parse_expr
from dylan.tree.node_address import NodeAddress
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def isolated():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def request(sentence, backend="mltt", **options):
    return parse_request({"sentence": sentence, "grammar": f"2026-english-{backend}", **options})


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "sentence,noun",
    [
        ("I am a doctor.", "doctor"),
        ("I am a black dog.", "dog"),
        ("john is a man.", "man"),
        ("you are a doctor.", "doctor"),
        ("every man is a doctor.", "doctor"),
        ("john thinks that I am a doctor.", "doctor"),
    ],
)
def test_nominal_copula_builds_a_property_not_a_choice_term(backend, sentence, noun, tmp_path):
    result = request(sentence, backend)
    assert result["complete"] and result["failure"] is None
    meaning = result["words"][-1]["normalized"]
    assert noun in meaning and "ε" not in meaning
    assert "copula" in result["templates"] and "predicative-article" in result["templates"]
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
    if sentence == "I am a doctor.":
        assert meaning == ("(speaker ∈ doctor)" if backend == "mltt" else "doctor(speaker)")
    if backend == "mltt" and shutil.which("coqc"):
        source = tmp_path / "Meaning.v"
        source.write_text(result["coq"])
        compiled = subprocess.run(
            [shutil.which("coqc"), str(source)], capture_output=True, text=True, timeout=15
        )
        assert compiled.returncode == 0, compiled.stderr
        assert "exists member" in result["coq"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "sentence",
    [
        "I am.",
        "I am a.",
        "I am doctor.",
        "I am black dog.",
        "I am a a doctor.",
        "I a doctor.",
        "john likes I.",
        "I does not am a doctor.",
    ],
)
def test_missing_article_complement_and_nominative_object_do_not_complete(backend, sentence):
    result = request(sentence, backend)
    assert not result["complete"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_first_person_is_a_contextual_subject(backend):
    assert request("I walk.", backend)["words"][-1]["normalized"] == "walk(speaker)"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_actual_wordnet_sentence_and_sense_provenance(backend):
    from dylan.lexical_dictionary import configuration

    if not configuration()["installed"]:
        pytest.skip("WordNet index is not installed")
    result = request("I am an asshole", backend, lexical_mode="dictionary", n_best=3)
    assert result["complete"]
    assert all(row["known"] for row in result["diagnostics"]["lexical_coverage"])
    assert "asshole_n09815188" in result["words"][-1]["normalized"]
    assert any(
        entry["surface"] == "asshole" and entry["source"] == "dictionary"
        for entry in result["lexical"]["entries"]
    )
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_speaker_changes_do_not_reinterpret_an_earlier_i(backend):
    result = parse_request(
        {
            "grammar": f"2026-english-{backend}",
            "dialogue": [
                {"speaker": "Alice", "text": "I am a doctor."},
                {"speaker": "Bob", "text": "I am a man.", "boundary": "new_tree"},
            ],
        }
    )
    assert result["complete"]
    assert "speaker_Alice" in result["context_trees"][0]["normalized"]
    assert "speaker_Bob" in result["words"][-1]["normalized"]
    assert "speaker_Alice" not in result["words"][-1]["normalized"]
    labels = [frame["label"] for frame in result["operations"]]
    assert "put(Fo(speaker_Alice))" in labels
    assert "put(Fo(speaker_Bob))" in labels


def test_final_trace_replays_original_speaker_after_word_stack_is_empty():
    result = parse("I am a doctor.", "2026-english-mltt", speaker="Alice", trace=True)
    assert result.ok and "speaker_Alice" in str(result.semantics)
    assert any(step.action_name == "i" for step in result.action_steps)
    step = next(step for step in result.action_steps if step.action_name == "i")
    assert "speaker_Alice" in str(step.after_tree[NodeAddress("00")].get_formula())
    assert not result.parser.get_state().word_stack_ref()


def test_classical_predication_substitution_avoids_variable_capture():
    term = parse_expr("predication(cn(x,pi(y,e,rel(x,y))),y)").normalize()
    assert str(term) == "Π y1:e. rel(y, y1)"
