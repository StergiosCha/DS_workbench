"""JSON snapshots for the local DS Workbench, executed in an isolated worker."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from typing import Any

from dylan.action.meta.element import restore_meta_bindings, snapshot_meta_bindings
from dylan.action.execution_trace import capture_effects
from dylan.nlp.types import utterance_from_text
from dylan.tree.label.labels import FeatureLabel, Requirement
from dylan.tree.tree import Tree

EXAMPLES = [
    {"sentence": "a man knows you.", "label": "A transitive sentence"},
    {"sentence": "a man arrives.", "label": "A simple assertion"},
    {"sentence": "does a man arrive?", "label": "A question"},
    {"sentence": "john likes mary.", "label": "Proper names"},
]


def configuration() -> dict[str, Any]:
    from dynamicsyntax import get_grammars
    from dylan.greek_workbench import configuration as greek_configuration
    from dylan.dialogue_workbench import configuration as dialogue_configuration
    from dylan.lexical_expansion import configuration as lexical_configuration
    from dylan.decision.workbench import configuration as decision_configuration
    from dylan.paragraph_workbench import configuration as paragraph_configuration

    greek = greek_configuration()

    return {
        "engine": "DyLan / Python",
        "semantics": "Classical DS / Constructive DS / DS-TTR",
        "default_grammar": "2026-english-mltt",
        "systems": [
            {
                "id": "mltt",
                "label": "Constructive DS · Σ / Π",
                "grammars": [
                    "2026-english-mltt",
                    *[g for g in greek["grammars"] if g.endswith("-mltt")],
                ],
            },
            {
                "id": "classical",
                "label": "Classical DS · λ / ε / τ",
                "grammars": [
                    "2026-english-classical",
                    *[g for g in greek["grammars"] if g.endswith("-classical")],
                ],
            },
            {
                "id": "ttr",
                "label": "DS-TTR · records",
                "grammars": [g for g in get_grammars() if "ttr" in g and g != "ttr"],
            },
        ],
        "native_examples": [
            {"sentence": s, "label": label}
            for s, label in [
                ("a man walks.", "Indefinite"),
                ("I am a doctor.", "First-person subject and nominal predication"),
                ("every man walks.", "Universal"),
                ("every doctor examined a patient.", "Quantifier scope"),
                ("a black dog walks.", "Adjective refinement"),
                ("john walks quickly.", "VP modifier through LINK"),
                ("john walks because mary walks later.", "Finite causal clause and temporal modifier"),
                ("because mary walks later, john walks today.", "Preposed reason with an explicit comma"),
                ("when mary walks, john walks.", "Temporal clause with explicit main/subordinate contents"),
                ("john walks although mary walks later.", "Concessive clause"),
                ("if bill shouts, john walks because mary walks.", "Compose conditional and causal clauses"),
                ("bill shouts.", "Nominal type checking"),
                ("john thinks that mary walks.", "Clausal complement"),
                ("john says that mary thinks a man walks.", "Nested clauses"),
                ("john thinks that mary walks quickly.", "Two adverb attachments: request multiple analyses"),
                ("a man who walks arrives.", "Subject relative through LINK and MERGE"),
                ("a man who mary knows walks.", "Object relative through LINK and MERGE"),
                ("john, who mary knows, walks.", "Nonrestrictive LINK: preserve the name and add a separate assertion"),
                ("john gives mary a book.", "Give: recipient and theme"),
                ("john gives a book to mary.", "Give: theme and to-recipient"),
                ("john reads a book in a library.", "PP modifier with a DP complement"),
                ("john relies on mary.", "Selected on-complement"),
                ("john thinks mary walks in a park.", "Two PP attachments: request multiple analyses"),
            ]
        ],
        "grammars": [g for g in get_grammars() if g != "ttr"],
        "examples": EXAMPLES,
        "greek": greek,
        "dialogue": dialogue_configuration(),
        "paragraph": paragraph_configuration(),
        "lexical": lexical_configuration(),
        "decision": decision_configuration([g for g in get_grammars() if g.startswith("2026-")]),
        "max_characters": 500,
        "max_tokens": 40,
        "readings": {"default": 1, "maximum": 8, "dialogue_maximum": 1},
    }


def validate_request(payload: Any, *, sentence_limits=(500, 40)) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Send a JSON object with a sentence and grammar.")
    sentence, grammar = payload.get("sentence"), payload.get("grammar")
    if "paragraph" in payload:
        from dylan.paragraph_workbench import validate_paragraph

        sentence, _ = validate_paragraph(payload)
    elif "dialogue" in payload:
        from dylan.dialogue_workbench import validate_dialogue

        turns = validate_dialogue(payload)
        sentence = "\n".join(f"{t['speaker']}: {t['text']}" for t in turns)
    else:
        if not isinstance(sentence, str) or not sentence.strip():
            raise ValueError("Enter a sentence to parse.")
        if len(sentence) > sentence_limits[0]:
            raise ValueError(f"Use a sentence of at most {sentence_limits[0]} characters.")
        if len(utterance_from_text("Dylan", sentence).words) > sentence_limits[1]:
            raise ValueError(f"Use a sentence of at most {sentence_limits[1]} tokens.")
    if not isinstance(grammar, str) or grammar not in configuration()["grammars"]:
        raise ValueError("Choose one of the available grammars.")
    if payload.get("scope", "narrow") not in {"narrow", "wide"}:
        raise ValueError("Choose narrow or wide existential scope.")
    top_n = payload.get("top_n", 3)
    if type(top_n) is not int or not 0 <= top_n <= 20:
        raise ValueError("top_n must be an integer from 0 to 20 (0 keeps all entries).")
    if not isinstance(payload.get("strict", False), bool):
        raise ValueError("strict must be a boolean.")
    if type(payload.get("allow_model_fallback", True)) is not bool:
        raise ValueError("allow_model_fallback must be a boolean.")
    n_best = payload.get("n_best", 1)
    if type(n_best) is not int or not 1 <= n_best <= 8:
        raise ValueError("n_best must be an integer from 1 to 8.")
    if "dialogue" in payload and n_best != 1:
        raise ValueError("n_best must be 1 for dialogue; alternative transcript analyses are not implemented.")
    if "paragraph" in payload and n_best != 1:
        raise ValueError("n_best must be 1 for paragraphs.")
    if type(payload.get("reading_traces", False)) is not bool:
        raise ValueError("reading_traces must be a boolean.")
    if payload.get("decision_mode", "off") not in {"off", "stub", "jev"}:
        raise ValueError("Choose off, stub or jev decision mode.")
    from dylan.lexical_expansion import validate_options

    validate_options(payload)
    return sentence.strip(), grammar


def semantic_type_errors(tree: Tree) -> list[dict[str, str]]:
    """Deterministic application failures on already decorated daughters."""
    type_errors = []
    if tree.semantic_profile:
        from dylan.formula.mltt.semantics import SemanticFormula, SemanticType, apply_semantics, left_consumes_predicate

        for addr, node in tree.items():
            left, right = tree.get(addr.down0()), tree.get(addr.down1())
            if node.get_formula() is not None or left is None or right is None:
                continue
            lt, rt = left.get_type(), right.get_type()
            lf, rf = left.get_formula(), right.get_formula()
            if (
                isinstance(lt, SemanticType)
                and isinstance(rt, SemanticType)
                and isinstance(lf, SemanticFormula)
                and isinstance(rf, SemanticFormula)
                and not left.contains(Requirement(FeatureLabel("CLOSED")))
                and not right.contains(Requirement(FeatureLabel("CLOSED")))
            ):
                args = (lf, lt, rf, rt) if left_consumes_predicate(lt, rt, reflexive=left.contains(FeatureLabel("REFLEXIVE"))) else (rf, rt, lf, lt)
                try:
                    apply_semantics(*args, tree.semantic_profile)
                except TypeError as exc:
                    type_errors.append({"node": str(addr), "message": str(exc)})
    return type_errors


def tree_snapshot(tree: Tree, context: Any) -> dict[str, Any]:
    """Serialize actual decorations and a partial semantic projection of this state."""
    nodes, edges = [], []
    for addr, node in tree.items():
        node_id = str(addr)
        labels = [str(label) for label in node.labels]
        requirements = [str(label) for label in node.labels if isinstance(label, Requirement)]
        nodes.append(
            {
                "id": node_id,
                "labels": labels,
                "requirements": requirements,
                "type": str(node.get_type()) if node.get_type() is not None else None,
                "required_type": (
                    str(node.get_required_type()) if node.get_required_type() is not None else None
                ),
                "formula": str(node.get_formula()) if node.get_formula() is not None else None,
                "fixed": addr.is_fixed(),
                "clause": node.contains(FeatureLabel("CLAUSE")),
                "clause_closed": node.contains(FeatureLabel("CLOSED")),
            }
        )
        parent = addr.up()
        while parent is not None and parent not in tree:
            parent = parent.up()
        if parent is not None:
            path = node_id[len(str(parent)) :]
            edges.append(
                {
                    "source": str(parent),
                    "target": node_id,
                    "path": path,
                    "kind": "link"
                    if "L" in path or "C" in path
                    else "unfixed"
                    if any(c in path for c in "*UP")
                    else "fixed",
                }
            )
            if path == "B":
                # The stored predecessor points by LINK to the clause, as in
                # thesis (2.93)-(2.94); it is not a daughter of that clause.
                edges[-1].update(source=node_id, target=str(parent), path="L", kind="link")
    # Semantic projection may introduce underspecified formulae. Work on a copy
    # and restore rule bindings so inspection cannot alter the parse itself.
    bindings = snapshot_meta_bindings()
    try:
        formula = tree.clone().get_maximal_semantics(context).evaluate()
        semantics = str(formula)
        normalized = str(formula.simplified()) if hasattr(formula, "simplified") else None
        if tree.semantic_profile and tree.get_root_node().get_formula() is None:
            semantics = normalized = None
        semantic_error = None
    except (ValueError, TypeError, RuntimeError, RecursionError) as exc:
        semantics = None
        normalized = None
        semantic_error = f"Semantic projection unavailable: {type(exc).__name__}"
    finally:
        restore_meta_bindings(bindings)
    type_errors = semantic_type_errors(tree)
    return {
        "pointer": str(tree.pointer),
        "nodes": nodes,
        "edges": edges,
        "complete": tree.is_complete(),
        "semantics": semantics,
        "normalized": normalized,
        "backend": tree.semantic_profile.get("backend", "ttr"),
        "type_errors": type_errors,
        "semantic_error": semantic_error,
        "context_assumptions": list(tree.semantic_profile.get("context_assumptions", {}).values()),
        "reflexive_bindings": tree.semantic_profile.get("reflexive_bindings", []),
        "speech_act": (
            {"kind": "polar_question", "content": semantics, "asserted": False}
            if tree.get_root_node().contains(FeatureLabel("POLAR-QUESTION")) else
            {"kind": "polarity_answer", **tree.semantic_profile["answer_context"]}
            if tree.get_root_node().contains(FeatureLabel("SHORT-ANSWER")) else None
        ),
        "requirement_count": sum(len(n["requirements"]) for n in nodes),
    }


def parse_request(payload: Any, on_event=None, *, _parser=None, _trace=True, _setup=None,
                  _trace_budget=None) -> dict[str, Any]:
    """Record word states and replayed action states, stopping at the first failure."""
    from dynamicsyntax import icp
    from dylan.parser.parse_stats import ParseStats
    from dylan.action.lexical_action import LexicalAction
    from dynamicsyntax._parse import _active_path_edges, _steps_from_edge
    from dylan.workbench_readings import collect_readings, operation_frame, rule_frame, RuleTraceBudget
    from dynamicsyntax.parse_trace import action_kind

    trace_operations = _trace is True
    trace_level = "operations" if trace_operations else "actions" if _trace else "words"
    trace_budget = _trace_budget or (RuleTraceBudget() if _trace == "actions" else None)
    trace_truncated = False

    if isinstance(payload, dict) and "paragraph" in payload:
        from dylan.paragraph_workbench import parse_paragraph

        validate_request(payload)
        return parse_paragraph(payload, on_event)
    sentence, grammar = validate_request(payload, sentence_limits=(2000, 160) if _parser else (500, 40))
    if payload.get("compare_jev"):
        from dylan.jev_comparison import compare
        return compare(payload, on_event, trace=_trace)
    if payload.get("lexical_mode") == "assisted":
        if "dialogue" in payload:
            raise ValueError("Open-text assistance currently accepts sentence or paragraph input.")
        from dylan.assisted_parsing import parse_assisted
        return parse_assisted(payload, on_event, parser=_parser, trace_budget=trace_budget)
    from dylan.dialogue_workbench import transcript_words, validate_dialogue

    dialogue = validate_dialogue(payload) if "dialogue" in payload else None
    uttered, metadata = transcript_words(
        dialogue or [{"speaker": "Dylan", "text": sentence, "boundary": "continue"}]
    )
    tokens = [word.word for word in uttered]
    started = time.perf_counter()
    default_top_n = 0 if grammar.startswith("2026-") and "ttr" not in grammar else 3
    parser = _parser or icp(grammar, top_n=payload.get("top_n", default_top_n), strict=payload.get("strict", False))
    # Earlier propositions remain in the DAG for reference resolution, but
    # their word indices and trace steps belong to their own sentence.
    historical_edges = {e.edge_id for e in _active_path_edges(parser)} if _parser else set()
    all_path_edges = _active_path_edges
    def current_edges(parser):
        return [e for e in all_path_edges(parser) if e.edge_id not in historical_edges]
    _active_path_edges = current_edges
    try:
        from dylan.lexical_expansion import expand

        controls = set(parser.forced_repairanda + parser.repairanda + [parser.WAIT])
        lexical = _setup(parser) if _setup else expand(
            parser,
            grammar,
            tokens,
            payload.get("lexical_mode", "off"),
            controls=controls,
            on_event=on_event,
            allow_model_fallback=payload.get("allow_model_fallback", True),
        )
        if _parser is not None:
            earlier_entries = getattr(parser, "_paragraph_lexical_entries", [])
            new_entries = lexical["entries"]
            lexical["entries"] = [
                {**entry, "reused": True} for entry in earlier_entries
                if entry["surface"] in tokens
            ] + new_entries
            parser._paragraph_lexical_entries = earlier_entries + new_entries
        if parser.semantic_profile:
            parser.semantic_profile["scope"] = payload.get("scope", "narrow")
        if _parser is not None:
            parser.forced_repair = parser.forced_restart = False
            parser.context.set_repair_processing(False)
        elif dialogue:
            parser.init_participants(list(dict.fromkeys(t["speaker"] for t in dialogue)))
        else:
            parser.init()
        parser.new_sentence()
        from dylan.decision.workbench import attach as attach_decision, report as decision_report

        attach_decision(parser, payload.get("decision_mode", "off"))
        clause_index = 0
        edge_words = {}
        active_indices = []
        previous_trees, repairs = [], []
        previous_stats = ParseStats()

        def frame(tree: Tree, label: str, word_index: int, kind: str) -> dict[str, Any]:
            return {
                "label": label,
                "word_index": word_index,
                "kind": kind,
                **(
                    {"control": "repair_marker" if parser.forced_repair else "parser_control"}
                    if kind == "word" and word_index >= 0 and tokens[word_index] in controls
                    else {}
                ),
                **(
                    {
                        "speaker": metadata[word_index]["speaker"] if word_index >= 0 else None,
                        "addressee": metadata[word_index]["addressee"] if word_index >= 0 else None,
                        "turn_index": metadata[word_index]["turn_index"] if word_index >= 0 else -1,
                        "clause_index": clause_index,
                        "active_words": list(active_indices),
                        "context_count": len(previous_trees),
                    }
                    if dialogue
                    else {}
                ),
                **tree_snapshot(tree, parser.context),
            }

        initial = frame(parser.get_best_tuple().tree, "Axiom", -1, "axiom")
        words, actions, operations = [initial], [initial], [initial]
        if on_event:
            on_event(
                {
                    "event": "start",
                    "initial": initial,
                    "tokens": tokens,
                    "sentence": sentence,
                    "grammar": grammar,
                    "trace_level": trace_level,
                    "lexical": lexical,
                    "dialogue": dialogue,
                    "token_metadata": metadata if dialogue else None,
                }
            )

        def append(channel, value):
            nonlocal trace_truncated
            if channel == "operations" and not trace_operations:
                return
            if channel == "actions" and trace_budget and not trace_budget.accept(value):
                trace_truncated = True
                return
            {"words": words, "actions": actions, "operations": operations}[channel].append(value)
            if on_event:
                on_event({"event": "frame", "channel": channel, "frame": value})

        def append_operation(effect, rule, index, rule_index):
            append("operations", {**operation_frame(effect, rule, index, rule_index, frame),
                                  "rule_kind": actions[rule_index].get("rule_kind", "action")})

        def cap_failure(index):
            name = parser.last_cap_hit
            assert name is not None
            limit = getattr(parser, name)
            label = {
                "max_lexical_adjustment_pairs": "lexical expansion",
                "max_nonoptional_adjust_passes": "mandatory rule application",
                "max_completion_steps": "completion search",
            }[name]
            return {
                "kind": "search_limit",
                "cap": name,
                "limit": limit,
                "token": tokens[index],
                "index": index,
                "message": f"Parsing reached the {label} limit ({limit}). The result is inconclusive.",
            }

        last_completion_actions = []

        def finish_tree(index):
            nonlocal last_completion_actions
            last = parser.get_best_tuple().tree.clone()
            completion_actions, completed = parser.complete_tree(last)
            last_completion_actions = completion_actions
            if parser.last_cap_hit is not None:
                return last
            if completion_actions:
                replay = last
                for action in completion_actions if _trace else []:
                    before = replay.clone()
                    with capture_effects() if trace_operations else contextlib.nullcontext([]) as effects:
                        replay = parser.apply_actions(replay, [action])
                    if replay is None:
                        break
                    append("actions", rule_frame(before, replay, action.name, action_kind(action), index, frame))
                    for effect in effects:
                        append_operation(effect, action.name, index, len(actions) - 1)
                final = frame(completed, "Completion", index, "completion")
                append("words", final)
                append("actions", {**final, "label": "; ".join(a.name for a in completion_actions)})
                append("operations", final)
            return completed

        seen_edges: set[int] = set()
        failure = None
        clause_start = 0
        for index, word in enumerate(uttered):
            info = metadata[index]
            answer_boundary = (
                dialogue and index and word.word in {"yes", "no"}
                and not parser.forced_repair and not parser.get_state().repair_processing_enabled()
                and parser.get_best_tuple().tree.get_root_node().contains(FeatureLabel("POLAR-QUESTION"))
            )
            explicit_boundary = dialogue and index and info["turn_start"] and info["boundary"] == "new_tree"
            if explicit_boundary or answer_boundary:
                completed_previous = finish_tree(index - 1)
                if parser.last_cap_hit is not None:
                    failure = cap_failure(index - 1)
                    break
                if answer_boundary and not explicit_boundary and (
                    not completed_previous.is_complete() or semantic_type_errors(completed_previous)
                ):
                    failure = {"kind": "missing_context", "token": word.word, "index": index,
                               "message": "Yes/No cannot answer this unfinished question; its DS requirements are still open."}
                    break
                previous_trees.append(
                    frame(completed_previous, f"Tree {clause_index + 1}", index - 1, "context")
                )
                previous_stats.add(parser.stats)
                # The new axiom's source is the actual completed preceding tree.
                # Contextual answer actions can then inspect the selected DAG path.
                parser.get_best_tuple().tree = completed_previous
                parser.new_sentence()
                parser.forced_repair = parser.forced_restart = False
                parser.context.set_repair_processing(False)
                clause_index += 1
                clause_start = index
                active_indices = []
                seen_edges.update(e.edge_id for e in _active_path_edges(parser))
                axiom = frame(parser.get_best_tuple().tree, "Answer tree" if answer_boundary else "New tree", index, "axiom")
                for channel in ("words", "actions", "operations"):
                    append(channel, axiom)
            before_path = _active_path_edges(parser)
            before_entries = {}
            if not dialogue and getattr(parser, "lexical_selector", None) is not None:
                from dylan.lexical_revision import expanded_path, entry
                before_entries = {i: entry(a) for i, _, a in expanded_path(parser)}
            pending_repair = parser.forced_repair or parser.get_state().repair_processing_enabled()
            parsed = parser.parse_word(word)
            if parser.last_cap_hit is not None:
                failure = cap_failure(index)
                break
            if parsed is None:
                known = bool(parser.lexicon.lookup(word.word))
                failure = {
                    "token": word.word,
                    "index": index,
                    "message": (
                        f"“{word.word}” is not in this grammar’s lexicon."
                        if not known
                        else f"The grammar could not continue at “{word.word}”."
                    ),
                }
                if known and parser.context.last_reference_failure:
                    failure.update(parser.context.last_reference_failure)
                elif dialogue and pending_repair and known:
                    has_context = bool(active_indices)
                    failure["kind"] = "repair_unavailable" if has_context else "missing_context"
                    failure["message"] = (
                        "No eligible local repair accepts this replacement. The previous tree is preserved."
                        if has_context
                        else "There is no earlier contribution in this tree to repair. Supply the preceding context first."
                    )
                elif dialogue and info["turn_start"] and known and words[-1]["complete"]:
                    failure["kind"] = "context_boundary"
                    failure["message"] = (
                        "The current tree is complete. Choose ‘New tree’ for a new proposition, or use an explicit repair marker for a correction."
                    )
                break
            failed_tuple = parser.get_best_tuple()
            while semantic_type_errors(parser.get_best_tuple().tree):
                # A type clash eliminates this analysis, not its unseen lexical
                # alternatives. Exhaust ordinary parser search before reporting it.
                if not parser.parse_goal(None):
                    parser.get_state().set_current_tuple(failed_tuple)
                    break
            if parser.last_cap_hit is not None:
                failure = cap_failure(index)
                break
            lexical_revision = None
            if not dialogue and getattr(parser, "lexical_selector", None) is not None:
                lexical_revision = parser.lexical_selector.reconsider(parser, uttered[:index + 1])
            actual = parser.get_best_tuple().tree.clone()
            after_path = _active_path_edges(parser)
            lexical_changes = []
            if before_entries:
                for i, _, action in expanded_path(parser):
                    after_entry = entry(action)
                    if i in before_entries and before_entries[i] != after_entry:
                        change = {"target_index": i, "after_index": index,
                                  "before": before_entries[i], "after": after_entry,
                                  "observed_prefix": tokens[:index + 1],
                                  "reason": "Jev preference validated by DS" if lexical_revision and lexical_revision["status"] == "revised" else "DS continuation"}
                        lexical_changes.append(change)
                        parser.lexical_selector.report["path_updates"].append(change)
            for edge in after_path:
                if edge.word is not None and edge.edge_id not in edge_words:
                    match = next(
                        (
                            j
                            for j in range(index, -1, -1)
                            if uttered[j].word == edge.word.word
                            and uttered[j].speaker == edge.word.speaker
                        ),
                        index,
                    )
                    edge_words[edge.edge_id] = match
            repair = None
            common = 0
            while (
                common < min(len(before_path), len(after_path))
                and before_path[common].edge_id == after_path[common].edge_id
            ):
                common += 1
            if common < len(before_path):
                # Replaying an earlier alternative must visibly return to its
                # source tree, including when this is search rather than repair.
                seen_edges.intersection_update(e.edge_id for e in after_path[:common])
                if not (dialogue and pending_repair):
                    rollback_tuple = (after_path[common].src if common < len(after_path)
                                      else parser.get_best_tuple())
                    rollback = rollback_tuple.tree
                    transition = {
                        **frame(rollback, "Backtrack: revise the earlier analysis", index, "backtrack"),
                        "pointer_before": words[-1]["pointer"],
                        "backtrack": {"rollback_tuple": rollback_tuple.tuple_id},
                        "lexical_changes": lexical_changes,
                        **({"lexical_revision": lexical_revision}
                           if lexical_revision and lexical_revision["status"] == "revised" else {}),
                    }
                    for channel in ("words", "actions", "operations"):
                        append(channel, transition)
            if dialogue and pending_repair:
                replaced = [
                    edge_words[e.edge_id] for e in before_path[common:] if e.edge_id in edge_words
                ]
                if replaced:
                    rollback = after_path[common].src.tree
                    active_indices = [
                        edge_words[e.edge_id]
                        for e in after_path[:common]
                        if e.edge_id in edge_words and edge_words[e.edge_id] >= clause_start
                    ]
                    repair = {
                        "replaced": replaced,
                        "replacement": index,
                        "speaker": word.speaker,
                        "from_pointer": words[-1]["pointer"],
                        "to_pointer": str(rollback.pointer),
                        "rollback_tuple": after_path[common].src.tuple_id,
                        "clause_index": clause_index,
                    }
                    repairs.append(repair)
                    transition = {
                        **frame(rollback, "Repair: return to the earlier tree", index, "repair"),
                        "repair": repair,
                        "pointer_before": words[-1]["pointer"],
                    }
                    for channel in ("words", "actions", "operations"):
                        append(channel, transition)
            # Repaired-away tokens remain in the transcript, not the active path.
            active_indices = [
                edge_words[e.edge_id]
                for e in after_path
                if e.edge_id in edge_words and edge_words[e.edge_id] >= clause_start
            ]
            append("words", frame(actual, word.word, index, "word"))
            for edge in after_path if _trace else []:
                if edge.edge_id in seen_edges:
                    continue
                seen_edges.add(edge.edge_id)
                for step in _steps_from_edge(parser, edge, operations=trace_operations):
                    append("actions", rule_frame(step.before_tree, step.after_tree, step.action_name, step.action_kind, index, frame))
                    if step.operations:
                        for effect in step.operations:
                            append_operation(effect, step.action_name, index, len(actions) - 1)
                    elif trace_operations:
                        append(
                            "operations",
                            {
                                **frame(step.after_tree, step.action_name, index, "grouped"),
                                "rule": step.action_name,
                                "trace_note": "This transition could not be replayed as individual effects.",
                            },
                        )
            # The recorded word boundary is authoritative if replay grouped or
            # approximated a transition; never present a replay as a live debugger.
            append("actions", frame(actual, f"After “{word.word}”", index, "word"))
            append("operations", frame(actual, f"After “{word.word}”", index, "word"))
            if words[-1]["type_errors"]:
                failure = {
                    "kind": "semantic_type_mismatch",
                    "token": word.word,
                    "index": index,
                    "message": words[-1]["type_errors"][0]["message"],
                }
                break
        if failure is None:
            completed = finish_tree(len(tokens) - 1)
            if parser.last_cap_hit is not None:
                failure = cap_failure(len(tokens) - 1)
        completion_search = None
        if (failure is None and not words[-1]["complete"] and not dialogue
                and not any(token in controls for token in tokens)):
            from dylan.workbench_readings import seek_complete_primary, replay_reading
            selected, completion_search = seek_complete_primary(
                parser, previous_edges=historical_edges, tokens=tokens,
            )
            if selected is not None:
                completed, last_completion_actions, edges = selected
                replay = replay_reading(parser, edges, last_completion_actions, completed, tokens,
                                        include_operations=trace_operations, include_actions=bool(_trace))
                rollback = {**replay["words"][0], "kind": "backtrack",
                            "word_index": len(tokens) - 1,
                            "label": "End of input: try another DS derivation",
                            "pointer_before": words[-1]["pointer"]}
                for channel in ("words", "actions", "operations"):
                    append(channel, rollback)
                    for step in replay[channel][1:]:
                        append(channel, step)
            if parser.last_cap_hit is not None:
                failure = cap_failure(len(tokens) - 1)
        final = words[-1]
        if trace_truncated:
            gap = {**final, "kind": "trace_gap",
                   "label": "Rule trace limit reached · final recorded tree"}
            actions.append(gap)
            if on_event:
                on_event({"event": "frame", "channel": "actions", "frame": gap})
        if failure is None and final["complete"] and (final["semantic_error"] or final["type_errors"]):
            failure = {"kind": "semantic_type_mismatch", "index": len(tokens) - 1,
                       "token": tokens[-1] if tokens else "",
                       "message": final["semantic_error"] or final["type_errors"][0]["message"]}
        coq = None
        if failure is None and final["complete"] and final["backend"] == "mltt":
            coq = completed.get_maximal_semantics(parser.context).to_coq()
        from dylan.greek_workbench import assessment

        pending_repair = parser.forced_repair
        complete = (
            failure is None
            and not pending_repair
            and final["complete"]
            and all(t["complete"] for t in previous_trees)
        )
        diagnostics = assessment(
            grammar, tokens, parser.lexicon, failure, complete, controls=controls
        )
        diagnostics["cap_hit"] = parser.last_cap_hit
        previous_stats.add(parser.stats)
        stats = previous_stats.to_dict()
        diagnostics["stats"] = stats
        expanded = {entry["surface"]: entry["source"] for entry in lexical["entries"]}
        for item in diagnostics["lexical_coverage"]:
            if item["token"] in expanded:
                item["source"] = expanded[item["token"]]
        if getattr(parser, "lexical_selector", None) is not None:
            parser.lexical_selector.finish(parser)
        if _setup:
            from dylan.jev_comparison import selected_entries
            lexical["used"] = selected_entries(parser, _active_path_edges(parser))
        from dylan.construction_assistance import used_constructions
        result = {
            "sentence": sentence,
            "grammar": grammar,
            "tokens": tokens,
            "ok": failure is None,
            "complete": complete,
            "failure": failure,
            "cap_hit": parser.last_cap_hit,
            "stats": stats,
            "templates": sorted({
                action.get_lexical_action_type()
                for edge in _active_path_edges(parser)
                for action in edge.get_actions()
                if isinstance(action, LexicalAction) and action.get_lexical_action_type()
            }) if complete else [],
            "derivation": {
                "actions": [a.name for edge in _active_path_edges(parser) for a in edge.get_actions()],
                "completion_actions": [a.name for a in last_completion_actions],
            } if complete else None,
            "diagnostics": diagnostics,
            "lexical": lexical,
            "clause_constructions": used_constructions(_active_path_edges(parser)),
            "decision": decision_report(parser, payload.get("decision_mode", "off")),
            "words": words,
            "actions": actions,
            "operations": operations if trace_operations else [],
            "dialogue": dialogue,
            "token_metadata": metadata if dialogue else None,
            "repairs": repairs,
            "context_trees": previous_trees,
            "pending_repair": pending_repair,
            "completion_search": completion_search,
            "backend": final["backend"],
            "scope": payload.get("scope", "narrow"),
            "coq": coq,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "trace_note": "Rules and individual effects replay the selected derivation through the engine. Word states are recorded directly.",
        }
        result["readings"] = []
        result["reading_search"] = {
            "requested": payload.get("n_best", 1), "returned": 0,
            "exhausted": False, "stop_reason": "dialogue" if dialogue else "no_complete_primary",
        }
        if complete and not dialogue:
            result["readings"], result["reading_search"] = collect_readings(
                parser, completed, last_completion_actions, tokens,
                limit=payload.get("n_best", 1), include_traces=payload.get("reading_traces", False),
                previous_edges=historical_edges,
            )
        if _parser is not None and complete:
            # Store the completed tree, including final substitutions, as the
            # context endpoint used by the next sentence.
            parser.get_best_tuple().tree = completed
        result["trace_level"] = trace_level
        result["trace_truncated"] = trace_truncated
        if trace_truncated:
            result["trace_note"] += " The rule snapshot budget was reached: playback explicitly jumps to the final recorded tree. Parsing and coverage are unaffected."
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        return result
    finally:
        if _parser is None:
            parser.close()


def main() -> None:
    """Worker protocol: one request on stdin, one response on stdout."""
    try:
        payload = json.load(sys.stdin)
        output = sys.stdout

        def emit(event):
            output.write(json.dumps(event, ensure_ascii=False) + "\n")
            output.flush()

        with contextlib.redirect_stdout(io.StringIO()):
            result = parse_request(payload, emit if payload.get("stream") else None)
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
    if isinstance(locals().get("payload"), dict) and payload.get("stream"):
        emit({"event": "result", "result": result})
    else:
        json.dump(result, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
