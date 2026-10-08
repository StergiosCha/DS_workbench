"""Try a lexical preference through actual DS search, retaining the current path on failure."""

from dylan.action.lexical_action import LexicalAction
from dylan.action.meta.element import snapshot_meta_bindings, restore_meta_bindings
from dylan.dag.groundable_edge import CompletionEdge


def entry(action):
    return {"word": action.word, "template": action.metadata.get("template", action.action_type),
            "symbol": action.metadata.get("symbol", action.parameters[0] if action.parameters else None)}


def expanded_path(parser):
    from dynamicsyntax._parse import _active_path_edges

    result, index = [], -1
    for edge in _active_path_edges(parser):
        if edge.word is not None:
            index += 1
        for action in edge.actions:
            if isinstance(action, LexicalAction) and action.metadata.get("source") in {"dictionary", "model"}:
                result.append((index, edge, action))
    return result


def try_preference(parser, target_edge, symbols, observed_suffix, *, max_attempts=24):
    """Replay only this lexical subtree, bounded by the observed input and parser caps.

    Temporary exclusions constrain a probe, never the retained candidate inventory.
    All edge flags are restored; the new current path is installed only on success.
    Search work is still counted, including unsuccessful trials.
    """
    from dynamicsyntax._parse import _active_path_edges
    from dylan.workbench_api import semantic_type_errors

    dag = parser.get_state()
    anchor = target_edge.src
    while isinstance(dag.get_parent_edge(anchor), CompletionEdge):
        anchor = dag.get_parent(anchor)
    # The parser can split completion actions from each lexical alternative.
    # Find all choices at this word boundary, including those split paths.
    choices, allowed, pending = [], {}, [(anchor, [])]
    examined = 0
    while pending:
        node, path = pending.pop()
        examined += 1
        if examined > 512:
            return "candidate_limit"
        allowed.setdefault(node, set())
        for edge in dag.get_out_edges(node):
            if isinstance(edge, CompletionEdge):
                pending.append((edge.dst, [*path, edge]))
            elif edge.word == target_edge.word and any(
                    isinstance(action, LexicalAction) and action.metadata.get("symbol") in symbols
                    for action in edge.actions):
                choices.append(edge)
                for step in [*path, edge]:
                    allowed.setdefault(step.src, set()).add(step)
    if not choices:
        return "no_viable_preference"
    saved = (dag.cur, list(dag.word_stack), dag.exhausted, dag.first_tuple_after_last_word,
             list(dag.last_n), parser.last_cap_hit, parser.context.last_reference_failure)
    old_floor = getattr(dag, "backtrack_floor", None)
    old_allowed = dag.probe_allowed
    bindings = snapshot_meta_bindings()
    flags = {edge: set(edge._props) for edges in dag._out.values() for edge in edges}
    status = "no_viable_preference"
    try:
        # A word state can still await optional completion. Do not replace a
        # completable prefix with an unfinished frame just because its root has
        # not yet been thinned in the recorded word state.
        _, old_completed = parser.complete_tree(saved[0].tree.clone())
        old_complete = old_completed.is_complete()
        restore_meta_bindings(bindings)
        if parser.last_cap_hit:
            return "search_limit"
        dag.backtrack_floor = anchor
        dag.probe_allowed = allowed
        dag.cur = anchor
        dag.exhausted = False
        dag.word_stack = list(reversed(observed_suffix))
        for edges in allowed.values():
            for edge in edges:
                edge.set_seen(False)
        # A completion edge may precede the target's lexical action.
        if dag.go_first() is None:
            return status
        for _ in range(max_attempts):
            ok = not dag.word_stack or parser.parse_goal(None)
            if parser.last_cap_hit:
                return "search_limit"
            if not ok:
                return status
            tree = dag.cur.tree
            compatible = not semantic_type_errors(tree)
            if compatible and old_complete:
                _, completed = parser.complete_tree(tree.clone())
                compatible = completed.is_complete() and not semantic_type_errors(completed)
                if parser.last_cap_hit:
                    return "search_limit"
            if compatible:
                path = _active_path_edges(parser)
                if any(edge in choices for edge in path):
                    status = "revised"
                    return status
            if not parser.parse_goal(None):
                return "search_limit" if parser.last_cap_hit else status
        return "candidate_limit"
    finally:
        for edge, props in flags.items():
            edge._props = props
        dag.backtrack_floor = old_floor
        dag.probe_allowed = old_allowed
        dag.word_stack = saved[1]
        dag.exhausted = saved[2]
        parser.last_cap_hit = saved[5]
        parser.context.last_reference_failure = saved[6]
        if status != "revised":
            dag.cur, dag.first_tuple_after_last_word, dag.last_n = saved[0], saved[3], saved[4]
            restore_meta_bindings(bindings)
        else:
            dag.first_tuple_after_last_word = dag.cur
            dag.update_last_n()
        active = set(_active_path_edges(parser))
        for edges in dag._out.values():
            for edge in edges:
                edge.set_in_context(edge in active)
