"""Observed-prefix DS traces and bounded fragment probes.

Input failures are coverage outcomes, never human grammaticality judgments.
The parser is reused only within a probe; priming memory is an external object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

from dylan.nlp.types import utterance_from_text
from dylan.parser.interactive_context_parser import InteractiveContextParser
from dynamicsyntax._parse import _active_path_edges, _complete_native_parse, _steps_from_edge


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    default=str).encode()).hexdigest()


def snapshot(tree):
    nodes = [{"address": str(address), "labels": sorted(str(label) for label in node.labels)}
             for address, node in tree.items()]
    nodes.sort(key=lambda n: n["address"])
    return {"pointer": str(tree.pointer), "nodes": nodes,
            "pending": [{"address": n["address"], "requirement": label}
                        for n in nodes for label in n["labels"] if label.startswith("?")],
            "complete": tree.is_complete()}


def action_record(action):
    source = getattr(action, "_source_lines", None)
    program = "\n".join(source) if source else str(action.get_effect())
    result = {"name": action.get_name(), "class": type(action).__name__,
              "template": getattr(action, "action_type", None),
              "parameters": list(getattr(action, "parameters", ())),
              "program": program, "program_sha256": hashlib.sha256(program.encode()).hexdigest(),
              "provenance": getattr(action, "metadata", {}),
              "backtracks_on_success": action.backtracks_on_success()}
    result["id"] = digest(result)
    return result


def fingerprint(parser):
    root = getattr(parser.lexicon, "_resource_dir", None)
    files = {}
    if root:
        for path in sorted(Path(root).rglob("*.txt")):
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest(files)


class DSAdapter:
    """Bounded first-success search with all retained lexical entries.

    Candidate counts describe recorded search, not exhaustive ambiguity counts.
    """

    def __init__(self, grammar="2026-english-classical", *, cap=1000, vocabulary="original", extensions=()):
        if vocabulary not in {"original", "dictionary"}:
            raise ValueError("Unknown vocabulary mode")
        self.grammar, self.cap, self.vocabulary = grammar, cap, vocabulary
        self.extensions = tuple(extensions)
        if set(self.extensions) - {"polydefinites"}:
            raise ValueError("Unknown grammar extension")
        self.parser = InteractiveContextParser(
            grammar, top_n=0, log_level="off", repairing=False,
            max_lexical_adjustment_pairs=cap, max_nonoptional_adjust_passes=cap,
            max_completion_steps=cap)
        self.fingerprint = fingerprint(self.parser)
        if "polydefinites" in self.extensions:
            if grammar != "2026-smg-classical":
                raise ValueError("The polydefinite extension requires Classical SMG")
            from dylan.hybrid import polydefinites
            polydefinites.install(self.parser)
            self.fingerprint = digest([self.fingerprint, Path(polydefinites.__file__).read_text()])

    def prepare(self, text):
        if self.vocabulary == "dictionary":
            from dylan.lexical_expansion import expand
            words = [w.word for w in utterance_from_text("Dylan", text).words]
            return expand(self.parser, self.grammar, words, "dictionary", allow_model_fallback=False)
        return {"mode": "original"}

    def close(self):
        self.parser.close()

    def probe(self, text, *, left_context="", complete=False, speaker="Dylan", trace=True, project_functions=False):
        if len((left_context + " " + text).split()) > 80:
            raise ValueError("Probe supports at most 80 tokens including context")
        parser = self.parser
        vocabulary = self.prepare(left_context + " " + text)
        parser.init()
        parser.new_sentence()
        observed, frames = [], []
        context_words = utterance_from_text(speaker, left_context).words if left_context.strip() else []
        target_words = utterance_from_text(speaker, text).words if text.strip() else []
        status, failure = "recognized_fragment", None
        started = time.perf_counter()
        for index, word in enumerate([*context_words, *target_words]):
            is_context = index < len(context_words)
            before = snapshot(parser.get_best_tuple().tree) if trace else None
            candidates = parser.lexicon.lookup(word.word)
            inventory = [action_record(a) for a in candidates] if trace else []
            known = bool(candidates)
            prior_path = [e.edge_id for e in _active_path_edges(parser)]
            ok = parser.parse_word(word) is not None
            observed.append(word.word)
            after = snapshot(parser.get_best_tuple().tree) if trace else None
            actions, replay_ok = [], True
            if trace:
                for edge in _active_path_edges(parser):
                    if edge.edge_id in prior_path:
                        continue
                    steps = _steps_from_edge(parser, edge, operations=True)
                    programs = [action_record(a) for a in edge.get_actions()]
                    exact = len(steps) == len(programs) and all(
                        step.action_name == program["name"] for step, program in zip(steps, programs))
                    replay_ok &= exact
                    actions.append({"word": edge.word.word if edge.word else None,
                                    "programs": programs, "atomic_replay": exact,
                                    "steps": [{"action": s.action_name,
                                               "before": snapshot(s.before_tree),
                                               "after": snapshot(s.after_tree)} for s in steps]})
                frames.append({"index": index, "fragment_index": index - len(context_words),
                               "context": is_context, "word": word.word, "observed": list(observed),
                               "speaker": speaker, "before": before, "after": after,
                               "lexical_candidates": inventory, "selected_actions": actions,
                               "replay_expanded": replay_ok, "accepted": ok,
                               "search": parser.stats.to_dict()})
                if project_functions:
                    from dylan.hybrid.correspondence import project
                    frames[-1]["lfg"] = project(parser, closed=False)
            if not ok or parser.last_cap_hit:
                status = "search_limit" if parser.last_cap_hit else "unsupported_lexicon" if not known else "unsupported_construction"
                failure = {"word": word.word, "index": index, "in_context": is_context,
                           "cap": parser.last_cap_hit}
                break
        if not target_words:
            status = "empty_input"
        if status == "recognized_fragment" and complete:
            _complete_native_parse(parser)
            status = "complete" if parser.get_best_tuple().tree.is_complete() else "pending_requirements"
            if parser.last_cap_hit:
                status = "search_limit"
                failure = {"cap": parser.last_cap_hit}
        state = snapshot(parser.get_best_tuple().tree)
        return {"schema": 1, "grammar": self.grammar, "grammar_sha256": self.fingerprint,
                "text": text, "left_context": left_context, "speaker": speaker,
                "task": "sentence_completion" if complete else "fragment_recognition",
                "status": status, "failure": failure, "frames": frames, "state": state,
                "search": parser.stats.to_dict(), "elapsed_seconds": time.perf_counter() - started,
                "config": {"cap": self.cap, "top_n": 0, "repairing": False, "vocabulary": self.vocabulary,
                           "extensions": self.extensions},
                "vocabulary": vocabulary,
                "ambiguity": "first successful search path; candidate inventories retained, not exhaustive parses"}


def replay(record):
    adapter = DSAdapter(record["grammar"], cap=record["config"]["cap"],
                        vocabulary=record["config"].get("vocabulary", "original"),
                        extensions=record["config"].get("extensions", ()))
    try:
        if adapter.fingerprint != record["grammar_sha256"]:
            return {"verified": False, "reason": "grammar_changed"}
        repeated = adapter.probe(record["text"], left_context=record["left_context"],
                                 complete=record["task"] == "sentence_completion",
                                 speaker=record["speaker"])
        original_states = [(f["word"], f["before"], f["after"]) for f in record["frames"]]
        repeated_states = [(f["word"], f["before"], f["after"]) for f in repeated["frames"]]
        programs_equal = ([f["lexical_candidates"] for f in record["frames"]] ==
                          [f["lexical_candidates"] for f in repeated["frames"]])
        equal = (programs_equal and original_states == repeated_states and record["status"] == repeated["status"] and
                 record["state"] == repeated["state"])
        return {"verified": equal, "reason": "identical_observed_states" if equal else "trace_mismatch"}
    finally:
        adapter.close()


@dataclass
class SequenceMemory:
    """Inspectable trial-local recency. Query precedes update to prevent self-priming."""

    decay: float = .8
    trial: int = 0
    occurrences: dict[tuple[str, ...], list[int]] = field(default_factory=dict)
    strengths: dict[tuple[str, ...], tuple[float, int]] = field(default_factory=dict)

    def __post_init__(self):
        if not 0 < self.decay <= 1:
            raise ValueError("Decay must be in (0, 1]")

    def activation(self, sequence):
        value = self.strengths.get(tuple(sequence))
        return 0. if value is None else value[0] * self.decay ** (self.trial - value[1] - 1)

    def observe(self, sequences):
        for sequence in set(tuple(s) for s in sequences):
            self.strengths[sequence] = (self.activation(sequence) * self.decay + 1, self.trial)
            self.occurrences.setdefault(sequence, []).append(self.trial)
        self.trial += 1


@dataclass
class MacroStep:
    tree: object
    context: object


@dataclass
class IncrementalMacro:
    """Runtime action macro with observed-word gating and exact trigger preservation."""

    words: tuple[str, ...]
    actions: tuple[tuple[object, ...], ...]
    position: int = 0

    def __post_init__(self):
        if len(self.words) != len(self.actions) or not self.words:
            raise ValueError("Each macro word requires an action group")

    def step(self, word, tree, context):
        if self.position >= len(self.words) or word != self.words[self.position]:
            return None
        from dylan.action.meta.element import snapshot_meta_bindings, restore_meta_bindings
        bindings = snapshot_meta_bindings()
        candidate, candidate_context = tree.clone(), deepcopy(context)
        committed = False
        try:
            for action in self.actions[self.position]:
                candidate = action.instantiate().exec(candidate, candidate_context)
                if candidate is None:
                    return None
            self.position += 1
            committed = True
            return MacroStep(candidate, candidate_context)
        finally:
            if not committed:
                restore_meta_bindings(bindings)

    @property
    def complete(self):
        return self.position == len(self.words)
