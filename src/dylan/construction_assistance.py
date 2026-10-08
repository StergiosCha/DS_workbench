"""Compile structured connective hypotheses into existing, typed DS templates.

No model-supplied program text is accepted. Preferences reorder alternatives;
they do not remove the existing lexical programs or certify interpretation.
"""
from collections import Counter

from dylan.clause_inventory import CONNECTIVES, RELATIONS, templates


def requested_surfaces(tokens, language, lexicon, closed, failure=None):
    counts = Counter(tokens)
    # A word-level preference cannot distinguish two occurrences of the same
    # connective with different senses. Leave those alternatives to DS for now.
    requested = [w for w in dict.fromkeys(tokens) if failure is None and counts[w] == 1 and (
        len(CONNECTIVES[language].get(w, ())) > 1
        or (w in closed and w not in lexicon and w in CONNECTIVES[language]))]
    target = (failure or {}).get("token")
    if (isinstance(target, str) and target.isalpha() and len(target) <= 40
            and counts[target] == 1 and (target not in closed or target in CONNECTIVES[language])):
        requested.append(target)
    return list(dict.fromkeys(requested))[:8]


def schema(requested):
    fields = {"surface": {"type": "string", "enum": requested},
              "relation": {"type": "string", "enum": list(RELATIONS)},
              "evidence": {"type": "string"}}
    return {"type": "object", "properties": {"constructions": {"type": "array", "maxItems": 8,
        "items": {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}}},
        "required": ["constructions"], "additionalProperties": False}


def compile_proposals(parser, raw, requested, language):
    if not isinstance(raw, dict) or set(raw) != {"constructions"} or not isinstance(raw["constructions"], list) or len(raw["constructions"]) > 8:
        raise ValueError("Expected at most eight structured construction hypotheses.")
    backend = parser.semantic_profile.get("backend")
    if backend not in {"classical", "mltt"}:
        raise ValueError("Construction assistance requires a native semantic backend.")
    from dylan.assisted_parsing import GREEK_CLOSED
    from dylan.lexical_expansion import PROTECTED
    closed = PROTECTED if language == "en" else GREEK_CLOSED
    compiled, seen = [], set()
    for item in raw["constructions"]:
        if not isinstance(item, dict) or set(item) != {"surface", "relation", "evidence"}:
            raise ValueError("A construction supplies surface, relation and evidence only.")
        word, relation, evidence = item["surface"], item["relation"], item["evidence"]
        if not isinstance(word, str) or word not in requested or word in seen or not word.isalpha() or len(word) > 40:
            raise ValueError("Construction surface must be a unique requested single token.")
        if word in closed and word not in CONNECTIVES[language]:
            raise ValueError("An existing function word cannot be repurposed as a clause connective.")
        if not isinstance(relation, str) or relation not in RELATIONS:
            raise ValueError("Unknown construction relation.")
        if word in CONNECTIVES[language] and relation not in CONNECTIVES[language][word]:
            raise ValueError(f"{word}: relation is outside the reviewed readings for this connective.")
        if not isinstance(evidence, str) or not 1 <= len(evidence.strip()) <= 1200:
            raise ValueError("A construction needs a short reading explanation.")
        if parser.semantic_profile.get("predicates", {}).get(relation) != ["Content", "Content"]:
            raise ValueError("The selected grammar does not declare this relation's signature.")
        actions = [parser.lexicon.instantiate_template(word, t, [relation]) for t in templates(backend)]
        compiled.append((dict(item), actions))
        seen.add(word)
    return compiled


def install(parser, compiled, provenance):
    records = []
    for item, actions in compiled:
        word = item["surface"]
        originals = list(parser.lexicon.get(word, []))
        # Reuse matching reviewed actions, retaining their source metadata.
        preferred = []
        for action in actions:
            matching = next((a for a in originals if a._source_lines == action._source_lines), None)
            if matching is None:
                action.metadata.update(source="model-construction", relation=item["relation"], evidence=item["evidence"])
            preferred.append(matching or action)
        parser.lexicon[word] = preferred + [a for a in originals if a not in preferred]
        records.append({**item, **provenance, "source": "model-construction",
            "validation": "Reviewed template and signature checks passed; interpretation remains a hypothesis.",
            "programs": [list(a._source_lines) for a in preferred],
            "added_programs": sum(a not in originals for a in preferred),
            "alternatives_retained": len(parser.lexicon[word]) - len(preferred)})
    parser.lexicon.invalidate_vocab_cache()
    return records


def used_constructions(edges):
    from dylan.action.lexical_action import LexicalAction
    used, index = [], -1
    for edge in edges:
        if edge.word is not None:
            index += 1
        for action in edge.get_actions():
            if (isinstance(action, LexicalAction) and action.action_type in {"clause-post", "clause-front", "clause-post-content"}
                    and len(action.parameters) == 1 and action.parameters[0] in RELATIONS):
                used.append({"index": index, "surface": action.word, "relation": action.parameters[0],
                             "template": action.action_type, "description": RELATIONS[action.parameters[0]],
                             "source": action.metadata.get("source", "grammar")})
    return used
