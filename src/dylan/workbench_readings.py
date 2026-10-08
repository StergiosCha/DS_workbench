"""Bounded primary completion search and enumeration/replay of DS analyses.

Primary search may select a retained complete path after all input is consumed.
Subsequent reading enumeration preserves that selected result. Search limits do
not establish grammaticality judgments.
"""

from __future__ import annotations

import json
from copy import deepcopy

from dylan.action.execution_trace import capture_effects
from dylan.action.meta.element import restore_meta_bindings, snapshot_meta_bindings


def operation_frame(effect, rule, index, rule_index, frame):
    """Decorations and pointer movement for one replayed action-calculus step."""
    before = {str(a): [str(label) for label in n.labels] for a, n in effect.before_tree.items()}
    after = {str(a): [str(label) for label in n.labels] for a, n in effect.after_tree.items()}
    return {
        **frame(effect.after_tree, effect.operation, index, "operation"),
        "rule": rule,
        "rule_index": rule_index,
        "pointer_before": str(effect.before_tree.pointer),
        "conditions": list(effect.conditions),
        "delta": {
            "created": sorted(after.keys() - before.keys()),
            "removed": sorted(before.keys() - after.keys()),
            "decorations": [
                {"node": addr,
                 "added": [label for label in after.get(addr, []) if label not in before.get(addr, [])],
                 "removed": [label for label in before.get(addr, []) if label not in after.get(addr, [])]}
                for addr in sorted(before.keys() | after.keys())
                if before.get(addr, []) != after.get(addr, [])
            ],
        },
    }


def strategy_tags(action_names, snapshot):
    """Structural operations used by this path, without discourse inferences."""
    tags = []
    if any(name in {"star-adjunction", "late-star-adjunction"} for name in action_names):
        tags.append("star-adjunction")
    if (any(name.startswith(("link", "topic-", "*link", "*topic-")) for name in action_names)
            or any("L" in edge["path"] for edge in snapshot["edges"])):
        tags.append("link")
    return tags or ["fixed"]


def replay_reading(parser, edges, completion_actions, completed, tokens, *, include_operations=True):
    """Replay one complete path from its axiom, at words, rules and operations."""
    from dynamicsyntax._parse import _steps_from_edge
    from dylan.workbench_api import tree_snapshot

    def frame(tree, label, index, kind):
        return {"label": label, "word_index": index, "kind": kind,
                **tree_snapshot(tree, parser.context)}

    bindings = snapshot_meta_bindings()
    try:
        axiom = edges[0].src.tree if edges else parser.get_best_tuple().tree
        initial = frame(axiom, "Axiom", -1, "axiom")
        channels = {name: [initial] for name in ("words", "actions", "operations")}
        index = -1

        def action_frames(after, name, effects):
            channels["actions"].append(frame(after, name, index, "action"))
            if effects:
                channels["operations"].extend(
                    operation_frame(effect, name, index, len(channels["actions"]) - 1, frame)
                    for effect in effects
                )
            else:
                channels["operations"].append({
                    **frame(after, name, index, "grouped"), "rule": name,
                    "trace_note": "This transition could not be replayed as individual effects.",
                })

        for edge in edges:
            if edge.word is not None:
                index = next((i for i in range(index + 1, len(tokens))
                              if tokens[i] == edge.word.word), index)
            for step in _steps_from_edge(parser, edge, operations=True) if include_operations else []:
                action_frames(step.after_tree, step.action_name, step.operations)
            if edge.word is not None:
                boundary = frame(edge.dst.tree, edge.word.word, index, "word")
                for channel in channels.values():
                    channel.append(boundary)
        replay = parser.get_best_tuple().tree.clone()
        for action in completion_actions if include_operations else []:
            with capture_effects() as effects:
                replay = parser.apply_actions(replay, [action])
            if replay is None:
                break
            action_frames(replay, action.name, effects)
        final = frame(completed, "Completion", len(tokens) - 1, "completion")
        for channel in channels.values():
            channel.append(final)
        return channels
    finally:
        restore_meta_bindings(bindings)


def seek_complete_primary(parser, *, max_candidates=32, previous_edges=(), tokens=()):
    """Try retained DS alternatives after a fully consumed but incomplete input.

    No punctuation or words are inserted. Failed search restores the original
    prefix/context; successful search leaves the actual selected path active.
    """
    from dynamicsyntax._parse import _active_path_edges
    from dylan.workbench_api import tree_snapshot

    # Ranking hooks refer back to the live parser. Retain that reference when
    # snapshotting its context, rather than cloning the parser/client as well.
    context, bindings = deepcopy(parser.context, {id(parser): parser}), snapshot_meta_bindings()
    search = {"candidates_examined": 1, "stop_reason": "candidate_limit"}
    selected = False
    try:
        while search["candidates_examined"] < max_candidates:
            if not parser.parse_goal(None):
                search["stop_reason"] = "search_limit" if parser.last_cap_hit else "exhausted"
                break
            actions, tree = parser.complete_tree(parser.get_best_tuple().tree)
            search["candidates_examined"] += 1
            if parser.last_cap_hit:
                search["stop_reason"] = "search_limit"
                break
            if not tree.is_complete():
                continue
            edges = [edge for edge in _active_path_edges(parser) if edge.edge_id not in previous_edges]
            if [edge.word.word for edge in edges if edge.word is not None] != list(tokens):
                continue
            snapshot = tree_snapshot(tree, parser.context)
            if snapshot["complete"] and not snapshot["type_errors"] and not snapshot["semantic_error"]:
                selected = True
                search["stop_reason"] = "complete"
                return (tree, actions, edges), search
        return None, search
    finally:
        if not selected:
            parser.context = context
            restore_meta_bindings(bindings)


def collect_readings(parser, first_tree, completion_actions, tokens, *, limit=1,
                     include_traces=False, max_candidates=100, previous_edges=()):
    """Enumerate unique complete trees/strategies using ordinary backtracking."""
    from dynamicsyntax._parse import _active_path_edges
    from dylan.workbench_api import tree_snapshot

    readings, seen = [], set()
    before = parser.stats.to_dict()
    examined = 0
    tree = first_tree
    reason = "reading_limit"
    while True:
        examined += 1
        bindings = snapshot_meta_bindings()
        try:
            snapshot = tree_snapshot(tree, parser.context)
            if snapshot["complete"] and not snapshot["type_errors"] and not snapshot["semantic_error"]:
                edges = [e for e in _active_path_edges(parser) if e.edge_id not in previous_edges]
                names = [action.name for edge in edges for action in edge.get_actions()]
                names.extend(action.name for action in completion_actions)
                tags = strategy_tags(names, snapshot)
                # Different orders of redundant decorations are the same tree.
                key = json.dumps([tags, snapshot["semantics"], sorted(
                    (node["id"], sorted(node["labels"])) for node in snapshot["nodes"]
                )], ensure_ascii=False)
                if key not in seen:
                    seen.add(key)
                    reading = {
                        "id": len(readings) + 1, "complete": True,
                        "strategy": "+".join(tags), "strategies": tags,
                        "action_names": names, "tree": snapshot,
                        "semantics": snapshot["semantics"], "normalized": snapshot["normalized"],
                        "coq": (tree.get_maximal_semantics(parser.context).to_coq()
                                if snapshot["backend"] == "mltt" else None),
                    }
                    if readings and include_traces:
                        reading["trace"] = replay_reading(parser, edges, completion_actions, tree, tokens)
                    readings.append(reading)
        finally:
            restore_meta_bindings(bindings)
        if len(readings) >= limit:
            break
        if examined >= max_candidates:
            reason = "candidate_limit"
            break
        if not parser.parse_goal(None):
            reason = "search_limit" if parser.last_cap_hit else "exhausted"
            break
        completion_actions, tree = parser.complete_tree(parser.get_best_tuple().tree)
        if parser.last_cap_hit:
            reason = "search_limit"
            break
    after = parser.stats.to_dict()
    extra = {key: (value[len(before[key]):] if isinstance(value, list) else value - before[key])
             for key, value in after.items()}
    extra["children_built_per_word"] = [
        value - (before["children_built_per_word"][i]
                 if i < len(before["children_built_per_word"]) else 0)
        for i, value in enumerate(after["children_built_per_word"])
    ]
    return readings, {
        "requested": limit, "returned": len(readings), "candidates_examined": examined,
        "exhausted": reason == "exhausted", "stop_reason": reason,
        "cap_hit": parser.last_cap_hit, "stats": extra,
        "top_n_cuts": after["top_n_cuts"],
    }
