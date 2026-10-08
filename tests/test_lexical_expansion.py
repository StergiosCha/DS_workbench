"""New vocabulary must still execute ordinary, typed DS lexical programs."""

from copy import deepcopy
import json
import shutil
import subprocess
from urllib.error import HTTPError

import pytest

from dynamicsyntax import icp
from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.lexical_expansion import bundled_entries, expand, proposal, schema, validate_entries
from dylan.workbench_api import parse_request, validate_request


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    reset_all_meta_bindings()
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "proposals.sqlite3"))
    yield
    reset_all_meta_bindings()


def parse(text, backend="mltt", mode="bundled"):
    return parse_request(
        {"sentence": text, "grammar": f"2026-english-{backend}", "lexical_mode": mode}
    )


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize(
    "text,symbols",
    [
        ("a cat sleeps.", ["sleep", "cat"]),
        ("every teacher greets a child.", ["greet", "teacher", "child"]),
        ("mary reads a letter.", ["read", "letter"]),
        ("a red cat runs.", ["red", "run", "cat"]),
        ("alice smiled.", ["alice", "smile"]),
    ],
)
def test_bundled_forms_build_native_trees(backend, text, symbols):
    result = parse(text, backend)
    assert result["complete"]
    assert all(s in result["words"][-1]["normalized"] for s in symbols)
    assert result["lexical"]["entries"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    assert any(
        op["kind"] == "operation" and "put(Fo(" in op["label"] for op in result["operations"]
    )
    if text == "a cat sleeps." and backend == "classical":
        assert len(result["words"][-1]["nodes"]) == 7
        assert any(n["type"] == "cn" for n in result["words"][-1]["nodes"])


def test_expansion_does_not_change_original_lexicon_or_weaken_types():
    assert parse("a cat sleeps.", mode="off")["failure"]["kind"] == "lexicon_gap"
    assert parse("a cat sleeps.")["complete"]
    assert parse("a cat sleeps.", mode="off")["failure"]["kind"] == "lexicon_gap"
    assert parse("a stone sleeps.")["failure"]["kind"] == "semantic_type_mismatch"
    # Classical e/t typing intentionally has no animal/human selectional check.
    assert parse("a stone sleeps.", "classical")["complete"]


def test_new_nominal_and_predicate_declarations_compile_in_coq(tmp_path):
    coqc = shutil.which("coqc")
    if not coqc:
        pytest.skip("Coq is not installed")
    result = parse("every teacher greets a child.")
    target = tmp_path / "Expansion.v"
    target.write_text(result["coq"])
    checked = subprocess.run([coqc, str(target)], capture_output=True, text=True, timeout=20)
    assert checked.returncode == 0, checked.stderr


def test_large_bundled_vocabulary_is_not_limited_as_model_output():
    parser = icp("2026-english-mltt")
    try:
        words = list(bundled_entries())
        assert len(words) > 24
        report = expand(parser, "2026-english-mltt", words, "bundled")
        assert not report["remaining"]
        assert all(word in parser.lexicon for word in words)
    finally:
        parser.close()


def test_model_schema_constrains_domains_to_declared_types():
    constrained = schema({"subtyping": {"animal": ["object"], "cat": ["animal"]}})
    domain_schema = constrained["properties"]["entries"]["items"]["properties"]["domains"]["items"]
    assert set(domain_schema["enum"]) == {"object", "animal", "cat"}


@pytest.mark.parametrize(
    "patch",
    [
        {"surface": "walks"},
        {"surface": "every"},
        {"surface": "sorry"},
        {"lemma": "that"},
        {"template": "universal"},
        {"symbol": "purr(x));abort"},
        {"symbol": "x"},
        {"symbol": "mk_cat"},
        {"symbol": "human"},
        {"domains": ["imaginary_sort"]},
        {"domains": ["animal", "animal"]},
        {"morphology": "participle"},
        {"symbol": "walk", "domains": ["human"]},
        {"actions": "abort"},
        {"evidence": ""},
        {"template": []},
        {"domains": [None]},
    ],
)
def test_invalid_batches_cannot_install_even_the_valid_prefix(patch):
    parser = icp("2026-english-mltt")
    try:
        before = deepcopy(parser.semantic_profile)
        valid = proposal("purrs", "purr", "intransitive", ["animal"])
        invalid = {**proposal("sings", "sing", "intransitive", ["human"]), **patch}
        with pytest.raises(ValueError):
            validate_entries(
                {"entries": [valid, invalid]},
                ["purrs", "sings", "every", "sorry", "walks"],
                parser.lexicon,
                parser.semantic_profile,
            )
        assert "purrs" not in parser.lexicon and "sings" not in parser.lexicon
        assert parser.semantic_profile == before
    finally:
        parser.close()


def test_new_noun_signature_and_forward_reference(monkeypatch):
    def propose(context, schema):
        return {
            "entries": [
                proposal("cuddles", "cuddle", "transitive", ["human", "kitten"]),
                proposal("kitten", "kitten", "noun", ["animal"]),
            ]
        }, {"model": "test", "provider": "fixture"}

    monkeypatch.setattr(lexical_provider, "propose", propose)
    result = parse("john cuddles a kitten.", mode="model")
    assert result["complete"]
    assert "cuddle(john" in result["words"][-1]["normalized"]
    assert "Record kitten" in result["coq"]
    assert "Parameter cuddle : human -> kitten -> Prop." in result["coq"]
    assert all(e["source"] == "model" for e in result["lexical"]["entries"])


def test_provider_cache_is_context_and_backend_specific_and_preserves_provenance(monkeypatch):
    calls = []

    def propose(context, schema):
        calls.append(context)
        return {"entries": [proposal("purrs", "purr", "intransitive", ["animal"])]}, {
            "model": "small-fixture",
            "provider": "fixture",
        }

    monkeypatch.setattr(lexical_provider, "propose", propose)
    first = parse("a cat purrs.", mode="model")
    second = parse("a cat purrs.", mode="model")
    assert first["complete"] and second["complete"] and len(calls) == 1
    assert second["lexical"]["status"] == "cached"
    assert (
        second["lexical"]["entries"][-1]["created_at"]
        == first["lexical"]["entries"][-1]["created_at"]
    )
    assert second["diagnostics"]["lexical_coverage"][2]["source"] == "model"
    assert parse("a dog purrs.", mode="model")["complete"]
    assert parse("a cat purrs.", "classical", mode="model")["complete"]
    assert len(calls) == 3


def test_multiple_valencies_are_actions_for_the_parser_to_choose(monkeypatch):
    monkeypatch.setattr(
        lexical_provider,
        "propose",
        lambda *args: (
            {
                "entries": [
                    proposal("sings", "sing", "intransitive", ["human"]),
                    proposal(
                        "sings", "sing", "transitive", ["human", "object"], symbol="sing_piece"
                    ),
                ]
            },
            {"model": "fixture", "provider": "fixture"},
        ),
    )
    one = parse("john sings.", mode="model")
    two = parse("john sings a book.", mode="model")
    assert one["complete"] and two["complete"]
    assert "sing(john)" == one["words"][-1]["normalized"]
    assert "sing_piece(john" in two["words"][-1]["normalized"]
    assert len(one["lexical"]["entries"]) == 2


def test_invalid_model_batch_does_not_erase_bundled_entries(monkeypatch):
    monkeypatch.setattr(
        lexical_provider,
        "propose",
        lambda *args: (
            {
                "entries": [
                    proposal("purrs", "purr", "intransitive", ["animal"]),
                    proposal("that", "that", "proper", ["object"]),
                ]
            },
            {"model": "fixture", "provider": "fixture"},
        ),
    )
    result = parse("a cat purrs.", mode="model")
    assert result["lexical"]["status"] == "rejected"
    assert [e["surface"] for e in result["lexical"]["entries"]] == ["cat"]
    assert result["failure"]["kind"] == "lexicon_gap"


def test_provider_failure_preserves_prefix_and_missing_word_diagnosis(monkeypatch):
    def fail(*args):
        raise lexical_provider.ProposalUnavailable("Timed out")

    monkeypatch.setattr(lexical_provider, "propose", fail)
    result = parse("a cat purrs.", mode="model")
    assert result["lexical"]["status"] == "unavailable"
    assert result["failure"]["kind"] == "lexicon_gap"
    assert result["words"][-1]["label"] == "cat"


@pytest.mark.parametrize(
    "mode,text,backend",
    [
        ("off", "a cat purrs.", "mltt"),
        ("bundled", "a cat purrs.", "mltt"),
        ("model", "a cat sleeps.", "mltt"),
        ("model", "no man walks.", "mltt"),
    ],
)
def test_no_provider_call_without_unknown_open_class_forms(monkeypatch, mode, text, backend):
    def unexpected(*args):
        pytest.fail("Unexpected network proposal")

    monkeypatch.setattr(lexical_provider, "propose", unexpected)
    parse(text, backend, mode)


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_greek_clitic_order_stays_under_its_existing_grammar(monkeypatch, backend):
    def unexpected(*args):
        pytest.fail("Greek expansion is not implemented")

    monkeypatch.setattr(lexical_provider, "propose", unexpected)
    for text, complete in [("τον αγαπά.", True), ("αγαπά τον.", False)]:
        result = parse_request(
            {"sentence": text, "grammar": f"2026-smg-{backend}", "lexical_mode": "model"}
        )
        assert result["complete"] is complete
        assert result["lexical"]["status"] == "unsupported"
        if not complete:
            assert result["failure"]["kind"] == "constraint_violation"


def test_dialogue_expansion_is_shared_across_speakers():
    result = parse_request(
        {
            "grammar": "2026-english-mltt",
            "lexical_mode": "bundled",
            "dialogue": [
                {"speaker": "A", "text": "every teacher greets", "boundary": "continue"},
                {"speaker": "B", "text": "a child.", "boundary": "continue"},
            ],
        }
    )
    assert result["complete"] and "greet" in result["words"][-1]["normalized"]


def test_invalid_mode_rejected_at_request_boundary():
    with pytest.raises(ValueError):
        validate_request(
            {
                "grammar": "2026-english-mltt",
                "sentence": "john walks.",
                "lexical_mode": {"url": "anything"},
            }
        )


def test_http_provider_sends_only_structured_proposals_and_redacts_errors(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.setenv("DS_LEXICAL_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "SECRET_TEST_KEY")
    seen = []

    def urlopen(request, timeout, context):
        seen.append(json.loads(request.data))
        assert timeout == 15
        assert request.get_header("Authorization") == "Bearer SECRET_TEST_KEY"
        raise HTTPError(request.full_url, 401, "SECRET_TEST_KEY", {}, None)

    monkeypatch.setattr(lexical_provider, "urlopen", urlopen)
    with pytest.raises(lexical_provider.ProposalUnavailable) as caught:
        lexical_provider.propose({"tokens": ["sings"]}, {"type": "object"})
    assert str(caught.value) == "Lexical provider returned HTTP 401."
    assert seen[0]["response_format"]["json_schema"]["strict"]
    assert "SECRET_TEST_KEY" not in json.dumps(lexical_provider.configuration())


def test_stream_reports_expansion_before_tree_growth(monkeypatch):
    monkeypatch.setattr(
        lexical_provider,
        "propose",
        lambda *args: (
            {
                "entries": [
                    proposal("purrs", "purr", "intransitive", ["animal"]),
                ]
            },
            {"model": "fixture", "provider": "fixture"},
        ),
    )
    events = []
    result = parse_request(
        {"grammar": "2026-english-mltt", "sentence": "a cat purrs.", "lexical_mode": "model"},
        events.append,
    )
    assert result["complete"]
    assert [e["event"] for e in events[:2]] == ["lexical", "start"]
    assert events[1]["lexical"]["entries"][-1]["surface"] == "purrs"
