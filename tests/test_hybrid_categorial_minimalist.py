import pytest

from dylan.hybrid import ccg, minimalist as mg
from dylan.hybrid.terms import app, const, free, lam, normalize, var


def test_lambda_substitution_avoids_capture():
    result = normalize(app(lam("x", lam("y", var("x"))), var("y")))
    assert free(result) == {"y"}
    assert result.name != "y"


def test_ccg_composition_and_raising_preserve_free_variables():
    left = ccg.Sign(ccg.cat("S/NP"), var("z"), ("left",))
    right = ccg.Sign(ccg.cat("NP/N"), const("right"), ("right",))
    combined = ccg.combine(left, right)[0]
    assert free(combined.meaning) == {"z"}
    raised = ccg.raise_np(ccg.Sign(ccg.cat("NP"), var("f"), ("name",)))
    assert free(raised.meaning) == {"f"}


def test_mg_intransitive_subject_is_a_left_specifier():
    assert mg.parse("john walks")["status"] == "derived"
    assert mg.parse("walks john")["status"] == "no_derivation_in_fragment"


def test_ccg_composes_an_unfinished_constituent():
    result = ccg.parse("will make his")
    assert result["status"] == "derived"
    assert any(a["category"] == str(ccg.cat("(S\\NP)/N")) for a in result["analyses"])
    assert not ccg.parse("will make his", composition=False)["analyses"]


def test_ccg_application_and_coordination_constraints():
    sentence = ccg.parse("john likes mary")
    assert any(a["category"] == "S" and "john" in a["meaning"] and "mary" in a["meaning"] for a in sentence["analyses"])
    assert any(a["category"] == "NP" for a in ccg.parse("john and mary")["analyses"])
    assert not any(a["category"] == "NP" for a in ccg.parse("john and his")["analyses"])


def test_minimalist_merge_and_move_are_feature_licensed():
    simple = mg.parse("john likes mary")
    assert simple["status"] == "derived"
    assert "((likes john) mary)" in simple["analyses"][0]["meaning"]
    question = mg.parse("who did john like")
    assert question["status"] == "derived"
    assert any(h["operation"] == "Move" for h in question["analyses"][0]["history"])
    assert "who" in question["analyses"][0]["meaning"]
    assert mg.parse("who john likes")["status"] == "no_derivation_in_fragment"


def test_merge_cannot_reuse_same_lexical_occurrence_or_mismatch_features():
    a = mg.item("john", ["d"], const("john"), 0)
    with pytest.raises(mg.DerivationError):
        mg.merge(a, a)
    b = mg.item("likes", ["=v", "v"], const("like"), 1)
    with pytest.raises(mg.DerivationError):
        mg.merge(b, a)


def test_shortest_move_and_bounds_are_explicit():
    a = mg.Mover(("who",), ("-wh",), "x", const("who"))
    b = mg.Mover(("what",), ("-wh",), "y", const("what"))
    with pytest.raises(mg.DerivationError):
        mg.well_formed_movers((a, b))
    assert mg.parse("who did john like", cap=2)["status"] == "search_limit"
