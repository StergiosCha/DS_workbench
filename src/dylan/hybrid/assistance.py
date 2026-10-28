"""Optional typed sense ranking and validated LLM proposals for research inspection."""

import argparse
import json
from pathlib import Path

from dylan import lexical_provider
from dylan.decision.client import DecisionClient
from dylan.decision.provider import settings
from dylan.lexical_selection import candidate_groups, lexical_state
from dylan.decision.questions.lexical_v1 import questions
from dylan.lexical_expansion import schema, validate_entries, allowed_domains, TEMPLATES
from dylan.nlp.types import utterance_from_text
from dylan.hybrid.traces import DSAdapter, action_record


def configuration():
    decision = settings()
    return {"jev": {"configured": bool(decision["key"]), "provider": decision["provider"], "model": decision["model"]},
            "llm": lexical_provider.configuration(),
            "policy": "research judgments only; no automatic grammar-rule installation"}


def rank(prefix, word, *, mode="stub", client=None):
    if not word.isalpha() or len(word) > 40 or len(prefix.split()) > 40:
        raise ValueError("Provide one word and a prefix of at most 40 words")
    adapter = DSAdapter(vocabulary="dictionary")
    try:
        adapter.prepare(prefix + " " + word)
        probe = adapter.probe(prefix) if prefix.strip() else None
        actions = adapter.parser.lexicon.lookup(word.lower())
        eligible = [a for a in actions if a.metadata.get("source") in {"dictionary", "model"}]
        if not eligible:
            return {"status": "no_dictionary_candidates", "word": word, "prefix": prefix}
        state, _ = lexical_state(adapter.parser, utterance_from_text("Dylan", word).words[0], eligible)
        # Supplied text remains observed context even when the bounded grammar
        # cannot parse it; distinguish it from the active DS parse path.
        state["observed_prefix"] = prefix
        state["prefix_status"] = probe["status"] if probe else "empty"
        candidates, _ = candidate_groups(eligible)
        qs = questions(candidates)
        if not qs:
            return {"status": "single_analysis", "candidates": candidates}
        client = client or DecisionClient(mode, log_path="build/hybrid/assistance/decisions.jsonl")
        record = client.decide(state, qs, idea="hybrid-sense-evaluation", calibration=mode == "jev",
                               deterministic_order=[c["id"] for c in candidates])
        return {"status": "judged" if record and not record["stub"] else "unavailable" if mode == "jev" else "stub",
                "record": record, "candidates": candidates,
                "interpretation": "preference among supplied lexical programs; native DS still checks application"}
    finally:
        adapter.close()


def draft(prefix, word, *, proposal=None):
    if not word.isalpha() or len(word) > 40 or len(prefix.split()) > 40:
        raise ValueError("Provide one word and a prefix of at most 40 words")
    adapter = DSAdapter()
    try:
        parser = adapter.parser
        if word.lower() in parser.lexicon:
            return {"status": "already_in_grammar", "programs": [action_record(a) for a in parser.lexicon.lookup(word.lower())]}
        context = {"tokens": (prefix + " " + word).split(), "unknown": [word.lower()],
                   "templates": TEMPLATES, "allowed_domains": allowed_domains(parser.semantic_profile),
                   "theory": parser.semantic_profile}
        provider = {"provider": "supplied_fixture", "model": "none"}
        if proposal is None:
            proposal, provider = lexical_provider.propose(context, schema(parser.semantic_profile))
        compiled, theory = validate_entries(proposal, [word.lower()], parser.lexicon, parser.semantic_profile)
        # Return reviewable programs and declarations; proposal compilation is
        # not evidence that the proposed lexical analysis is linguistically right.
        return {"status": "compiled_for_review", "proposal": proposal, "provider": provider,
                "compiled": [{"entry": item, "program": action_record(action)} for item, action in compiled],
                "theory": theory, "installed": False}
    finally:
        adapter.close()


def main():
    from dylan.workbench_environment import load_environment
    load_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["rank", "draft", "configuration"])
    parser.add_argument("--prefix", default="John walked to the")
    parser.add_argument("--word", default="bank")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/assistance/result.json"))
    args = parser.parse_args()
    if args.model:
        import os
        os.environ["DS_LEXICAL_MODEL"] = args.model
    if args.action == "configuration":
        print(json.dumps(configuration(), indent=2))
        return
    if args.action == "draft" and not args.live:
        raise SystemExit("Drafting requires --live; use supplied proposals through the Python API for offline checks")
    try:
        result = rank(args.prefix, args.word, mode="jev" if args.live else "stub") if args.action == "rank" else draft(args.prefix, args.word)
    except lexical_provider.ProposalUnavailable as exc:
        result = {"status": "provider_unavailable", "message": str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps({"status": result["status"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
