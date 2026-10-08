"""Dictionary candidates, optional lexical proposals, and prefix-only Jev preferences."""

from collections import OrderedDict
from datetime import datetime, timezone
import sqlite3

from dylan import lexical_provider
from dylan.decision.client import DecisionClient, content_hash, validate_answers
from dylan.decision.provider import settings
from dylan.decision.questions.lexical_v1 import options
from dylan.decision.questions.incremental_v1 import questions
from dylan.decision.state import entry_state
from dylan.lexical_expansion import (
    TEMPLATES, SURFACE, PROTECTED, VERSION, _cache, _install, bundled_entries, schema, validate_entries,
)

THRESHOLD = 0.50


def preferences(candidates, answers):
    """An uncertain frame must not erase a useful sense preference, or vice versa."""
    choices = options(candidates)
    selected = {}
    for name, values in choices.items():
        answer = answers.get(name, {})
        choice = answer.get("choice")
        if choice in values and answer["probabilities"][choice] >= THRESHOLD:
            selected[name] = values[choice]
    if not selected:
        return {}, {}
    weights = {}
    for candidate in candidates:
        weight = 1.0
        for name, field in (("sense", "symbol"), ("frame", "template")):
            if name in selected:
                if name == "sense":
                    choice = next(k for k, v in choices[name].items() if candidate["symbol"] in v["symbols"])
                else:
                    choice = next(k for k, v in choices[name].items() if v[field] == candidate[field])
                weight *= answers[name]["probabilities"][choice]
        weights[candidate["id"]] = weight
    return weights, selected


def configuration():
    from dylan.jev_comparison import configuration as comparison_configuration
    provider = settings()
    return {"configured": bool(provider["key"]), "provider": provider["provider"], "model": provider["model"],
            "comparison": comparison_configuration(),
            "description": "Jev revisits word senses as input arrives; DS checks frames and every proposed revision."}


def candidate_groups(actions):
    """Group finite/base programs of one analysis so they do not split its vote."""
    groups = OrderedDict()
    for action in actions:
        meta = action.metadata
        key = (meta.get("template"), meta.get("symbol"), tuple(meta.get("domains", ())))
        groups.setdefault(key, []).append(action)
    candidates, memberships = [], {}
    for i, group in enumerate(groups.values()):
        meta = group[0].metadata
        identity = f"l{i}"
        candidates.append({
            "id": identity, "lemma": meta["lemma"], "template": meta["template"],
            "symbol": meta["symbol"], "domains": meta["domains"], "morphology": meta["morphology"],
            "evidence": meta["evidence"], "source": meta["source"],
            "frame_description": TEMPLATES[meta["template"]]["description"],
            "program_hash": content_hash([a._source_lines for a in group]),
        })
        memberships.update({id(action): identity for action in group})
    return candidates, memberships


def lexical_state(parser, word, actions):
    snapshot = entry_state(parser, word, actions)
    candidates, memberships = candidate_groups(actions)
    return {"grammar": snapshot["grammar"], "prefix": snapshot["tokens_so_far"],
            "word": snapshot["next_word"], "tree": snapshot["tree"],
            "speaker": snapshot["speaker"], "candidates": candidates}, memberships


class LexicalSelector:
    def __init__(self, client=None):
        self.client = client or DecisionClient("jev", runtime=True, lexical=True)
        self.report = {"provider": self.client.provider["provider"], "model": self.client.provider["model"],
                       "decisions": [], "live_calls": 0, "used": [], "revisions": [], "path_updates": []}
        self.seen = {}
        self.suspended = False
        self.reconsidered = {}

    def order(self, parser, word, actions):
        if self.suspended or not actions or any(a.metadata.get("source") not in {"dictionary", "model"} for a in actions):
            return actions
        state, memberships = lexical_state(parser, word, actions)
        candidates = state["candidates"]
        if len(candidates) < 2:
            return actions
        if len(candidates) > 254:
            self.report["decisions"].append({"word": word.word, "status": "candidate_limit", "preferred": None})
            return actions
        qs = questions(candidates)
        if not qs:
            return actions
        weights, _ = self.decide(state, qs)
        # This changes consideration order, never the inventory of programs.
        return sorted(actions, key=lambda action: -weights.get(memberships[id(action)], 0))

    def decide(self, state, qs):
        candidates = state["candidates"]
        key = content_hash([self.client.provider["provider"], self.client.provider["model"], 6, state, qs])
        if key not in self.seen:
            cached = None
            try:
                cached = _cache("jev-lexical:" + key)
                if (isinstance(cached, dict) and cached.get("model") == self.client.provider["model"]
                        and cached.get("provider") == self.client.provider["provider"]):
                    self.client.recorded[key] = validate_answers(cached["answers"], qs)
                else:
                    cached = None
            except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
                cached = None
            try:
                record = self.client.decide(state, qs, idea=6, deterministic_order=[c["id"] for c in candidates])
            except (OSError, ValueError, TypeError):
                record = None
            answers = record["answers"] if record and not record["stub"] else None
            weights, selected = preferences(candidates, answers) if answers else ({}, {})
            self.seen[key] = (weights, selected)
            self.report["decisions"].append({
                "word": state["word"], "prefix": state.get("observed_prefix", state["prefix"]), "preferred": selected,
                "phase": "reconsider" if "observed_prefix" in state else "lookup",
                "target_index": state.get("target_index", len(state["prefix"])),
                "status": "preferred" if selected else "uncertain" if answers else "unavailable",
                "answers": answers or {}, "candidates": candidates,
                "questions": qs,
                "cached": bool(cached), "gate": record.get("gate") if record else None,
                "latency_ms": record.get("latency_ms", 0) if record else 0,
                "error": record.get("error") if record else None,
                "cost_usd": record.get("cost_usd") if record and not cached else None,
            })
            self.report["live_calls"] = self.client.live_calls
            if answers and not cached:
                try:
                    _cache("jev-lexical:" + key, {"model": record["model"], "provider": record["provider"],
                                                "answers": record["answers"]})
                except (OSError, sqlite3.Error, ValueError):
                    pass
        return self.seen[key]

    def reconsider(self, parser, observed):
        """Revisit at most one earlier word per content-word boundary, never unseen input."""
        from dylan.lexical_revision import expanded_path, entry, try_preference
        from dylan.decision.state import nodes_only_snapshot
        from dynamicsyntax._parse import _active_path_edges

        # Function words can force ordinary DS backtracking; they do not by
        # themselves spend another model request on an earlier lexical sense.
        if self.suspended or not observed or observed[-1].word in PROTECTED or not SURFACE.fullmatch(observed[-1].word):
            return None
        if [e.word.word for e in _active_path_edges(parser) if e.word is not None] != [w.word for w in observed]:
            # Repair/control transcripts need a separate mapping from input to
            # active words; do not apply sentence indices to a revised transcript.
            return None
        path = expanded_path(parser)
        for index, edge, action in path:
            if index >= len(observed) - 1 or self.reconsidered.get(index, 0) >= 3:
                continue
            actions = parser.lexicon.lookup(action.word)
            if any(a.metadata.get("source") not in {"dictionary", "model"} for a in actions):
                continue
            candidates, _ = candidate_groups(actions)
            qs = questions(candidates, reconsider=True)
            if not qs or len(candidates) > 254:
                continue
            self.reconsidered[index] = self.reconsidered.get(index, 0) + 1
            state, _ = lexical_state(parser, edge.word, actions)
            state.update(prefix=[w.word for w in observed[:index]],
                         observed_prefix=[w.word for w in observed], target_index=index,
                         tree=nodes_only_snapshot(parser.get_best_tuple().tree))
            _, selected = self.decide(state, qs)
            preferred = selected.get("sense")
            event = {"word": action.word, "target_index": index, "after_index": len(observed) - 1,
                     "observed_prefix": state["observed_prefix"], "before": entry(action),
                     "after": entry(action), "preferred": preferred, "status": "uncertain"}
            if preferred:
                if action.metadata["symbol"] in preferred["symbols"]:
                    event["status"] = "retained"
                else:
                    self.suspended = True
                    try:
                        event["status"] = try_preference(parser, edge, preferred["symbols"], observed[index:])
                    finally:
                        self.suspended = False
                    if event["status"] == "revised":
                        event["after"] = next(entry(a) for i, _, a in expanded_path(parser) if i == index)
            self.report["revisions"].append(event)
            return event
        return None

    def finish(self, parser):
        from dynamicsyntax._parse import _active_path_edges
        from dylan.action.lexical_action import LexicalAction

        self.report["used"] = [
            {"word": action.word, "template": action.metadata["template"], "symbol": action.metadata["symbol"]}
            for edge in _active_path_edges(parser) for action in edge.actions
            if isinstance(action, LexicalAction) and action.metadata.get("source") in {"dictionary", "model"}
        ]


def prepare(parser, grammar, tokens, unknown, report, controls, *, allow_model_fallback=True):
    """Validate the inventory before Jev sees it; model fallback uses only left context."""
    from dylan.lexical_dictionary import candidates, configuration as dictionary_configuration
    from dylan.decision.gates import grammar_hash

    report.update(status="jev", dictionary=dictionary_configuration(), morphology={},
                  allow_model_fallback=allow_model_fallback, model_requests=0)
    selector = LexicalSelector()
    parser.lexical_selector = selector
    report["selection"] = selector.report
    if not report["dictionary"]["installed"]:
        report["notices"].append("The optional WordNet dictionary is not installed; using available lexical fallbacks.")
    bundled, fallback_calls = bundled_entries(), 0
    for word in unknown:
        if word in PROTECTED or not SURFACE.fullmatch(word):
            continue
        try:
            proposals, analyses = candidates(word)
            report["morphology"][word] = analyses
            provenance = {"source": "dictionary", "dictionary": report["dictionary"]["source"]}
            if not proposals and word in bundled:
                proposals, provenance = bundled[word], {"source": "bundled", "version": VERSION}
            if not proposals and not analyses and allow_model_fallback and lexical_provider.configuration()["configured"]:
                config = lexical_provider.settings()
                context = {"tokens": tokens[:tokens.index(word) + 1], "unknown": [word], "templates": TEMPLATES,
                           "allowed_domains": sorted({"object", *parser.semantic_profile["subtyping"]}),
                           "theory": parser.semantic_profile}
                key = "jev-fallback:" + content_hash([VERSION, grammar_hash(grammar), context, config["url"], config["model"]])
                try:
                    cached = _cache(key)
                except (OSError, sqlite3.Error, ValueError):
                    cached = None
                if cached:
                    proposals, provenance = cached["entries"], cached["provenance"]
                elif fallback_calls < 1:
                    fallback_calls += 1
                    report["model_requests"] += 1
                    raw, provider = lexical_provider.propose(context, schema(parser.semantic_profile))
                    # Validate the raw object before caching or selecting any entry.
                    validate_entries(raw, [word], parser.lexicon, parser.semantic_profile, controls)
                    proposals = raw["entries"]
                    provenance = {"source": "model", **provider, "created_at": datetime.now(timezone.utc).isoformat()}
                    try:
                        _cache(key, {"entries": proposals, "provenance": provenance})
                    except (OSError, sqlite3.Error):
                        pass
                else:
                    report["notices"].append(f"No dictionary candidate for {word}; the one-request model fallback budget is used.")
                provenance = {**provenance, "cached": bool(cached)}
            compiled, theory = validate_entries(
                {"entries": proposals}, [word], parser.lexicon, parser.semantic_profile, controls,
                max_entries=len(proposals), max_analyses=len(proposals),
            )
            report["entries"] += _install(parser, compiled, theory, provenance)
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError, lexical_provider.ProposalUnavailable):
            report["notices"].append(f"Lexical candidates for {word} were unavailable or failed validation.")
    report["remaining"] = [word for word in unknown if word not in parser.lexicon]
    if report["remaining"] and not allow_model_fallback:
        report["notices"].append("Analysis LLM is off; missing-word model fallback and cached model proposals were not used.")
    return report
