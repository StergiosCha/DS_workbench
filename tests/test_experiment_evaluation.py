from copy import deepcopy

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from scipy.integrate import quad  # noqa: E402

from dylan.experiments.contracts import Configuration  # noqa: E402
from dylan.experiments.evaluation import compare, rt_log_density, simulate, standardize  # noqa: E402
from dylan.experiments.study import prototype  # noqa: E402


@pytest.mark.parametrize("shift", [0., .15])
def test_transformed_density_integrates_to_one_in_response_time_units(shift):
    integral, error = quad(lambda rt: np.exp(rt_log_density(rt, -.2, .3, shift)), shift, np.inf)
    assert integral == pytest.approx(1., abs=1e-7)
    assert error < 1e-6


def test_test_distribution_cannot_change_training_scaling():
    train = np.array([[1., 0., 7.], [1., 2., 7.], [1., 4., 7.]])
    a, _ = standardize(train, np.array([[1., 1., 0.]]))
    b, future = standardize(train, np.array([[1., 1000., 8.]]))
    np.testing.assert_array_equal(a, b)
    assert a.shape[1] == 2
    assert future[0,1] > 100


def fixture_rows():
    return [{"participant":i, "family":"f00", "order":1, "activation":.5, "condition":"matched", "lag":0} for i in range(4)]


def test_provenance_group_count_alignment_and_response_domain_guards():
    rows = fixture_rows()
    config = Configuration()
    responses = simulate(rows, config)
    prepared = {(config.grammar, config.memory): rows}
    coverage = {"common_families":["f00"]}
    result = compare(prototype(), prepared, coverage, responses, data_kind="synthetic")
    assert result["status"] == "insufficient_independent_groups"
    with pytest.raises(ValueError, match="provenance"):
        compare(prototype(), prepared, coverage, responses, data_kind="human")
    with pytest.raises(ValueError, match="Duplicate"):
        compare(prototype(), prepared, coverage, [*responses, responses[0]], data_kind="synthetic")
    reversed_rows = {**prepared, ("ccg-incremental-v1", config.memory):list(reversed(rows))}
    with pytest.raises(ValueError, match="aligned"):
        compare(prototype(), reversed_rows, coverage, responses, data_kind="synthetic")
    responses = deepcopy(responses)
    responses[0]["rt_seconds"] = .1
    result = compare(prototype(), prepared, coverage, responses, data_kind="synthetic")
    assert result["exclusions"]["outside_common_rt_domain"] == 1


def test_simulation_is_reproducible_and_cannot_silently_produce_human_labels():
    rows = fixture_rows()
    a = simulate(rows, Configuration(), seed=12)
    assert a == simulate(rows, Configuration(), seed=12)
    assert a != simulate(rows, Configuration(), seed=13)
    assert all(r["data_kind"] == "synthetic" for r in a)
