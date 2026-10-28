import pytest

from dylan.hybrid.features import (
    Construction, ConstructionRegistry, FeatureGraph, Node, TypeSystem,
    UnificationError, linguistic_types, nominal_description, unify,
)
from dylan.hybrid.lfg import FStructure, Predicate, transitive


def test_agreement_refinement_and_failure_do_not_mutate_inputs():
    types = linguistic_types()
    article = nominal_description(gender="masc", case="nom")
    noun = nominal_description(gender="masc", number="sg", referent="x")
    before = article.canonical()
    merged = unify(article, noun, types)
    assert merged.nodes[merged.at(["AGR", "NUMBER"])].sort == "sg"
    assert merged.nodes[merged.at(["INDEX"])].atom == "x"
    with pytest.raises(UnificationError):
        unify(article, nominal_description(gender="fem"), types)
    assert article.canonical() == before


def test_reentrancy_propagates_conflicts():
    types = TypeSystem({"top": (), "pair": ("top",), "value": ("top",),
                        "a": ("value",), "b": ("value",)},
                       {"pair": {"FIRST": "value", "SECOND": "value"}})
    shared = FeatureGraph("r", {"r": Node("pair", {"FIRST": "x", "SECOND": "x"}), "x": Node("value")})
    conflict = FeatureGraph("r", {"r": Node("pair", {"FIRST": "x", "SECOND": "y"}),
                                  "x": Node("a"), "y": Node("b")})
    with pytest.raises(UnificationError):
        unify(shared, conflict, types)
    compatible = FeatureGraph("r", {"r": Node("pair", {"FIRST": "x"}), "x": Node("a")})
    result = unify(shared, compatible, types)
    assert result.at(["FIRST"]) == result.at(["SECOND"])


def test_cyclic_graph_unification_terminates():
    types = TypeSystem({"top": (), "list": ("top",)}, {"list": {"TAIL": "list"}})
    first = FeatureGraph("x", {"x": Node("list", {"TAIL": "x"})})
    second = FeatureGraph("y", {"y": Node("list", {"TAIL": "y"})})
    result = unify(first, second, types)
    assert result.at(["TAIL"]) == result.root


def test_inappropriate_features_and_inheritance_conflicts():
    types = linguistic_types()
    invalid = FeatureGraph("x", {"x": Node("nominal", {"GENDER": "y"}), "y": Node("masc")})
    with pytest.raises(UnificationError):
        invalid.validate(types)
    registry = ConstructionRegistry(types)
    registry.add(Construction("masculine", (), nominal_description(gender="masc"), "", "fixture"))
    registry.add(Construction("singular", (), nominal_description(number="sg"), "", "fixture"))
    registry.add(Construction("both", ("masculine", "singular"), nominal_description(), "", "fixture"))
    assert registry.resolve("both").nodes[registry.resolve("both").at(["AGR", "GENDER"])].sort == "masc"
    with pytest.raises(UnificationError):
        registry.add(Construction("conflict", ("both",), nominal_description(gender="fem"), "", "fixture"))
    assert "conflict" not in registry.entries


def test_lfg_closure_and_coherence_are_distinct():
    structure = transitive("John", "like")
    assert structure.check()["valid"] and not structure.check()["complete"]
    assert not structure.check(closed=True)["valid"]
    structure = transitive("John", "like", "Mary")
    assert structure.check(closed=True)["complete"]
    structure.functions["f0"]["COMP"] = "f2"
    assert structure.check()["issues"][0]["kind"] == "coherence"


def test_lfg_functional_uncertainty_shares_target_and_reports_bounds():
    structure = FStructure("f0", {
        "f0": Predicate("say", ("SUBJ", "COMP")), "f1": Predicate("read", ("SUBJ", "OBJ")),
        "john": Predicate("John", ()), "mary": Predicate("Mary", ()), "book": Predicate("book", ())},
        {"f0": {"SUBJ": "john", "COMP": "f1"}, "f1": {"SUBJ": "mary", "OBJ": "book"}})
    assert structure.link_topic("book", max_depth=0)["reason"] == "bound_exhausted"
    linked = structure.link_topic("book", max_depth=1)
    assert linked["linked"]
    assert linked["paths"][0]["path"] == ("COMP", "OBJ")
    assert structure.functions["f0"]["TOPIC"] == structure.functions["f1"]["OBJ"]
    assert structure.check(closed=True)["complete"]
