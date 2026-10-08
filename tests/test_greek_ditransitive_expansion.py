"""Case-based frame evidence and final DS search must retain both Greek objects."""
from copy import deepcopy
import shutil

import pytest

from dynamicsyntax import icp
from dylan import lexical_provider
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.assisted_parsing import compile_entries
from dylan.corpus import compile_coq
from dylan.greek_lexical_dictionary import source
from dylan.workbench_api import parse_request


@pytest.fixture(autouse=True)
def bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


def run(text, backend, mode="corpus", **kw):
    return parse_request({"sentence": text, "grammar": f"2026-smg-{backend}", "lexical_mode": mode, **kw})


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("text,roles", [
    ("Της το έδωσε", "(pro, theme, her)"),
    ("Της το έδωσε.", "(pro, theme, her)"),
    ("Του το δίνει", "(pro, theme, him)"),
    ("Της το δίνω", "(speaker, theme, her)"),
    ("Της το παρέχει", "(pro, theme, her)"),
])
def test_corpus_frame_keeps_recipient_and_theme_without_model(monkeypatch, backend, text, roles):
    def forbidden(*args, **kwargs):
        pytest.fail("An attested frame must not need an LLM request")
    monkeypatch.setattr(lexical_provider, "propose", forbidden)
    result = run(text, backend, "assisted")
    assert result["complete"] and result["assistance"]["verified"], result["failure"]
    assert result["words"][-1]["normalized"].endswith(roles)
    assert "_v3(" in result["words"][-1]["normalized"]
    assert result["lexical"]["attempts"] == []
    assert result["tokens"] == text.lower().replace(".", " .").split()
    assert not any(n["requirements"] for n in result["words"][-1]["nodes"])
    assert "verb-ditransitive" in result["templates"]
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("text", ["το της έδωσε", "της με έδωσε", "έδωσε της το", "της μου το έδωσε", "της το δώσει"])
def test_new_frames_do_not_bypass_clitic_or_dependent_form_constraints(backend, text):
    result = run(text, backend)
    assert not result["complete"]
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
@pytest.mark.parametrize("text", ["του με έδωσε", "του με έδωσε.", "της με έδωσε", "του σε έδωσε"])
def test_pcc_cluster_cannot_escape_into_a_nested_unfixed_node(backend, text):
    result = run(text, backend)
    assert not result["ok"] and not result["complete"]
    assert result["failure"]["index"] == 1
    assert result["failure"]["kind"] == "pcc_violation"
    assert result["diagnostics"]["grammar_constraint"]["kind"] == "pcc"
    assert result["words"][-1]["label"] == text.split()[0]
    assert not any("PP" in node["id"] for frame in result["words"] for node in frame["nodes"])


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_assistance_cannot_repair_a_pcc_violation(monkeypatch, backend):
    monkeypatch.setattr(lexical_provider, "propose", lambda *args, **kwargs: pytest.fail("PCC does not need a model repair"))
    result = run("του με έδωσε", backend, "assisted")
    assert not result["complete"] and result["failure"]["kind"] == "pcc_violation"
    assert result["lexical"]["attempts"] == []


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_end_of_input_search_selects_real_path_and_replays_it(backend):
    result = run("Της το έδωσε", backend, n_best=3, reading_traces=True)
    assert result["complete"]
    assert result["completion_search"]["stop_reason"] == "complete"
    assert result["completion_search"]["candidates_examined"] >= 2
    assert any(frame["kind"] == "backtrack" for frame in result["operations"])
    assert result["operations"][-1]["nodes"] == result["words"][-1]["nodes"]
    assert result["readings"] and all(r["complete"] for r in result["readings"])
    assert result["derivation"]["actions"]


def model_entry():
    # A real but unindexed verb; this does not overwrite corpus give semantics.
    return {"surface": "χάρισε", "lemma": "χαρίζω", "template": "ditransitive",
            "domains": ["object", "object", "object"], "case": "none", "gender": "none",
            "person": "3", "number": "sg", "verb_form": "finite",
            "evidence": "A giving-as-a-gift frame: subject, accusative theme and genitive recipient."}


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_model_can_propose_same_frame_and_ds_still_checks_it(monkeypatch, backend):
    calls = []
    def propose(context, schema, **kwargs):
        calls.append(context)
        assert context["templates"]["ditransitive"]["arity"] == 3
        assert context["backend"] == backend
        return {"entries": [model_entry()]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    result = run("της το χάρισε", backend, "assisted")
    assert result["complete"] and calls
    assert "el_charizo_" in result["words"][-1]["normalized"]
    assert result["words"][-1]["normalized"].endswith("(pro, theme, her)")
    assert any(e["source"] == "model" and e["template"] == "verb-ditransitive" for e in result["lexical"]["entries"])
    if backend == "mltt" and shutil.which("coqc"):
        assert compile_coq(result["coq"], {}) == "passed"


def test_ditransitive_proposal_cannot_lie_about_arity_or_person():
    parser = icp("2026-smg-mltt")
    before = deepcopy(parser.semantic_profile)
    try:
        for changes in ({"domains": ["object", "object"]}, {"person": "none"}, {"number": "pl"}, {"verb_form": "nonfinite"}):
            with pytest.raises(ValueError):
                compile_entries(parser, {"entries": [{**model_entry(), **changes}]}, ["χάρισε"], "el")
        assert parser.semantic_profile == before and "χάρισε" not in parser.lexicon
    finally:
        parser.close()


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_llm_can_repair_an_existing_incomplete_transitive_frame(monkeypatch, backend):
    from dylan import greek_lexical_dictionary
    data = deepcopy(source())
    data["entries"]["έδωσε"] = [r for r in data["entries"]["έδωσε"] if r["kind"] != "ditransitive"]
    monkeypatch.setattr(greek_lexical_dictionary, "source", lambda: data)
    calls = []
    def propose(context, schema, **kwargs):
        calls.append(context)
        assert context["failure"]["kind"] == "incomplete_tree"
        assert any("Case(gen)" in n["labels"] for n in context["failure"]["tree_at_failure"])
        return {"entries": [{**model_entry(), "surface": "έδωσε", "lemma": "δίνω"}]}, {"provider": "fixture", "model": "fixture"}
    monkeypatch.setattr(lexical_provider, "propose", propose)
    result = run("Της το έδωσε", backend, "assisted")
    assert result["complete"] and len(calls) == 1
    assert [a["complete"] for a in result["assistance"]["derivation_attempts"]] == [False, True]
    assert result["words"][-1]["normalized"].endswith("(pro, theme, her)")


def test_corpus_keeps_form_and_frame_evidence_separate():
    data = source()
    row = next(r for r in data["entries"]["έδωσε"] if r["kind"] == "ditransitive")
    assert row["features"]["Person"] == "3" and row["features"]["Tense"] == "Past"
    assert row["frame_evidence"]["sentence_id"] != row["sentence_id"]
    assert row["frame_evidence"]["theme"]["case"] == "acc"
    assert row["frame_evidence"]["recipient"]["case"] == "gen"
    assert not any(r["kind"] == "ditransitive" for r in data["entries"].get("περπατάει", []))
    assert not any(r["kind"] == "ditransitive" for r in data["entries"].get("δώσει", []))


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_paragraph_final_search_preserves_context_and_source(backend):
    result = parse_request({"paragraph": "Του το δίνει. Της το έδωσε", "grammar": f"2026-smg-{backend}", "lexical_mode": "corpus"})
    assert result["complete"] and result["coverage"]["complete"] == 2
    assert result["sentences"][1]["text"] == "Της το έδωσε"
    assert result["sentences"][1]["context_sentences"] == [0]
    assert result["sentences"][1]["result"]["words"][-1]["normalized"].endswith("(pro, theme, her)")


def test_unsuccessful_completion_search_preserves_live_ranker_and_prefix():
    from dylan.decision.ranking import FanoutRanker
    from dylan.nlp.types import utterance_from_text
    from dylan.workbench_readings import seek_complete_primary
    from dylan.workbench_api import tree_snapshot
    parser = icp("2026-smg-mltt")
    try:
        assert parser.parse_utterance(utterance_from_text("A", "της"))
        parser.get_state().rank_hook = FanoutRanker(parser)
        before = tree_snapshot(parser.get_best_tuple().tree, parser.context)
        selected, search = seek_complete_primary(parser, tokens=["της"], max_candidates=2)
        assert selected is None
        assert tree_snapshot(parser.get_best_tuple().tree, parser.context) == before
        assert parser.get_state().rank_hook.parser is parser
        assert search["stop_reason"] in {"exhausted", "candidate_limit"}
    finally:
        parser.close()
