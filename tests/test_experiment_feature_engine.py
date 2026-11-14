import pytest

from dylan.experiments.contracts import Observation
from dylan.experiments.feature_engine import FeatureEngine, MODES, register


def analyse(text, mode="ccg-feature-head-v1"):
    return FeatureEngine(mode).analyse(Observation(text, task="sentence"))


@pytest.mark.parametrize("text,accepted", [
    ("the student near the sailors is good", True),
    ("the student near the sailors are good", False),
    ("the students near the sailor are good", True),
    ("the students near the sailor is good", False),
    ("the mechanic hurt himself", True),
    ("the mechanics hurt themselves", True),
    ("the mechanic near the sailors hurt himself", True),
    ("the mechanic near the sailors hurt themselves", False),
    ("the mechanics near the sailor hurt themselves", True),
    ("the mechanics near the sailor hurt himself", False),
    ("the taxi driver behind the teachers is good", True),
    ("the taxi drivers behind the teacher are good", True),
    ("the student near the sailors behind the mechanic are good", False),
    ("the students near the sailor behind the mechanic are good", True),
    ("the students near the sailor are playing tennis", True),
    ("the students near the sailor is playing tennis", False),
    ("the students near the sailor enjoy tennis", True),
    ("the students near the sailor enjoys tennis", False),
])
def test_dependency_uses_np_head_in_controls_outside_the_source_suite(text, accepted):
    result = analyse(text)
    assert result.complete == accepted
    assert result.status == ("complete" if accepted else "constraint_rejection")
    assert result.provenance["diagnostic_coverage"]


def test_nearest_changes_controller_and_constraints_are_individually_removable():
    sv = "the student near the sailors are good"
    reflexive = "the student near the sailors hurt themselves"
    assert analyse(sv, "ccg-feature-nearest-v1").complete
    assert analyse(reflexive, "ccg-feature-nearest-v1").complete
    assert analyse(sv, "ccg-feature-no-agreement-v1").complete
    assert not analyse(reflexive, "ccg-feature-no-agreement-v1").complete
    assert not analyse(sv, "ccg-feature-no-binding-v1").complete
    assert analyse(reflexive, "ccg-feature-no-binding-v1").complete
    for text in (sv, reflexive):
        assert analyse(text, "ccg-feature-none-v1").complete


def test_binding_interpretation_reuses_the_local_subject():
    result = analyse("the mechanic hurt himself")
    assert result.complete and "local_reflexive" not in result.meanings[0]
    assert result.meanings[0].count("(the mechanic)") == 2
    assert all(c["mechanism"] == "local_reflexive"
               for a in result.provenance["analyses"] for c in a["checks"])


def test_all_modes_share_the_lexicon_and_constraint_rejection_has_a_derivation():
    results = [analyse("the student near the sailors is good", mode) for mode in MODES]
    assert len({r.provenance["lexicon_sha256"] for r in results}) == 1
    rejected = analyse("the student near the sailors are good")
    check = rejected.provenance["rejections"][0]
    assert check["subject_head"]["lemma"] == "student"
    assert check["unconstrained_derivation"]["category"] == "S"
    assert check["checks"][0]["actual"]["nodes"] != check["checks"][0]["required"]["nodes"]


def test_unknown_structure_and_bounds_never_become_constraint_rejections():
    assert analyse("the glorp is good").status == "unsupported_lexicon"
    assert analyse("the student the sailors is good").status == "unsupported_structure"
    assert analyse("the " * 31 + "student is good").status == "unsupported_length"
    assert not analyse("the student is").complete


def test_prefix_states_do_not_see_future_words_or_multiword_prepositions():
    result = analyse("the student in front of the sailors is good")
    for i, frame in enumerate(result.states):
        assert frame["observed"] == "the student in front of the sailors is good".split()[:i + 1]
    prefix = FeatureEngine("ccg-feature-head-v1").analyse(
        Observation("the student in front of", task="fragment"))
    assert prefix.states == result.states[:5]
    assert not prefix.complete


def test_registration_is_explicit_and_runs_in_the_neutral_host():
    register()
    from dylan.experiments.contracts import Configuration
    from dylan.experiments.host import Session

    session = Session(Configuration(grammar="ccg-feature-head-v1", memory="count-v1"))
    try:
        observation = Observation("the students near the sailor are good", task="sentence")
        first, second = session.observe(observation), session.observe(observation)
        assert first["analysis"]["complete"] and first["cue_count"] > 0
        assert first["activation"] == 0 and second["activation"] > 0
        assert first["analysis"]["meanings"] == second["analysis"]["meanings"]
    finally:
        session.close()
