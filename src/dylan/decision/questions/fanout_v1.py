"""Order existing DS continuations using only the observed prefix."""


def questions(candidates):
    return {"continuation": {
        "type": "choice",
        "instructions": (
            "Which candidate DS continuation should be explored first for tokens_so_far and next_word? "
            "Use the specified grammar/dialect, pointer, open requirements, lexical evidence and "
            "candidate trees. All candidates already exist in the parser. Judge contextual fit "
            "within this prefix; do not assume unseen later words, declare grammaticality, "
            "invent actions or repair input. Choose uncertain if no preference is supported."
        ),
        "criteria": {**{candidate["id"]: {"candidate_state": f"candidates[{i}]"}
                         for i, candidate in enumerate(candidates)},
                     "uncertain": "The available prefix gives no reliable preference."},
    }}
