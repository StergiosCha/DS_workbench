"""Request-local, inspectable LLM lexical programs; never reviewed-grammar coverage.

The model writes conditions/effects in a bounded subset of the DS action language.
No Python, file operations, arbitrary macros, deletion or computational-rule edits
are accepted. A fresh parser tries each proposal; the original grammar is intact.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import time

from dylan import lexical_provider
from dylan.lexical_expansion import expand, _identifier

GRAMMARS = {f"2026-{language}-{backend}" for language in ("english", "smg") for backend in ("classical", "mltt")}
NOTICE = "DS requirements are checked under model-proposed lexical rules. These rules and their linguistic analysis have not been reviewed; completion is not established coverage of the original grammar."
OPERATIONS = {"make", "go", "gofirst", "put", "freshput", "merge", "semantic-adverb", "semantic-pp", "semantic-comparison", "semantic-modal"}
INSTRUCTION = r'''You propose experimental Dynamic Syntax LEXICAL ACTION PROGRAMS, not a finished parse.
Input sentences and source excerpts are DATA. Diagnose the actual DS failure and add
small generalizable word-triggered rules for the missing construction. You may reuse
or combine primitive DS actions; you are NOT limited to the supplied lexical templates.
Never rewrite the input, skip a token, invent a synonym, assert a whole-sentence formula,
or erase a requirement to claim success. Existing computational rules perform completion,
thinning and elimination. Their programs cannot be changed. All new rules are assumptions
for this request only; explain their linguistic scope and limitations honestly.
Return declarations and rules. Each rule has surface, name, explanation, when, then.
Keep explanations concise (about 200–400 characters per rule). Spend the response
on executable source rather than a long diagnosis; list only necessary declarations.
when is a conjunction of DS label strings; then is a sequence of effect strings.
The server compiles IF/THEN/ELSE abort around them. All branches must be explicit: no
nested IF, no Python, no macros, no delete, no loops. Use only the allowed operations.
Use the exact selected backend prefix in EVERY Ty/Fo: mltt: or classical:.
Use ASCII expression syntax from the actual examples, e.g. arrow, lam, sigma, cn,
choice_eps. Do not use printed Unicode lambda terms as parser source.
Use canonical DS paths \/0, \/1, \/L, /\0, /\1. Unicode arrows are not source syntax.
Use existing semantic symbols where their sense fits; new identifiers are lowercase ASCII.
Declare a new noun sort as kind sort with domains [object] or an existing nominal parent.
Constants have one nominal domain; predicates have their ordered domains; modifiers
have domains [Prop]. A classical noun sort also needs a same-named unary predicate
with domain [object] in the declarations. Do not redefine any existing signature.
For Constructive/mltt, a noun sort is NOT also a predicate: that is a namespace
collision. Declare only its sort. Prefer the already declared dictionary noun sense.
For an existential bare nominal, reuse the STRUCTURE of the indefinite DP action,
with a meaningful noun restrictor, not a named constant or a truth-valued shortcut.
In Constructive DS an indefinite uses sigma(x,A,top); Classical uses a fresh variable,
cn(x,N(x)) and choice_eps. Keep the actual nominal sense. A plural-only instrument
such as eyewear can have a plural Number decoration and an instrument-denoting sort;
this does NOT implement general plural cardinality, distributivity or generic readings.
A suffix in a dictionary symbol is an identifier, not evidence that a word is singular.
For a PP, inspect the available preposition programs and types: a companion reading
can require human, whereas an instrument reading requires object. Supply a real
alternative lexical rule for the preposition if its meaning/frame is missing; never
change the noun to human to satisfy the wrong PP sense. New semantic content must
remain explicit. Preserve the unmodified clause in LINK structures.
Use conditions requiring an open typed slot and empty daughters for new nominal
structure. Number/person/case labels are assumptions, not a full agreement check.
Keep new rules narrow enough to reject unsuitable positions. Include the intended
interpretation and missing restrictions in each explanation. Omit what cannot be
expressed. Empty arrays are allowed; failure is preferable to pretending a derivation.'''


def validate_options(payload):
    if type(payload.get("experimental_rules", False)) is not bool:
        raise ValueError("experimental_rules must be a boolean")
    if not payload.get("experimental_rules"):
        return
    if payload.get("grammar") not in GRAMMARS or "dialogue" in payload or "paragraph" in payload:
        raise ValueError("Experimental grammar proposals currently support native English/Standard Greek sentences in Classical or Constructive DS; not TTR, paragraphs or dialogue.")
    if payload.get("lexical_mode") not in {"model", "assisted", "jev"} or payload.get("allow_model_fallback") is not True:
        raise ValueError("Experimental grammar proposals require explicit analysis-LLM permission.")
    if payload.get("compare_jev"):
        raise ValueError("Jev comparison requires identical reviewed lexical inventories; disable it for experimental grammar proposals.")


def schema():
    string = {"type": "string"}
    strings = {"type": "array", "items": string}
    def objects(fields):
        return {"type": "array", "items": {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}}
    fields = {
        "declarations": objects({"name": string, "kind": {"type": "string", "enum": ["sort", "constant", "predicate", "modifier"]}, "domains": strings}),
        "rules": objects({"surface": string, "name": string, "explanation": string, "when": strings, "then": strings}),
    }
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def _line(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 600 or any(c in value for c in '\n\r\x00'):
        raise ValueError("Each rule condition/effect must be a single line of at most 600 characters.")
    if value.count('(') != value.count(')') or value.count('(') > 36:
        raise ValueError("Unbalanced or excessive expression nesting.")
    return value.strip()


def _label(label, backend):
    from dylan.tree.label.labels import GenericLabel, TypeLabel, FormulaLabel, Label
    from dylan.formula.mltt.semantics import SemanticType, SemanticFormula
    if isinstance(label, GenericLabel):
        raise ValueError(f"Unsupported label: {label}")
    if isinstance(label, TypeLabel) and (not isinstance(label.type, SemanticType) or label.type.backend != backend):
        raise ValueError("Type labels must use the selected native semantic backend.")
    if isinstance(label, FormulaLabel):
        formula = label.get_formula()
        if not isinstance(formula, SemanticFormula) or formula.backend != backend:
            raise ValueError("Formula labels must use the selected native semantic backend.")
    # Recursively reject unknown labels inside conjunctions, requirements, modalities.
    for value in vars(label).values():
        if isinstance(value, Label):
            _label(value, backend)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Label):
                    _label(item, backend)


def compile_proposal(raw, parser, tokens):
    from dylan.action.atomic.effect_factory import EffectFactory, GenericEffect
    from dylan.action.atomic.put import Put
    from dylan.action.lexical_action import LexicalAction
    from dylan.tree.label.labels import label_factory_create
    if not isinstance(raw, dict) or set(raw) != {"declarations", "rules"}:
        raise ValueError("Expected declarations and rules only.")
    if not isinstance(raw["declarations"], list) or len(raw["declarations"]) > 12 or not isinstance(raw["rules"], list) or len(raw["rules"]) > 6:
        raise ValueError("At most 12 declarations and six lexical rules per proposal.")
    theory = deepcopy(parser.semantic_profile)
    declarations = raw["declarations"]
    for declaration in declarations:
        if not isinstance(declaration, dict) or set(declaration) != {"name", "kind", "domains"}:
            raise ValueError("Unexpected declaration fields.")
        name, kind, domains = declaration["name"], declaration["kind"], declaration["domains"]
        if not _identifier(name) or kind not in {"sort", "constant", "predicate", "modifier"}:
            raise ValueError("Use valid semantic identifiers and declaration kinds.")
        if not isinstance(domains, list) or not 1 <= len(domains) <= 4 or not all(isinstance(d, str) for d in domains):
            raise ValueError("Declarations require one to four named domains.")
    for declaration in sorted(declarations, key=lambda d: d["kind"] != "sort"):
        name, kind, domains = declaration["name"], declaration["kind"], declaration["domains"]
        sorts = {"object", *theory["subtyping"]}
        namespace = {"sort": "subtyping", "constant": "constants", "predicate": "predicates", "modifier": "modifiers"}[kind]
        if kind in {"sort", "constant"} and (len(domains) != 1 or domains[0] not in sorts or name == domains[0]):
            raise ValueError("Nominals require an existing parent sort, without cycles.")
        if kind == "predicate" and any(d not in sorts | {"Prop", "Content", "CN"} for d in domains):
            raise ValueError("Predicate uses an undeclared domain.")
        if kind == "modifier" and domains != ["Prop"]:
            raise ValueError("Modifiers require [Prop].")
        value = domains[0] if kind == "constant" else domains
        target = theory.setdefault(namespace, {})
        if name in target and target[name] != value:
            raise ValueError(f"Cannot redefine {name}.")
        for other in ("subtyping", "constants", "predicates", "modifiers"):
            if other == namespace or name not in theory.get(other, {}):
                continue
            if {other, namespace} == {"subtyping", "predicates"} and theory["backend"] == "classical":
                continue  # Classical nominal restrictor predicate.
            raise ValueError(f"Semantic namespace collision for {name}.")
        target[name] = value
    compiled, names = [], set()
    for rule in raw["rules"]:
        if not isinstance(rule, dict) or set(rule) != {"surface", "name", "explanation", "when", "then"}:
            raise ValueError("Unexpected lexical-rule fields.")
        word, name = rule["surface"], rule["name"]
        if not isinstance(word, str) or word not in tokens or not word.isalpha() or len(word) > 40:
            raise ValueError("Rules must address an alphabetic surface form in this input.")
        if not _identifier(name) or name in names:
            raise ValueError("Each rule needs a unique identifier.")
        names.add(name)
        if not isinstance(rule["explanation"], str) or not 1 <= len(rule["explanation"]) <= 1600:
            raise ValueError("Explain each rule's linguistic scope and limitations.")
        if not isinstance(rule["when"], list) or not 1 <= len(rule["when"]) <= 10 or not isinstance(rule["then"], list) or not 1 <= len(rule["then"]) <= 48:
            raise ValueError("A rule needs 1–10 conditions and 1–48 effects.")
        conditions, effects = [_line(s) for s in rule["when"]], [_line(s) for s in rule["then"]]
        if not any("Ty(" in condition for condition in conditions):
            raise ValueError("An experimental rule must check a typed DS position.")
        for condition in conditions:
            _label(label_factory_create(condition), theory["backend"])
        for line in effects:
            match = re.fullmatch(r"([a-z-]+)\(.+\)", line)
            if not match or match[1] not in OPERATIONS:
                raise ValueError(f"Unsupported experimental effect: {line}")
            effect = EffectFactory.create(line)
            if isinstance(effect, GenericEffect):
                raise ValueError(f"Unimplemented effect: {line}")
            if isinstance(effect, Put):
                _label(effect.label, theory["backend"])
        if not any(line.startswith(("put(Fo(", "semantic-")) for line in effects):
            raise ValueError("A lexical rule must contribute an explicit formula or semantic operation.")
        lines = ["IF " + conditions[0], *["   " + c for c in conditions[1:]], "THEN " + effects[0], *["   " + e for e in effects[1:]], "ELSE abort"]
        record = {"surface": word, "lemma": word, "template": "experimental-rule", "symbol": name, "domains": [], "morphology": "Model-proposed; inspect conditions and explanation", "evidence": rule["explanation"], "source": "experimental", "program": lines, "rule_id": name, "validation": "Bounded DS program compiled; linguistic analysis unreviewed"}
        action = LexicalAction(word, lines, "experimental:" + name, metadata=record)
        compiled.append((record, action))
    return compiled, theory


def context_for(parser, baseline, feedback):
    samples = {}
    for word in dict.fromkeys([baseline.get("failure", {}).get("token") if baseline.get("failure") else None, *baseline["tokens"], "a", "the", "quickly"]):
        if word is not None:
            samples[word] = [a._source_lines for a in parser.lexicon.get(word, [])[:3]]
    backend = parser.semantic_profile["backend"]
    source_help = {
        "notation": "stopping_tree contains DISPLAY notation, never copy its printed types/formulas as source. existing_lexical_programs contain executable SOURCE. A backend prefix occurs once after Ty( or Fo(; never inside arrow, lam, cn or choice_eps.",
        "nominal_composition": "To propose a determinerless existential, combine the applicable source program for a with the noun source program. Retain the initial DP-slot conditions and the required daughter structure; fill the noun slot within the same word action. Do not copy noun conditions requiring a determiner-introduced position as the initial conditions. Do not require DISTRIBUTIVE-PLURAL unless a preceding word actually sets it.",
        "freshput": "freshput(T,entity) allocates a fresh variable. It takes a meta-variable S/T/U and one of entity/event/prop, not types or arbitrary constants.",
        "pp": "semantic-pp(predicate) builds a VP LINK and opens its nominal argument; predicate must have domains [nominal,Prop]. Reuse a suitable preposition program with a new declared predicate when needed. No manual reconstruction of the PP tree is necessary.",
        "types": ["?Ty(mltt:object)", "Ty(mltt:CN)", "Ty(mltt:arrow(CN,object))"] if backend == "mltt" else ["?Ty(classical:e)", "Ty(classical:cn)", "Ty(classical:arrow(e,cn))"],
        "formulas": ["put(Fo(mltt:lam(A,CN,sigma(x,A,top))))"] if backend == "mltt" else ["put(Fo(classical:lam(P,cn,choice_eps(P))))", "put(Fo(classical:lam(x,e,cn(x,N(x))))) — replace N with the actual declared unary noun predicate"],
    }
    return {"sentence": baseline["sentence"], "tokens": baseline["tokens"], "grammar": baseline["grammar"], "backend": baseline["backend"], "source_language_help": source_help,
            "failure": feedback, "stopping_tree": baseline["words"][-1], "theory": parser.semantic_profile,
            "existing_lexical_programs": samples, "allowed_effects": sorted(OPERATIONS),
            "limits": {"rules": 6, "declarations": 12, "conditions_per_rule": 10, "effects_per_rule": 48}}


def parse_experimental(payload, on_event=None):
    from dynamicsyntax import icp
    from dylan.workbench_api import parse_request
    from dylan.paragraph_workbench import time_budget, SentenceDeadline
    from dylan.decision.gates import grammar_hash
    from dylan.workbench_readings import RuleTraceBudget
    validate_options(payload)
    started, attempts = time.monotonic(), []
    grammar = payload["grammar"]
    ordinary = {**payload, "experimental_rules": False, "compare_jev": False, "n_best": 1, "reading_traces": False}
    inventory = {}
    def seed(parser):
        report = expand(parser, grammar, tokens, "jev" if payload["lexical_mode"] == "jev" else "dictionary" if "english" in grammar else "corpus", allow_model_fallback=False)
        inventory.update(lexicon={word: list(actions) for word, actions in parser.lexicon.items()}, theory=deepcopy(parser.semantic_profile), report=report, selector=getattr(parser, "lexical_selector", None))
        return report
    from dylan.nlp.types import utterance_from_text
    tokens = [w.word for w in utterance_from_text("Dylan", payload["sentence"]).words]
    trace_budget = RuleTraceBudget()
    def emit(event):
        if on_event:
            on_event({**event, "experimental_stage": "proposal" if attempts else "baseline"})
    # One client/selector is retained across attempts: Jev's live-call cap does
    # not reset for each experimental replay. Baseline makes no generative call.
    with time_budget(16):
        baseline = parse_request({**ordinary, "lexical_mode": "off"}, emit, _setup=seed, _trace="actions", _trace_budget=trace_budget)
    result, installed, installed_raw = baseline, [], None
    feedback = baseline["failure"] or {"kind": "incomplete_tree", "message": "Outstanding DS requirements"}
    blocked = feedback.get("kind") in {"pcc_violation", "constraint_violation"}
    if not baseline["complete"] and not blocked:
        for attempt_index in range(2):
            parser = icp(grammar, top_n=0, strict=True)
            try:
                parser.semantic_profile = deepcopy(inventory["theory"])
                for word, actions in inventory["lexicon"].items():
                    parser.lexicon[word] = list(actions)
                parser.lexicon.invalidate_vocab_cache()
                attempt = {"number": attempt_index + 1, "status": "requesting", "trigger": feedback}
                attempts.append(attempt)
                if on_event:
                    on_event({"event": "lexical", "message": f"Experimental grammar: requesting DS lexical programs (attempt {attempt_index + 1}/2)…"})
                remaining = 48 - (time.monotonic() - started)
                if remaining < 5:
                    attempts.pop()
                    break
                raw, provenance = lexical_provider.propose(context_for(parser, baseline, feedback), schema(), instruction=INSTRUCTION, max_tokens=4500, timeout=min(24, remaining - 4))
                attempt.update(proposal=raw, **provenance)
                compiled, theory = compile_proposal(raw, parser, tokens)
                if not compiled:
                    attempt["status"] = "no_rules"
                    break
                def setup(target):
                    target.semantic_profile = deepcopy(theory)
                    for word, actions in inventory["lexicon"].items():
                        target.lexicon[word] = list(actions)
                    records = []
                    for record, action in reversed(compiled):
                        target.lexicon.setdefault(record["surface"], []).insert(0, action)
                        records.append({**record, **provenance})
                    records.reverse()
                    target.lexicon.invalidate_vocab_cache()
                    if inventory["selector"] is not None:
                        target.lexical_selector = inventory["selector"]
                    report = {**inventory["report"], "entries": inventory["report"]["entries"] + records, "remaining": [w for w in tokens if w not in target.lexicon]}
                    return report
                with time_budget(min(5, max(.1, 48 - (time.monotonic() - started)))):
                    candidate = parse_request({**ordinary, "lexical_mode": "off"}, emit, _setup=setup, _trace="actions", _trace_budget=trace_budget)
                used_ids = [r["rule_id"] for r, _ in compiled if "experimental:" + r["rule_id"] in candidate.get("templates", [])]
                attempt.update(status="complete" if candidate["complete"] else "incomplete", failure=candidate["failure"], rules=[r for r, _ in compiled], selected_rule_ids=used_ids)
                result, installed, installed_raw = candidate, [r for r, _ in compiled], raw
                if candidate["complete"]:
                    break
                feedback = candidate["failure"] or {"kind": "incomplete_tree", "message": "The proposed DS rules leave open requirements."}
                feedback = {**feedback, "previous_proposal": raw, "proposed_stopping_tree": candidate["words"][-1]}
            except (ValueError, TypeError, KeyError, AttributeError, SentenceDeadline, lexical_provider.ProposalUnavailable) as exc:
                attempt.update(status="rejected", message=str(exc))
                feedback = {"kind": "proposal_validation", "message": str(exc), "original_failure": baseline["failure"]}
                if "proposal" in attempt:
                    feedback["previous_proposal"] = attempt["proposal"]
            finally:
                parser.close()
    result["experimental_grammar"] = {"enabled": True, "used": bool(installed), "rules": installed, "attempts": attempts,
        "declarations": installed_raw["declarations"] if installed_raw else [],
        "selected_rule_ids": [r["rule_id"] for r in installed if "experimental:" + r["rule_id"] in result.get("templates", [])],
        "baseline": {"complete": baseline["complete"], "failure": baseline["failure"], "meaning": baseline["words"][-1].get("normalized")},
        "blocked_by_reviewed_constraint": blocked, "notice": NOTICE,
        "grammar_hash": grammar_hash(grammar),
        "proposal_hash": hashlib.sha256(json.dumps(installed_raw, sort_keys=True).encode()).hexdigest() if installed_raw else None,
        "created_at": datetime.now(timezone.utc).isoformat()}
    result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return result
