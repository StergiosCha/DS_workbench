import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from dylan.hybrid.mixed_model import fit, log_density  # noqa: E402


def test_crossed_model_recovers_signal_and_handles_unseen_groups():
    rng = np.random.default_rng(123)
    subjects = [f"p{i}" for i in range(24) for _ in range(16)]
    items = [f"i{j}" for _ in range(24) for j in range(16)]
    covariate = rng.normal(size=len(subjects))
    x = np.column_stack([np.ones(len(subjects)), covariate])
    subject_effect = rng.normal(0, .2, 24)
    item_effect = rng.normal(0, .1, 16)
    y = 1 + .4 * covariate + np.repeat(subject_effect, 16) + np.tile(item_effect, 24) + rng.normal(0, .1, len(subjects))
    result = fit(x, y, subjects, items)
    assert result.converged
    assert abs(result.beta[1] - .4) < .04
    known_mean, known_var = result.predict(x[:1], subjects[:1], items[:1])
    unseen_mean, unseen_var = result.predict(x[:1], ["new-subject"], ["new-item"])
    assert unseen_var[0] > known_var[0]
    assert abs(unseen_mean[0] - x[0] @ result.beta) < 1e-10
    assert np.isfinite(log_density(y[:1], known_mean, known_var)).all()


def test_predictive_covariance_matches_dense_joint_gaussian():
    rng = np.random.default_rng(71)
    subjects = [str(i) for i in range(6) for _ in range(5)]
    items = [str(i) for _ in range(6) for i in range(5)]
    x = np.column_stack([np.ones(30), rng.normal(size=30)])
    y = x @ np.array([.4, .7]) + rng.normal(0, .3, 30)
    fitted = fit(x, y, subjects, items)
    z = np.zeros((30, 11))
    for i, (subject, item) in enumerate(zip(subjects, items)):
        z[i, int(subject)] = z[i, 6 + int(item)] = 1
    g = np.diag([fitted.group_variances[0]] * 6 + [fitted.group_variances[1]] * 5)
    v = z @ g @ z.T + np.eye(30) * fitted.residual_variance
    cross = z[:2] @ g @ z.T
    inv = np.linalg.inv(v)
    adjusted = x[:2] - cross @ inv @ x
    expected = (z[:2] @ g @ z[:2].T + np.eye(2) * fitted.residual_variance
                - cross @ inv @ cross.T + adjusted @ fitted.beta_covariance @ adjusted.T)
    mean, variance = fitted.predict(x[:2], subjects[:2], items[:2])
    assert np.allclose(mean, x[:2] @ fitted.beta + cross @ inv @ (y - x @ fitted.beta))
    assert np.allclose(variance, np.diag(expected))
