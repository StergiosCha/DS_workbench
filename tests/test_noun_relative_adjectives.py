"""Cross-construction checks, including the reported copular failures."""

import shutil
import subprocess

import pytest

from dylan import lexical_dictionary, lexical_provider
from dylan.lexical_expansion import proposal
from dylan.workbench_api import parse_request


@pytest.fixture
def vocabulary(monkeypatch):
    original = lexical_dictionary.candidates

    def candidates(word):
        if word in {"great", "good", "skilled", "expensive"}:
            return [
                proposal(word, word, "subsective-adjective", ["object"], symbol=word + "_kind")
            ], []
        if word == "person":
            return [proposal(word, word, "noun", ["human"])], []
        return original(word)

    monkeypatch.setattr(lexical_dictionary, "candidates", candidates)


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("name", ["john", "mary", "george"])
@pytest.mark.parametrize("adjective", ["great", "good", "skilled", "expensive"])
@pytest.mark.parametrize(
    "frame",
    [
        "{name} is a {adjective} person.",
        "{name} was a {adjective} person.",
        "{name} is not a {adjective} person.",
        "john thinks that {name} is a {adjective} person.",
    ],
)
def test_noun_relative_adjectives_across_copular_frames(
    vocabulary, backend, name, adjective, frame
):
    result = parse_request(
        {
            "sentence": frame.format(name=name, adjective=adjective),
            "grammar": "2026-english-" + backend,
            "lexical_mode": "dictionary",
            "allow_model_fallback": False,
        },
        _trace=False,
    )
    assert result["complete"], result["failure"]
    meaning = result["words"][-1]["normalized"]
    assert adjective + "_kind" in meaning and "person" in meaning
    assert "subsective-adjective" in result["templates"]
    assert result["lexical"].get("model_requests", 0) == 0


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "sentence",
    [
        "a great person walks.",
        "all great people walk.",
        "john likes a great person.",
        "john is a great black dog.",
        "john is a black great dog.",
    ],
)
def test_quantifiers_objects_and_stacked_modifiers(vocabulary, backend, sentence, tmp_path):
    result = parse_request(
        {
            "sentence": sentence,
            "grammar": "2026-english-" + backend,
            "lexical_mode": "dictionary",
            "allow_model_fallback": False,
        }
    )
    assert result["complete"], result["failure"]
    if backend == "mltt" and shutil.which("coqc"):
        path = tmp_path / "Meaning.v"
        path.write_text(result["coq"])
        built = subprocess.run(
            [shutil.which("coqc"), str(path)], capture_output=True, text=True, timeout=15
        )
        assert built.returncode == 0, built.stderr


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "sentence",
    [
        "john is a great.",
        "john is great person.",
        "john is a great a person.",
        "john a great person.",
    ],
)
def test_incomplete_nominal_shapes_still_fail(vocabulary, backend, sentence):
    result = parse_request(
        {
            "sentence": sentence,
            "grammar": "2026-english-" + backend,
            "lexical_mode": "dictionary",
            "allow_model_fallback": False,
        },
        _trace=False,
    )
    assert not result["complete"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("mode", ["assisted", "jev"])
def test_unknown_name_uses_model_then_same_noun_relative_program(
    vocabulary, monkeypatch, backend, mode
):
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(
        lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "fixture"}
    )
    monkeypatch.setenv("DS_EPHEMERAL_MODELS", "1")

    def model(context, schema, **kwargs):
        if "requested" in context:
            entry = {
                "surface": "mitsotakis",
                "lemma": "mitsotakis",
                "template": "proper",
                "domains": ["human"],
                "case": "none",
                "gender": "none",
                "person": "none",
                "number": "sg",
                "verb_form": "none",
                "evidence": "Proper name; no claim about the person.",
            }
        else:
            entry = proposal("mitsotakis", "mitsotakis", "proper", ["human"])
        return {"entries": [entry]}, {"model": "fixture"}

    monkeypatch.setattr(lexical_provider, "propose", model)
    result = parse_request(
        {
            "sentence": "mitsotakis is a great person",
            "grammar": "2026-english-" + backend,
            "lexical_mode": mode,
            "allow_model_fallback": True,
        },
        _trace=False,
    )
    assert result["complete"], result["failure"]
    assert "mitsotakis" in result["words"][-1]["normalized"]


def test_dictionary_does_not_make_privatives_subsective():
    for word in ["fake", "former", "alleged"]:
        entries, _ = lexical_dictionary.candidates(word)
        assert not any(e["template"] == "subsective-adjective" for e in entries)


@pytest.mark.parametrize(
    "backend, expected",
    [
        ("mltt", "(john ∈ Σ x:person. great_kind(person, x))"),
        ("classical", "(person(john) ∧ great_kind(λ z:e. person(z), john))"),
    ],
)
@pytest.mark.parametrize("negative", [False, True])
def test_copular_meaning_preserves_noun_restriction_and_negation(
    vocabulary, backend, expected, negative
):
    sentence = "john is not a great person." if negative else "john is a great person."
    result = parse_request(
        {
            "sentence": sentence,
            "grammar": "2026-english-" + backend,
            "lexical_mode": "dictionary",
            "allow_model_fallback": False,
        },
        _trace=False,
    )
    assert result["words"][-1]["normalized"] == (f"¬({expected})" if negative else expected)


@pytest.mark.parametrize(
    "backend, expected",
    [
        ("mltt", "(john ∈ Σ x:(Σ x:dog. black(x)). great_kind(Σ x:dog. black(x), π₁(x)))"),
        ("classical", "((dog(john) ∧ black(john)) ∧ great_kind(λ z:e. (dog(z) ∧ black(z)), john))"),
    ],
)
def test_subsective_adjective_receives_the_modified_noun_restrictor(vocabulary, backend, expected):
    result = parse_request(
        {
            "sentence": "john is a great black dog.",
            "grammar": "2026-english-" + backend,
            "lexical_mode": "dictionary",
            "allow_model_fallback": False,
        },
        _trace=False,
    )
    assert result["words"][-1]["normalized"] == expected
