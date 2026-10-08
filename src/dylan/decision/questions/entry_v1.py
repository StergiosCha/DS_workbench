"""Entry ranking uses left context and actual lexical alternatives only."""

THRESHOLD = 0.50


def questions(entries):
    return {"entry": {"type": "choice", "instructions": (
        "Which listed lexical entry of `next_word` best fits `tokens_so_far`? "
        "Use the grammar/dialect, pointer and open requirements in `tree`, and each entry's "
        "lexical_evidence. Do not assume later words. This is a preference among supplied "
        "analyses; do not judge grammaticality."
    ), "criteria": {**{e["id"]: {"template": e["template"], "parameters": e["params"],
                               "lexical_evidence": e.get("lexical_evidence", {})} for e in entries},
                     "other_or_none": "No listed entry fits the available left context."}}}
