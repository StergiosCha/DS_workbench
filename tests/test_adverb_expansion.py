"""New manner words use the existing LINK rules, with real DS in both calculi."""
from copy import deepcopy
import shutil
import subprocess

import pytest

from dynamicsyntax import icp
from dylan import lexical_dictionary, lexical_provider
from dylan.lexical_expansion import proposal, validate_entries
from dylan.workbench_api import parse_request


@pytest.fixture
def provider(monkeypatch, tmp_path):
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "lexical.sqlite3"))
    monkeypatch.setenv("DS_JEV_LOG", str(tmp_path / "jev.jsonl"))
    monkeypatch.setattr(lexical_provider, "configuration", lambda: {"configured": True})
    monkeypatch.setattr(lexical_provider, "settings", lambda: {"url": "https://fixture", "model": "fixture"})
    dictionary = {
        "person": proposal("person", "person", "noun", ["human"]),
        "entered": proposal("entered", "enter", "transitive", ["human", "object"]),
        "room": proposal("room", "room", "noun", ["object"]),
    }
    monkeypatch.setattr(lexical_dictionary, "candidates", lambda word: ([deepcopy(dictionary[word])], []) if word in dictionary else ([], []))
    def no_jev_call(*args, **kwargs):
        pytest.fail("One supplied sense does not require a Jev request")
    monkeypatch.setattr("dylan.decision.client.request.urlopen", no_jev_call)
    calls = []
    def propose(context, spec, **options):
        calls.append(context)
        fields = spec["properties"]["entries"]["items"]["properties"]
        assert "adverb" in fields["template"]["enum"]
        assert "Prop" in fields["domains"]["items"]["enum"]
        assert "Prop" in context["allowed_domains"]
        entries = []
        for word in context.get("requested", context.get("unknown", [])):
            if word in dictionary:
                entry = deepcopy(dictionary[word])
            elif word in {"randomly", "carefully", "slowly", "accidentally"}:
                entry = proposal(word, word, "adverb", ["Prop"], evidence="Manner reading in the supplied prefix")
            else:
                continue
            if "requested" in context:
                entry = {k: v for k, v in entry.items() if k not in {"symbol", "morphology"}}
                entry.update(case="none", gender="none", person="none", number="sg" if entry["template"] == "noun" else "none", verb_form="finite" if entry["template"] == "transitive" else "none")
            entries.append(entry)
        return {"entries": entries}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    return calls


def parse(text, backend, mode, **kwargs):
    return parse_request({"sentence": text, "grammar": f"2026-english-{backend}", "lexical_mode": mode, **kwargs})


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("mode", ["model", "assisted", "jev"])
def test_reported_sentence_uses_a_new_modifier_link(provider, backend, mode):
    result = parse("the person entered the room randomly", backend, mode)
    assert result["complete"], result.get("failure")
    assert len(provider) == 1
    frame = result["words"][-1]
    assert "randomly" in frame["normalized"] and "enter" in frame["normalized"]
    assert any("L" in node["id"] for node in frame["nodes"])
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    entries = [entry for entry in result["lexical"]["entries"] if entry["surface"] == "randomly"]
    assert len(entries) == 3 and all(e["domains"] == ["Prop"] and e["source"] == "model" for e in entries)
    assert any("semantic-adverb(" in line for e in entries for line in e["program"])
    assert not any(e["symbol"] == "quickly" for e in entries)


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("word", ["carefully", "slowly", "accidentally"])
def test_template_generalizes_beyond_reported_word(provider, backend, word):
    result = parse(f"john walks {word}.", backend, "jev")
    assert result["complete"] and f"{word}(walk(john))" == result["words"][-1]["normalized"]
    assert len(provider) == 1 and result["lexical"]["model_requests"] == 1
    assert provider[0]["tokens"] == ["john", "walks", word]  # no future punctuation


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_model_off_bypasses_cached_new_adverbs_but_quickly_still_works(provider, backend):
    assert parse("john walks randomly.", backend, "jev", allow_model_fallback=True)["complete"]
    off = parse("john walks randomly.", backend, "jev", allow_model_fallback=False)
    assert not off["complete"] and off["lexical"]["model_requests"] == 0
    assert off["lexical"]["remaining"] == ["randomly"]
    assert parse("the person entered the room quickly", backend, "dictionary")["complete"]
    assert len(provider) == 1


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_attachment_alternatives_preserve_the_new_operator(provider, backend):
    result = parse("john thinks that mary walks randomly.", backend, "model", n_best=3, reading_traces=True)
    assert {reading["normalized"] for reading in result["readings"]} == {
        "randomly(think(john, walk(mary)))", "think(john, randomly(walk(mary)))"}
    assert all(r.get("trace", result)["words"][-1]["complete"] for r in result["readings"])


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_postverbal_template_does_not_license_preverbal_position(provider, backend):
    result = parse("john randomly walks.", backend, "model")
    assert not result["complete"]
    assert result["failure"]["token"] == "randomly"
    assert result["lexical"]["remaining"] == []  # syntax coverage, not a lexicon gap


@pytest.mark.parametrize("patch", [
    {"domains": ["object"]}, {"lemma": "quickly", "symbol": "quickly_new"},
    {"template": "noun", "domains": ["Prop"]},
    {"symbol": "randomly_other", "template": "transitive", "domains": ["Prop", "object"]},
])
def test_modifier_typing_and_identity_are_not_weakened(patch):
    parser = icp("2026-english-mltt")
    try:
        before = deepcopy(parser.semantic_profile)
        entry = {**proposal("randomly", "randomly", "adverb", ["Prop"]), **patch}
        with pytest.raises(ValueError):
            validate_entries({"entries": [entry]}, ["randomly"], parser.lexicon, parser.semantic_profile)
        assert parser.semantic_profile == before and "randomly" not in parser.lexicon
    finally:
        parser.close()


def test_new_modifier_is_declared_in_constructive_export(provider, tmp_path):
    result = parse("john walks randomly.", "mltt", "model")
    assert result["complete"] and "Parameter randomly : Prop -> Prop." in result["coq"]
    if not shutil.which("coqc"):
        pytest.skip("Coq executable unavailable; export declaration checked")
    target = tmp_path / "Adverb.v"
    target.write_text(result["coq"])
    checked = subprocess.run(["coqc", str(target)], capture_output=True, text=True, timeout=20)
    assert checked.returncode == 0, checked.stderr
