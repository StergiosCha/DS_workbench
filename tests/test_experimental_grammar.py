"""Model-written programs remain local, inspectable and distinct from reviewed DS."""
from copy import deepcopy

import pytest

from dynamicsyntax import icp
from dylan import lexical_dictionary, lexical_provider
from dylan.experimental_grammar import compile_proposal
from dylan.lexical_expansion import proposal
from dylan.workbench_api import parse_request


def bare_program(backend, word="glasses"):
    if backend == "mltt":
        when = ["?Ty(mltt:object)", r"¬<\/0>Ex.x", r"¬<\/1>Ex.x"]
        effects = ["put(Number(pl))", r"make(\/1)", r"go(\/1)", "put(Ty(mltt:arrow(CN,object)))",
                   "put(Fo(mltt:lam(A,CN,sigma(x,A,top))))", r"go(/\1)", r"make(\/0)", r"go(\/0)",
                   "put(Ty(mltt:CN))", "put(Fo(mltt:eyewear))"]
    else:
        when = ["?Ty(classical:e)", r"¬<\/0>Ex.x", r"¬<\/1>Ex.x"]
        effects = ["put(Number(pl))", r"make(\/1)", r"go(\/1)", "put(Ty(classical:arrow(cn,e)))",
                   "put(Fo(classical:lam(P,cn,choice_eps(P))))", "put(!)", r"go(/\1)", r"make(\/0)", r"go(\/0)",
                   "put(?Ty(classical:cn))", r"make(\/0)", r"go(\/0)", "put(Ty(classical:e))", "freshput(T,entity)", "put(!)",
                   r"go(/\0)", r"make(\/1)", r"go(\/1)", "put(Ty(classical:arrow(e,cn)))",
                   "put(Fo(classical:lam(x,e,cn(x,eyewear(x)))))", "put(!)"]
    declarations = [{"name":"eyewear", "kind":"sort", "domains":["object"]}]
    if backend == "classical":
        declarations.append({"name":"eyewear", "kind":"predicate", "domains":["object"]})
    declarations.append({"name":"with_equipment", "kind":"predicate", "domains":["object", "Prop"]})
    root = "mltt:Prop" if backend == "mltt" else "classical:t"
    return {"declarations":declarations, "rules":[
        {"surface":word, "name":"bare_eyewear", "explanation":"Existential eyewear referent, plural-only form. Cardinality and wearing are not inferred.", "when":when, "then":effects},
        {"surface":"with", "name":"with_equipment_rule", "explanation":"Object accompaniment via LINK; no claim that the object is worn.", "when":[f"Ty({root})", "¬Ex.?x"], "then":[r"go(\/1)", "semantic-pp(with_equipment)"]}]}


@pytest.fixture
def dictionary(monkeypatch, tmp_path):
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("DS_JEV_LOG", str(tmp_path / "jev.jsonl"))
    entries = {"person":proposal("person","person","noun",["human"]),
               "entered":proposal("entered","enter","transitive",["human","object"]),
               "room":proposal("room","room","noun",["object"])}
    monkeypatch.setattr(lexical_dictionary, "candidates", lambda word: ([deepcopy(entries[word])], []) if word in entries else ([], []))
    def forbidden(*args, **kwargs):
        pytest.fail("Unexpected provider call")
    monkeypatch.setattr(lexical_provider, "propose", forbidden)
    monkeypatch.setattr("dylan.decision.client.request.urlopen", forbidden)
    return entries


def request(backend, **extra):
    return {"sentence":"A person entered the room with glasses", "grammar":f"2026-english-{backend}", "lexical_mode":"assisted", "allow_model_fallback":True, "experimental_rules":True, **extra}


@pytest.mark.parametrize("backend", ["mltt", "classical"])
@pytest.mark.parametrize("mode", ["assisted", "jev"])
def test_new_bare_nominal_rule_runs_in_ds_but_is_not_installed_globally(dictionary, monkeypatch, backend, mode):
    calls = []
    def model(context, spec, **kwargs):
        calls.append(context)
        assert context["failure"] and context["existing_lexical_programs"]["a"]
        assert context["backend"] == backend
        return bare_program(backend), {"provider":"fixture", "model":"fixture"}
    monkeypatch.setattr(lexical_provider, "propose", model)
    events = []
    result = parse_request(request(backend, lexical_mode=mode), events.append)
    assert result["complete"], result["experimental_grammar"]
    exp = result["experimental_grammar"]
    assert exp["used"] and not exp["baseline"]["complete"] and len(calls) == 1
    assert exp["rules"][0]["program"][0].startswith("IF ?Ty(")
    assert "eyewear" in result["words"][-1]["normalized"]
    assert "with_" in result["words"][-1]["normalized"]
    assert "experimental:bare_eyewear" in result["templates"]
    assert any("L" in node["id"] for node in result["words"][-1]["nodes"])
    assert {e.get("experimental_stage") for e in events if e["event"] == "start"} == {"baseline", "proposal"}
    assert result["diagnostics"]["judgment"]["status"] == "not_assessed"
    ordinary = parse_request(request(backend, lexical_mode="dictionary", experimental_rules=False))
    assert not ordinary["complete"] and "experimental_grammar" not in ordinary


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_compiled_rule_does_not_invent_an_article_position(dictionary, monkeypatch, backend):
    monkeypatch.setattr(lexical_provider, "propose", lambda *args, **kwargs: (bare_program(backend), {}))
    result = parse_request(request(backend, sentence="John walks with a glasses."))
    assert not result["complete"]
    assert len(result["experimental_grammar"]["attempts"]) == 2


@pytest.mark.parametrize("effect", ["python(print('bad'))", "delete(?Ty(mltt:object))", "do_nothing", "put(Ty(e))", "put(Fo(classical:eyewear))", "put(SilentlyInventedLabel)", "make(\\/0)\nput(Fo(mltt:top))"])
def test_invalid_programs_cannot_mutate_the_grammar(effect):
    parser = icp("2026-english-mltt")
    try:
        before = deepcopy(parser.semantic_profile)
        raw = bare_program("mltt")
        raw["rules"][0]["then"].append(effect)
        with pytest.raises((ValueError, TypeError)):
            compile_proposal(raw, parser, ["glasses"])
        assert parser.semantic_profile == before and "glasses" not in parser.lexicon
    finally:
        parser.close()


def test_unknown_condition_and_wrong_surface_are_rejected():
    parser = icp("2026-english-mltt")
    try:
        raw = bare_program("mltt")
        raw["rules"][0]["when"].append("PretendEverythingFits")
        with pytest.raises(ValueError):
            compile_proposal(raw, parser, ["glasses"])
        with pytest.raises(ValueError):
            compile_proposal(bare_program("mltt", "anotherword"), parser, ["glasses"])
    finally:
        parser.close()


def test_validation_feedback_drives_second_request(dictionary, monkeypatch):
    calls = []
    def model(context, spec, **kwargs):
        calls.append(context)
        raw = bare_program("mltt")
        if len(calls) == 1:
            raw["rules"][0]["then"].append("delete(?Ty(mltt:object))")
        else:
            assert context["failure"]["kind"] == "proposal_validation"
        return raw, {}
    monkeypatch.setattr(lexical_provider,"propose",model)
    result = parse_request(request("mltt"))
    assert result["complete"]
    assert [a["status"] for a in result["experimental_grammar"]["attempts"]] == ["rejected", "complete"]


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_greek_program_uses_the_selected_native_backend(monkeypatch, backend):
    raw = {"declarations":[{"name":"suddenly", "kind":"modifier", "domains":["Prop"]}],
           "rules":[{"surface":"ξαφνικά", "name":"suddenly_link", "explanation":"Propositional suddenly modifier; no event timing inference.",
                     "when":[f"Ty({'mltt:Prop' if backend == 'mltt' else 'classical:t'})", "¬Ex.?x"],
                     "then":[r"go(\/1)", "semantic-adverb(suddenly)"]}]}
    monkeypatch.setattr(lexical_provider, "propose", lambda *args, **kwargs: (raw, {"model":"fixture"}))
    result = parse_request(request(backend, grammar=f"2026-smg-{backend}", sentence="ο γιώργος κοιμάται ξαφνικά"))
    assert result["complete"], result["experimental_grammar"]
    assert result["experimental_grammar"]["selected_rule_ids"] == ["suddenly_link"]
    assert "suddenly" in result["words"][-1]["normalized"]


def test_provider_failure_preserves_baseline(dictionary, monkeypatch):
    def failure(*args, **kwargs):
        raise lexical_provider.ProposalUnavailable("Fixture provider unavailable")
    monkeypatch.setattr(lexical_provider,"propose",failure)
    result = parse_request(request("mltt"))
    assert not result["complete"] and not result["experimental_grammar"]["used"]
    assert len(result["experimental_grammar"]["attempts"]) == 2


@pytest.mark.parametrize("backend", ["mltt", "classical"])
def test_existing_success_and_pcc_do_not_request_experimental_rules(dictionary, backend):
    good = parse_request(request(backend, sentence="John walks."))
    assert good["complete"] and not good["experimental_grammar"]["attempts"]
    bad = parse_request(request(backend, sentence="του με έδωσε", grammar=f"2026-smg-{backend}"))
    assert not bad["complete"] and bad["experimental_grammar"]["blocked_by_reviewed_constraint"]
    assert not bad["experimental_grammar"]["attempts"]


@pytest.mark.parametrize("overrides", [{"allow_model_fallback":False}, {"experimental_rules":"true"}, {"lexical_mode":"dictionary"}, {"grammar":"2015-english-ttr"}, {"compare_jev":True, "lexical_mode":"jev"}, {"dialogue":[{"speaker":"A","text":"John walks.","boundary":"continue"}]}])
def test_experimental_permission_and_backend_boundaries(overrides):
    with pytest.raises(ValueError):
        parse_request(request("mltt", **overrides))
