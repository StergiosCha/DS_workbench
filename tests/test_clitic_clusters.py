"""Sentence-level local adjunction, fixing and order contrasts from chapter 3."""

import json
from pathlib import Path
import shutil

import pytest

from dynamicsyntax import parse
from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.tree.node_address import NodeAddress

ROOT = Path(__file__).parents[1] / "src/dynamicsyntax/grammars"


@pytest.fixture(params=["mltt", "classical"])
def grammar(request, tmp_path):
    reset_all_meta_bindings()
    target = tmp_path / "grammar"
    shutil.copytree(ROOT / f"2026-smg-{request.param}", target)
    # Isolated lexical preview. New surface rows await their own source review.
    with (target / "lexicon.txt").open("a") as out:
        out.write("mu clitic-gen speaker 1\ntu clitic-gen him 3\n"
                  "dos verb-ditransitive-imperative give\n"
                  "dosane verb-ditransitive give pro_group 3 pl\n"
                  "milo verb-finite talk speaker 1 sg\n")
    theory = json.loads((target / "semantics.json").read_text())
    theory["predicates"].update(give=["object", "object", "object"], talk=["object", "object"])
    theory["constants"]["pro_group"] = "human"
    theory["reference_classes"]["pro_group"] = {"person": 3, "number": "pl", "default": "pro_group"}
    theory["referents"]["pro_group"] = {"person": 3, "number": "pl"}
    (target / "semantics.json").write_text(json.dumps(theory))
    assert Grammar(target, strict=True)
    assert Lexicon(target, strict=True).load_stats.words_failed == 0
    yield target
    reset_all_meta_bindings()


@pytest.mark.parametrize("sentence,meaning", [
    ("mu to dosane.", "give(pro_group, theme, speaker)"),
    ("dos mu to.", "give(hearer, theme, speaker)"),
    ("dos to mu.", "give(hearer, theme, speaker)"),
])
def test_smg_clusters_build_and_fix_indirect_object(grammar, sentence, meaning):
    result = parse(sentence, grammar, trace=True)
    assert result.ok and result.tree.is_complete()
    assert str(result.semantics) == meaning
    assert NodeAddress("0P") not in result.tree
    assert str(result.tree[NodeAddress("0110")].get_formula()) == "speaker"
    assert any(step.action_name == "merge-local" for step in result.action_steps)


@pytest.mark.parametrize("sentence", ["to mu dosane.", "to dos mu.", "mu to dos.", "to ton ksero."])
def test_smg_rejects_reversed_indicative_and_preimperative_accusatives(grammar, sentence):
    assert not parse(sentence, grammar).ok


def test_genitive_can_fix_as_the_sole_internal_argument(grammar):
    result = parse("tu milo.", grammar)
    assert result.ok and result.tree.is_complete()
    assert str(result.semantics) == "talk(speaker, him)"
    assert str(result.tree[NodeAddress("010")].get_formula()) == "him"


def test_genitive_prefix_stays_unfixed_and_unresolved(grammar):
    result = parse("mu", grammar, trace=True)
    assert not result.tree.is_complete()
    assert result.action_steps[0].word == "mu"
    assert str(result.tree[NodeAddress("0P")].get_formula()) == "U_speaker"
    assert {str(a) for a in result.tree} == {"0", "0P"}


def test_grico_imperative_gate_blocks_accusative_before_genitive(grammar):
    path = grammar / "lexical-actions.txt"
    backend = json.loads((grammar / "semantics.json").read_text())["backend"]
    path.write_text((ROOT / f"2026-grico-{backend}" / "lexical-actions.txt").read_text())
    with (grammar / "lexicon.txt").open("a") as out:
        out.write("do verb-ditransitive-imperative give\n")
    assert parse("do mu to.", grammar).tree.is_complete()
    assert not parse("do to mu.", grammar).ok


@pytest.mark.skipif(not shutil.which("coqc"), reason="Coq not installed")
def test_cluster_export_compiles(grammar, tmp_path):
    import subprocess

    result = parse("dos mu to.", grammar)
    if result.semantics.backend == "classical":
        with pytest.raises(ValueError, match="constructive DS"):
            result.to_coq()
        return
    source = tmp_path / "Cluster.v"
    source.write_text(result.to_coq())
    subprocess.run(["coqc", str(source)], check=True, capture_output=True, text=True, timeout=15)
