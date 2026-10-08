"""Small input snapshots contain observed state, without annotation leakage."""


def nodes_only_snapshot(tree):
    return {"pointer": str(tree.pointer), "nodes": [
        {"address": str(address), "labels": [str(label) for label in node.labels]}
        for address, node in tree.items()
    ]}


def entry_state(parser, word, actions):
    words = []
    dag = parser.context.get_dag()
    current = dag.get_current_tuple()
    while current is not None:
        edge = dag.get_parent_edge(current)
        if edge is None:
            break
        if edge.word is not None:
            words.append(edge.word.word)
        current = edge.src
    words.reverse()
    return {"grammar": getattr(parser.lexicon, "_resource_dir", None).name
            if getattr(parser.lexicon, "_resource_dir", None) else "loaded",
            "tokens_so_far": words,
            "next_word": word.word, "word_index": len(words),
            "tree": nodes_only_snapshot(dag.get_current_tuple().tree),
            "speaker": word.speaker,
            "entries": [{"id": f"e{i}", "template": action.action_type,
                         "params": list(getattr(action, "parameters", ())),
                         "lexical_evidence": getattr(action, "metadata", {})}
                        for i, action in enumerate(actions)]}


def fanout_state(parser, parent, edges):
    from dylan.action.lexical_action import LexicalAction

    dag = parser.get_state()
    words, current = [], parent
    while current is not None:
        edge = dag.get_parent_edge(current)
        if edge is None:
            break
        if edge.word is not None:
            words.append(edge.word.word)
        current = edge.src
    words.reverse()
    path = getattr(parser.lexicon, "_resource_dir", None)
    return {
        "grammar": path.name if path else "loaded", "tokens_so_far": words,
        "next_word": dag.word_stack[-1].word if dag.word_stack else None,
        "word_index": len(words), "tree": nodes_only_snapshot(parent.tree),
        "candidates": [
            {"id": f"c{i}", "tree": nodes_only_snapshot(edge.dst.tree),
             "operations": [a.name for a in edge.actions],
             "entries": [{"template": a.action_type, "parameters": list(a.parameters),
                          "lexical_evidence": getattr(a, "metadata", {})}
                         for a in edge.actions if isinstance(a, LexicalAction)],
             "incompleteness": edge.dst.tree.get_incompleteness_measure()}
            for i, edge in enumerate(edges)
        ],
    }
