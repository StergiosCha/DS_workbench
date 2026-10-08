"""Sourced indefinite DPs preserve CN structure, case and witness semantics."""

from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan import workbench_api
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.corpus import compile_coq
from dylan.tree.label.labels import label_factory_create
from dylan.tree.node_address import NodeAddress

ROOT = Path(__file__).parents[1]
GRAMMARS = ROOT / "src/dynamicsyntax/grammars"


@pytest.fixture(params=["mltt", "classical"])
def grammar(request):
    reset_all_meta_bindings()
    yield GRAMMARS / f"2026-smg-{request.param}"
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence", [
    "diavasa ena vivlio.", "ena vivlio diavasa.",
    "to diavasa ena vivlio.", "ena vivlio to diavasa.",
    "διάβασα ένα βιβλίο.", "ένα βιβλίο διάβασα.",
    "το διάβασα ένα βιβλίο.", "ένα βιβλίο το διάβασα.",
])
def test_common_noun_dp_orders_merge_with_the_same_meaning(grammar, sentence):
    # Appendix B (B.4), with omission of the preceding discourse/ego and
    # disclosed word-order and spelling adaptations. Not a discourse model.
    result = parse(sentence, grammar, strict=True, trace=True)
    assert result.ok and result.tree.is_complete() and result.cap_hit is None
    assert all(address.is_fixed() for address in result.tree)
    assert any(step.action_name == "merge-general" for step in result.action_steps)
    root = NodeAddress("010")
    dp = result.tree[root]
    assert dp.contains(label_factory_create("Case(acc)"))
    assert not dp.contains(label_factory_create("?Ex.Tn(x)"))
    cn = result.tree[root.down0()]
    if result.semantics.backend == "mltt":
        assert str(cn.get_type()) == "CN" and str(cn.get_formula()) == "book"
        assert str(result.semantics.simplified()) == "Σ x:book. read(speaker, x)"
        assert len([addr for addr in result.tree if str(addr).startswith(str(root))]) == 3
        if shutil.which("coqc"):
            assert compile_coq(result.semantics.to_coq(), {}) == "passed"
    else:
        assert str(cn.get_type()) == "cn"
        assert str(result.tree[root.down0().down0()].get_type()) == "e"
        assert str(result.tree[root.down0().down1()].get_type()) == "e → cn"
        assert str(result.tree[root.down1()].get_type()) == "cn → e"
        assert len([addr for addr in result.tree if str(addr).startswith(str(root))]) == 5
        assert str(result.semantics) == "read(speaker, ε x0:e. book(x0))"


@pytest.mark.parametrize("sentence", [
    "diavasa ena.", "diavasa vivlio.", "ena γiani diavasa.",
    "ton vivlio diavasa.", "tin diavasa ena vivlio.",
    "ena vivlio tin diavasa.", "diavasa ena vivlio ena vivlio.",
    "ena vivlio diavasa ton γiani.",
])
def test_missing_heads_wrong_category_reference_mismatch_or_extra_dp_cannot_complete(grammar, sentence):
    result = parse(sentence, grammar, strict=True)
    assert not result.ok and result.semantics is None and result.cap_hit is None


def test_complete_nominal_content_keeps_unresolved_address_and_case(grammar):
    result = parse("ena vivlio", grammar, strict=True, trace=True)
    assert not result.ok and not result.tree.is_complete()
    dp = result.tree[NodeAddress("0*")]
    assert dp.get_formula() is not None and dp.get_type() is not None
    assert dp.contains(label_factory_create("?Ex.Tn(x)"))
    assert any(str(label).startswith("?</\\0>Ty(") for label in dp.labels)
    assert result.tree.pointer == NodeAddress("0")


def test_workbench_shows_noun_daughters_and_merge_as_separate_operations(grammar):
    result = workbench_api.parse_request({"sentence": "ena vivlio to diavasa.", "grammar": grammar.name})
    assert result["complete"]
    noun_steps = [frame for frame in result["operations"] if frame.get("rule") == "vivlio"]
    assert any(frame["label"] == "beta-reduce" for frame in noun_steps)
    if result["backend"] == "classical":
        assert any(frame["delta"]["created"] == ["0*00"] for frame in noun_steps)
        assert any(frame["delta"]["created"] == ["0*01"] for frame in noun_steps)
    merge = next(frame for frame in result["operations"] if frame["label"].startswith("merge("))
    assert "0*" in merge["delta"]["removed"]
    assert any(addr.startswith("010") for addr in merge["delta"]["created"])
