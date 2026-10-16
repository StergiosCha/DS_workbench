import json

import pytest

from dylan import lexical_provider
from dylan.decision.gates import grammar_hash
from dylan.grammar_workshop import check_pack, export_grammar
from dylan.workbench_api import parse_request
from test_experimental_grammar import bare_program


def pack(backend="mltt"):
    grammar = "2026-english-" + backend
    return {
        "version": 1,
        "name": "Eyewear review",
        "grammar": grammar,
        "base_hash": grammar_hash(grammar),
        "seed_sentence": "A person entered the room with glasses",
        "proposal": bare_program(backend),
        "notes": "Personal review fixture. No wearing inference.",
        "origin": {"model": "fixture", "proposal_hash": ""},
        "tests": [
            {"sentence": "John walks with glasses.", "complete": True, "meaning": ""},
            {"sentence": "John walks with with glasses.", "complete": False, "meaning": ""},
        ],
    }


@pytest.fixture(autouse=True)
def no_model(monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail("Grammar reuse/review must not call a model")

    monkeypatch.setattr(lexical_provider, "propose", forbidden)
    monkeypatch.setattr("dylan.decision.client.request.urlopen", forbidden)


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_reuse_on_another_sentence_without_models(backend):
    p = pack(backend)
    r = parse_request(
        {
            "sentence": "John walks with glasses.",
            "grammar": p["grammar"],
            "grammar_pack": p,
            "allow_model_fallback": False,
        }
    )
    assert r["complete"], r["failure"]
    assert r["personal_grammar"]["selected_rule_ids"] == ["bare_eyewear", "with_equipment_rule"]
    assert r["personal_grammar"]["pack"] == p
    assert "experimental_grammar" not in r
    original = parse_request(
        {
            "sentence": "John walks with glasses.",
            "grammar": p["grammar"],
            "lexical_mode": "dictionary",
        }
    )
    assert not original["complete"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_checks_and_standalone_grammar_roundtrip(backend, tmp_path):
    p = pack(backend)
    report = check_pack(p)
    assert report["compiles"] and report["all_matched"], report
    result = export_grammar(p, tmp_path / "grammar")
    assert len(result["standalone"]) == 2
    assert json.loads((tmp_path / "grammar" / "grammar-pack.json").read_text()) == p
    with pytest.raises(ValueError, match="existing grammars"):
        export_grammar(p, tmp_path / "grammar")


def test_edits_invalidate_meaning_expectations_and_unknown_negatives_are_inconclusive():
    p = pack()
    p["tests"][0]["meaning"] = "unrelated"
    p["tests"].append(
        {"sentence": "John walks flibbertigibbetxyz.", "complete": False, "meaning": ""}
    )
    report = check_pack(p)
    assert [r["status"] for r in report["cases"]] == ["mismatch", "matched", "inconclusive"]
    assert not report["all_matched"]


def test_invalid_rules_and_changed_base_are_rejected():
    p = pack()
    p["proposal"]["rules"][0]["then"].append("delete(?Ty(mltt:object))")
    assert not check_pack(p)["compiles"]
    p = pack()
    p["base_hash"] = "a" * 64
    with pytest.raises(ValueError, match="base grammar has changed"):
        check_pack(p)


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_personal_rules_cannot_override_diagnosed_pcc(backend, monkeypatch):
    p = pack(backend)
    p["grammar"] = "2026-smg-" + backend
    p["base_hash"] = grammar_hash(p["grammar"])

    def forbidden(*args, **kwargs):
        pytest.fail("Do not install personal rules after a diagnosed PCC failure")

    monkeypatch.setattr("dylan.grammar_workshop.prepare", forbidden)
    result = parse_request(
        {
            "sentence": "του με έδωσε",
            "grammar": p["grammar"],
            "grammar_pack": p,
            "allow_model_fallback": False,
        }
    )
    assert not result["complete"]
    assert result["personal_grammar"]["blocked_by_reviewed_constraint"]
    assert not result["personal_grammar"]["applied"]
    assert not result["personal_grammar"]["rules"]


def test_negative_expectation_does_not_hide_real_dictionary_overgeneration():
    p = pack()
    # WordNet also supplies a determiner-taking noun reading. The personal
    # object-with rule permits it: this needs review, not a false passing badge.
    p["tests"] = [{"sentence": "John walks with a glasses.", "complete": False, "meaning": ""}]
    result = check_pack(p)
    assert result["cases"][0]["status"] == "mismatch"
    assert not result["all_matched"]


@pytest.mark.parametrize(
    "extra",
    [
        {"allow_model_fallback": True},
        {"lexical_mode": "jev"},
        {"experimental_rules": True},
        {"grammar": "2026-english-classical"},
        {"n_best": 3},
    ],
)
def test_pack_permission_and_backend_boundaries(extra):
    p = pack()
    with pytest.raises(ValueError):
        parse_request(
            {
                "sentence": "John walks.",
                "grammar": p["grammar"],
                "grammar_pack": p,
                "allow_model_fallback": False,
                **extra,
            }
        )
