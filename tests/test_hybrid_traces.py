import pytest

from dylan.hybrid.traces import DSAdapter, SequenceMemory, replay


def test_prefix_is_accepted_with_open_requirements_and_replays():
    adapter = DSAdapter()
    try:
        trace = adapter.probe("likes a", left_context="John")
        assert trace["status"] == "recognized_fragment"
        assert trace["state"]["pending"]
        assert trace["frames"][1]["observed"] == ["john", "likes"]
        assert all(f["replay_expanded"] for f in trace["frames"])
        assert replay(trace)["verified"]
    finally:
        adapter.close()


def test_unsupported_vocabulary_is_not_a_grammaticality_judgment():
    adapter = DSAdapter()
    try:
        result = adapter.probe("zzzzunknown")
        assert result["status"] == "unsupported_lexicon"
        assert "grammatical" not in result
    finally:
        adapter.close()


def test_completed_sentence_and_instrumentation_have_same_outcome():
    adapter = DSAdapter()
    try:
        traced = adapter.probe("John likes Mary", complete=True)
        plain = adapter.probe("John likes Mary", complete=True, trace=False)
        assert traced["status"] == plain["status"] == "complete"
        assert traced["state"] == plain["state"]
        assert traced["search"] == plain["search"]
        assert replay(traced)["verified"]
    finally:
        adapter.close()


def test_memory_preserves_order_and_does_not_prime_itself():
    memory = SequenceMemory(.5)
    sequence = ("VERB", "ADP", "DET")
    assert memory.activation(sequence) == 0
    memory.observe([sequence])
    assert memory.activation(sequence) == 1
    assert memory.activation(tuple(reversed(sequence))) == 0
    memory.observe([])
    assert memory.activation(sequence) == .5
    with pytest.raises(ValueError):
        SequenceMemory(2)


def test_macro_gates_observation_and_rolls_back_failed_actions():
    from copy import deepcopy
    from dylan.hybrid.traces import IncrementalMacro
    from dylan.action.meta.element import MetaElement

    class State(list):
        def clone(self):
            return deepcopy(self)

    class Action:
        def __init__(self, value, fail=False):
            self.value, self.fail = value, fail

        def instantiate(self):
            return self

        def exec(self, tree, context):
            tree.append(self.value)
            context["observed"].append(self.value)
            if self.fail:
                MetaElement.get("macro-fixture", str).value = "failed-binding"
                return None
            return tree

    original, context = State(), {"observed": []}
    macro = IncrementalMacro(("one", "two"), ((Action(1),), (Action(2),)))
    assert macro.step("two", original, context) is None
    one = macro.step("one", original, context)
    assert one.tree == [1] and not macro.complete
    assert original == [] and context == {"observed": []}
    two = macro.step("two", one.tree, one.context)
    assert two.tree == [1, 2] and two.context == {"observed": [1, 2]} and macro.complete
    meta = MetaElement.get("macro-fixture", str)
    meta.value = "before"
    failed = IncrementalMacro(("one",), ((Action(1), Action(2, fail=True)),))
    assert failed.step("one", original, context) is None
    assert failed.position == 0 and original == [] and context == {"observed": []}
    assert meta.value == "before"


def test_replay_detects_changed_dictionary_program_even_if_states_match():
    adapter = DSAdapter()
    try:
        record = adapter.probe("John likes Mary")
        record["frames"][0]["lexical_candidates"][0]["program"] += "\nchanged"
        assert not replay(record)["verified"]
    finally:
        adapter.close()


def test_native_macro_matches_expanded_action_programs():
    from copy import deepcopy
    from dynamicsyntax._parse import _active_path_edges
    from dylan.action.meta.element import snapshot_meta_bindings, restore_meta_bindings
    from dylan.hybrid.traces import IncrementalMacro, snapshot
    adapter = DSAdapter()
    try:
        adapter.probe("John")
        edge = _active_path_edges(adapter.parser)[-1]
        bindings = snapshot_meta_bindings()
        expanded, context = edge.src.tree.clone(), deepcopy(adapter.parser.context)
        for action in edge.get_actions():
            expanded = action.instantiate().exec(expanded, context)
            assert expanded is not None
        restore_meta_bindings(bindings)
        macro = IncrementalMacro(("john",), (tuple(edge.get_actions()),))
        result = macro.step("john", edge.src.tree, adapter.parser.context)
        assert result is not None and snapshot(result.tree) == snapshot(expanded)
    finally:
        adapter.close()
