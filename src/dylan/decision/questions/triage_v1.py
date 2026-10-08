"""Backlog estimates are separate from source judgments and parser failures."""

FAMILIES = (
    "placement negation na imperative gerund prohibitive cluster pcc doubling clld htld "
    "climbing auxiliary dp_case svo vso ovs wh relative coordination ethical_dative diachronic "
    "name indefinite universal_subj universal_obj definite adjective adverb complement "
    "relative_subj relative_obj wh_subj wh_obj yes_no coordination_prop coordination_vp "
    "tense_aux pronoun pp_adjunct pp_arg ditransitive copula_adj copula_np other"
).split()
THRESHOLD = 0.60


def questions():
    return {
        "failure_kind_estimate": {
            "type": "choice",
            "instructions": "Estimate a software coverage gap. Do not judge grammaticality.",
            "criteria": {key: key.replace("_", " ") for key in (
                "lexicon_gap", "construction_gap", "semantic_type_mismatch", "other")},
        },
        "construction_family": {
            "type": "choice",
            "instructions": "Which construction family should a human investigate first?",
            "criteria": {key: key.replace("_", " ") for key in FAMILIES},
        },
        "distance_from_coverage": {
            "type": "score",
            "instructions": "Estimate implementation distance, not linguistic acceptability.",
            "criteria": [
                "One lexicon row away: a template exists for every construction.",
                "One lexical template away: existing computational rules cover the construction.",
                "One computational rule or trigger away: a described construction remains unimplemented.",
                "Outside the described system: no supplied construction description covers it.",
            ],
        },
    }
