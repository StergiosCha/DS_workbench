"""Isolated worker API for the experimental hybrid syntax lab."""

import json
import sys

from dylan.hybrid import ccg, minimalist
from dylan.hybrid.assistance import configuration as assistance_configuration, draft, rank
from dylan.hybrid.correspondence import project
from dylan.hybrid.features import UnificationError
from dylan.hybrid.polydefinites import agreement_trace
from dylan.hybrid.traces import DSAdapter
from dylan.workbench_paths import data_path

GRAMMARS = {"2026-english-classical", "2026-smg-classical"}
EXAMPLES = [
    {"label": "An object still pending", "text": "John likes", "grammar": "2026-english-classical", "framework": "hybrid", "complete": False},
    {"label": "DS and grammatical functions", "text": "John likes Mary", "grammar": "2026-english-classical", "framework": "hybrid", "complete": True},
    {"label": "A fragment in left context", "text": "likes a", "left_context": "John", "grammar": "2026-english-classical", "framework": "ds", "complete": False},
    {"label": "Greek postnominal polydefinite", "text": "ο άνθρωπος ο μεγάλος περπατάει", "grammar": "2026-smg-classical", "framework": "hybrid", "complete": True},
    {"label": "Greek repeated definiteness", "text": "ο μεγάλος ο κόκκινος ο άνθρωπος περπατάει", "grammar": "2026-smg-classical", "framework": "hybrid", "complete": True},
    {"label": "Agreement conflict", "text": "ο άνθρωπος η μεγάλη περπατάει", "grammar": "2026-smg-classical", "framework": "hybrid", "complete": True},
    {"label": "CCG unfinished category", "text": "will make his", "grammar": "2026-english-classical", "framework": "ccg", "complete": False},
    {"label": "Feature-licensed movement", "text": "who did john like", "grammar": "2026-english-classical", "framework": "minimalist", "complete": True},
    {"label": "Compare the declared fragments", "text": "John likes Mary", "grammar": "2026-english-classical", "framework": "compare", "complete": True},
]


def configuration():
    return {"examples": EXAMPLES, "assistance": assistance_configuration(),
            "modules": [
                {"name": "DS", "capability": "incremental native interpretation and trace replay"},
                {"name": "Feature constraints", "capability": "typed graphs, sharing, agreement, monotonic construction inheritance"},
                {"name": "LFG", "capability": "bounded argument projection, completeness/coherence, functional uncertainty"},
                {"name": "Minimalist grammar", "capability": "bounded feature-driven Merge/Move derivations"},
                {"name": "CCG", "capability": "bounded application, composition and optional type raising"}],
            "scope": "Executable research fragments and partial correspondences; not complete implementations of these frameworks"}


def evidence():
    path = data_path("hybrid/summary.json")
    return json.loads(path.read_text()) if path.exists() else {
        "status": "not_built", "message": "Build the research report with python -m dylan.hybrid.report."}


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    allowed = {"action", "text", "grammar", "framework", "left_context", "complete", "prefix", "word", "live"}
    if set(payload) - allowed:
        raise ValueError("Unknown experiment option")
    for field in ["text", "left_context", "prefix", "word"]:
        if field in payload and (not isinstance(payload[field], str) or len(payload[field]) > 1000):
            raise ValueError(f"Invalid {field}")
    for flag in ["complete", "live"]:
        if flag in payload and type(payload[flag]) is not bool:
            raise ValueError(f"{flag} must be a boolean")
    action = payload.get("action", "analyse")
    if not isinstance(action, str) or action not in {"analyse", "rank", "draft"}:
        raise ValueError("Unknown experiment action")
    if action == "analyse":
        if not payload.get("text", "").strip() or len((payload.get("left_context", "") + " " + payload["text"]).split()) > 40:
            raise ValueError("Provide 1–40 words including left context")
        grammar = payload.get("grammar", "2026-english-classical")
        framework = payload.get("framework", "hybrid")
        if not isinstance(grammar, str) or grammar not in GRAMMARS:
            raise ValueError("Unknown experimental grammar")
        if not isinstance(framework, str) or framework not in {"hybrid", "ds", "ccg", "minimalist", "compare"}:
            raise ValueError("Unknown experimental configuration")
    else:
        if not payload.get("word", "").isalpha() or len(payload["word"]) > 40 or len(payload.get("prefix", "").split()) > 40:
            raise ValueError("Provide one alphabetic word and at most 40 words of context")
    return payload


def analyse(payload):
    validate(payload)
    action = payload.get("action", "analyse")
    if action == "rank":
        return rank(payload.get("prefix", ""), payload["word"], mode="jev" if payload.get("live") else "stub")
    if action == "draft":
        if not payload.get("live"):
            raise ValueError("Explicit live drafting must be selected")
        return draft(payload.get("prefix", ""), payload["word"])
    framework, text = payload.get("framework", "hybrid"), payload["text"]
    result = {"text": text, "framework": framework, "modules": {}}
    if framework in {"ds", "hybrid", "compare"}:
        grammar = payload.get("grammar", "2026-english-classical")
        extensions = ("polydefinites",) if framework == "hybrid" and grammar == "2026-smg-classical" else ()
        adapter = DSAdapter(grammar, extensions=extensions)
        try:
            trace = adapter.probe(text, left_context=payload.get("left_context", ""), complete=payload.get("complete", False),
                                  project_functions=framework in {"hybrid", "compare"})
            result["modules"]["ds"] = trace
            if framework in {"hybrid", "compare"}:
                result["modules"]["lfg"] = project(adapter.parser, closed=payload.get("complete", False))
            if extensions:
                try:
                    result["modules"]["features"] = {"status": "compatible", "trace": agreement_trace(text.split())}
                except UnificationError as exc:
                    result["modules"]["features"] = {"status": "conflict", "message": str(exc)}
                result["assumptions"] = [
                    "One contextually identifiable referent is assumed.",
                    "This intersective subject fragment does not model the full pragmatic distribution of polydefinites."]
        finally:
            adapter.close()
    for name, module, max_words in [("ccg", ccg, 12), ("minimalist", minimalist, 8)]:
        if framework in {name, "compare"}:
            result["modules"][name] = module.parse(text) if len(text.split()) <= max_words else {
                "status": "unsupported_length", "limit": max_words, "analyses": []}
    return result


def main():
    from dylan.workbench_environment import load_environment
    from dylan.lexical_provider import ProposalUnavailable
    load_environment()
    try:
        payload = json.load(sys.stdin)
        result = analyse(payload)
    except (ValueError, ProposalUnavailable) as exc:
        result = {"error": str(exc)}
    json.dump(result, sys.stdout, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
