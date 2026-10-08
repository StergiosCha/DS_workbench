"""Compare DS with and without Jev using one frozen lexical inventory.

The baseline is executed, not inferred from the first dictionary candidate.
Only trusted server-built lexical programs are copied between the two parsers.
"""
from copy import deepcopy
import time

from dylan.action.meta.element import reset_all_meta_bindings, snapshot_meta_bindings, restore_meta_bindings
from dylan.decision.client import content_hash

GRAMMARS = {"2026-english-classical", "2026-english-mltt"}
EXAMPLES = [
    {"sentence": "John lends a book to Mary.", "label": "Lend · temporary transfer"},
    {"sentence": "A crane walks with Mary.", "label": "Crane · context arrives later"},
    {"sentence": "John walks in a bank with Mary.", "label": "Bank · unresolved context"},
]


def configuration():
    return {"grammars": sorted(GRAMMARS), "examples": EXAMPLES,
            "description": "Two actual DS runs with identical lexical candidates; Jev preferences are the only intervention."}


def validate_options(payload):
    compare = payload.get("compare_jev", False)
    if type(compare) is not bool:
        raise ValueError("compare_jev must be a boolean.")
    if compare and (payload.get("grammar") not in GRAMMARS
                    or payload.get("lexical_mode") != "jev"
                    or "paragraph" in payload or "dialogue" in payload
                    or payload.get("decision_mode", "off") != "off"
                    or payload.get("n_best", 1) != 1):
        raise ValueError("Jev comparison uses one native English sentence, Jev lexical preferences, normal DS search and the first analysis.")


def snapshot(parser, tokens):
    programs = {}
    for word in dict.fromkeys(tokens):
        programs[word] = [{"lines": list(a._source_lines), "type": a.action_type,
                           "parameters": list(a.parameters), "metadata": deepcopy(a.metadata),
                           "no_left_adjustment": a.no_left_adjustment}
                          for a in parser.lexicon.get(word, [])]
    return {"programs": programs, "profile": deepcopy(parser.semantic_profile)}


def setup(inventory, report, *, use_jev):
    def install(parser):
        from dylan.action.lexical_action import LexicalAction
        from dylan.lexical_selection import LexicalSelector
        for word, rows in inventory["programs"].items():
            parser.lexicon[word] = [LexicalAction(word, row["lines"], row["type"], row["no_left_adjustment"],
                parameters=tuple(row["parameters"]), metadata=deepcopy(row["metadata"])) for row in rows]
        parser.lexicon.invalidate_vocab_cache()
        parser.semantic_profile = deepcopy(inventory["profile"])
        lexical = deepcopy({k: v for k, v in report.items() if k != "selection"})
        lexical["comparison_inventory_hash"] = content_hash(snapshot(parser, list(inventory["programs"])))
        if lexical["comparison_inventory_hash"] != content_hash(inventory):
            raise ValueError("The comparison lexical inventory changed during installation.")
        if use_jev:
            parser.lexical_selector = LexicalSelector()
            lexical["selection"] = parser.lexical_selector.report
        return lexical
    return install


def selected_entries(parser, edges):
    from dylan.action.lexical_action import LexicalAction
    entries, index = [], -1
    for edge in edges:
        if edge.word is not None:
            index += 1
        for action in edge.get_actions():
            if isinstance(action, LexicalAction) and action.metadata.get("source") in {"dictionary", "model", "bundled"}:
                entries.append({"index": index, "word": action.word,
                    **{k: action.metadata.get(k) for k in ("lemma", "symbol", "template", "evidence", "source")}})
    return entries


def summary(result, inventory_hash):
    last = result["words"][-1]
    return {"complete": result["complete"], "failure": result["failure"],
            "meaning": last.get("normalized") or last.get("semantics"),
            "used": result["lexical"].get("used", []), "stats": result["stats"],
            "elapsed_ms": result["elapsed_ms"], "inventory_hash": result["lexical"].get("comparison_inventory_hash", inventory_hash),
            "derivation": result["derivation"]}


def compare(payload, on_event=None, *, trace=True):
    from dynamicsyntax import icp
    from dylan.lexical_expansion import expand
    from dylan.nlp.types import utterance_from_text
    from dylan.paragraph_workbench import time_budget, SentenceDeadline
    from dylan.workbench_api import parse_request

    started = time.monotonic()
    bindings = snapshot_meta_bindings()
    request = {**payload, "compare_jev": False}
    grammar = payload["grammar"]
    tokens = [w.word for w in utterance_from_text("Dylan", payload["sentence"]).words]
    if on_event:
        on_event({"event": "lexical", "message": "Preparing identical lexical candidates for DS with and without Jev…"})
    try:
        reset_all_meta_bindings()
        prepared = icp(grammar, top_n=payload.get("top_n", 0), strict=payload.get("strict", False))
        try:
            with time_budget(20):
                controls = set(prepared.forced_repairanda + prepared.repairanda + [prepared.WAIT])
                report = expand(prepared, grammar, tokens, "jev", controls=controls,
                                allow_model_fallback=payload.get("allow_model_fallback", True))
                inventory = snapshot(prepared, tokens)
        finally:
            prepared.close()
        identity = content_hash(inventory)
        reset_all_meta_bindings()
        baseline = None
        try:
            with time_budget(4):
                baseline = parse_request(request, _trace=False, _setup=setup(inventory, report, use_jev=False))
        except SentenceDeadline:
            pass
        without = summary(baseline, identity) if baseline else {
            "complete": False, "failure": {"kind": "comparison_limit", "message": "The baseline exceeded its four-second allowance."},
            "meaning": None, "used": [], "stats": {}, "elapsed_ms": None, "inventory_hash": identity, "derivation": None}
        if on_event:
            on_event({"event": "lexical", "message": "Baseline recorded. Running DS with Jev sense preferences…"})
        reset_all_meta_bindings()
        with time_budget(max(.05, 50 - (time.monotonic() - started))):
            result = parse_request(request, on_event, _trace=trace, _setup=setup(inventory, report, use_jev=True))
        with_jev = summary(result, identity)
        selection = result["lexical"]["selection"]
        before = {e["index"]: e for e in without["used"]}
        after = {e["index"]: e for e in with_jev["used"]}
        changes = [{"index": index, "word": after[index]["word"], "without_jev": before.get(index), "with_jev": after[index]}
                   for index in sorted(before.keys() | after.keys())
                   if index in before and index in after and before[index]["symbol"] != after[index]["symbol"]]
        valid_answers = sum(bool(d.get("answers")) for d in selection["decisions"])
        status = ("inconclusive" if not without["complete"] or not with_jev["complete"] else
                  "no_model_answer" if not valid_answers else "changed" if changes else "same")
        result["jev_comparison"] = {
            "status": status, "without_jev": without, "with_jev": with_jev, "changes": changes,
            "valid_decisions": valid_answers, "live_calls": selection["live_calls"],
            "shared_model_candidates": sum(e.get("source") == "model" for e in report["entries"]),
            "candidate_programs": sum(len(rows) for rows in inventory["programs"].values()),
            "inventory_hash": identity, "same_inventory": without["inventory_hash"] == with_jev["inventory_hash"] == identity,
            "note": "Both runs use the same grammar, lexical programs, initial context, scope and entry limit. Baseline search has an extra four-second cap. Changed means a different selected predicate, not independently verified semantic improvement. Any lexical-model proposals are shared by both runs.",
        }
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return result
    finally:
        restore_meta_bindings(bindings)
