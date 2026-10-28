import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from dylan.hybrid.comparison import folds, standardize  # noqa: E402
from dylan.hybrid.predictors import lexical_features  # noqa: E402


def test_family_and_pattern_splits_block_shared_inputs():
    rows = [dict(family=f"f{i}", study=1, subject=i, prime=f"prime{i}", target=f"target{i}", pos_target=f"pos{i}") for i in range(12)]
    rows[1]["prime"] = rows[0]["target"]
    rows[2]["target"] = rows[1]["target"]
    assignment, _ = folds(rows)
    assert assignment[0] == assignment[1] == assignment[2]
    rows[4]["pos_target"] = rows[3]["pos_target"]
    assignment, _ = folds(rows, "pattern")
    assert assignment[3] == assignment[4]
    assert len(set(assignment)) == 3


def test_standardization_cannot_see_test_set_distribution():
    train = np.array([[1., 0.], [1., 2.]])
    transformed, heldout = standardize(train, np.array([[1., 101.]]))
    assert transformed[:, 1].tolist() == [-1., 1.]
    assert heldout[0, 1] == 100


def test_study_four_uses_displayed_length_for_frequency():
    metadata = {"four": 1000, "tri1": 10, **{f"uni{i}": 2 for i in range(1, 5)}}
    three, four = lexical_features(metadata, 3), lexical_features(metadata, 4)
    assert three["string_frequency"] == pytest.approx(np.log1p(10))
    assert four["string_frequency"] == pytest.approx(np.log1p(1000))
