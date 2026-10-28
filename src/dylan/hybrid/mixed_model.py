"""Gaussian crossed-intercept model on log RT, fitted by marginal maximum likelihood.

This predictive comparison model differs from the paper's shifted-lognormal
Bayesian model. Sparse Woodbury solves keep participant/item effects explicit.
"""

from dataclasses import dataclass
import math

import numpy as np
from scipy import sparse
from scipy.optimize import minimize
from scipy.sparse.linalg import splu


@dataclass
class Fit:
    beta: np.ndarray
    beta_covariance: np.ndarray
    residual_variance: float
    group_variances: tuple[float, float]
    groups: tuple[dict, dict]
    offsets: tuple[int, int]
    effects: np.ndarray
    posterior_covariance: np.ndarray
    effect_design: np.ndarray
    converged: bool
    message: str
    objective: float

    def predict(self, x, subjects, items):
        mean = x @ self.beta
        variance = np.full(len(x), self.residual_variance)
        for i, keys in enumerate(zip(subjects, items)):
            indices = []
            for group, key in enumerate(keys):
                if key in self.groups[group]:
                    index = self.offsets[group] + self.groups[group][key]
                    indices.append(index)
                    mean[i] += self.effects[index]
                else:
                    variance[i] += self.group_variances[group]
            if indices:
                variance[i] += self.posterior_covariance[np.ix_(indices, indices)].sum()
            adjusted_x = x[i] - self.effect_design[indices].sum(axis=0) if indices else x[i]
            variance[i] += adjusted_x @ self.beta_covariance @ adjusted_x
        return mean, np.maximum(variance, 1e-10)


def fit(x, y, subjects, items, *, max_iterations=100):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if len(y) < x.shape[1] + 5 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Insufficient or nonfinite model data")
    groups = ({key: i for i, key in enumerate(sorted(set(subjects)))},
              {key: i for i, key in enumerate(sorted(set(items)))})
    offsets = (0, len(groups[0]))
    count = sum(map(len, groups))
    rows = np.repeat(np.arange(len(y)), 2)
    columns = np.array([[groups[0][s], offsets[1] + groups[1][t]] for s, t in zip(subjects, items)]).ravel()
    z = sparse.csr_matrix((np.ones(len(rows)), (rows, columns)), shape=(len(y), count))
    ztz = (z.T @ z).tocsc()
    ztx, zty = z.T @ x, z.T @ y
    xtx, xty, yty = x.T @ x, x.T @ y, y @ y

    def evaluate(log_variances, details=False):
        residual, subject, item = np.exp(log_variances)
        g = np.r_[np.full(len(groups[0]), subject), np.full(len(groups[1]), item)]
        k = sparse.diags(1 / g, format="csc") + ztz / residual
        solver = splu(k)
        kx, ky = solver.solve(ztx), solver.solve(zty)
        information = xtx / residual - ztx.T @ kx / residual**2
        rhs = xty / residual - ztx.T @ ky / residual**2
        covariance = np.linalg.pinv(information, rcond=1e-10)
        beta = covariance @ rhs
        quadratic = yty / residual - zty @ ky / residual**2 - 2 * beta @ rhs + beta @ information @ beta
        logdet = len(y) * math.log(residual) + np.log(g).sum() + np.log(np.abs(solver.U.diagonal())).sum()
        objective = .5 * (logdet + max(0., quadratic) + len(y) * math.log(2 * math.pi))
        if not details:
            return objective
        effects = solver.solve(zty - ztx @ beta) / residual
        posterior = solver.solve(np.eye(count))
        return beta, covariance, effects, posterior, kx / residual, objective

    variance = max(float(np.var(y)), .001)
    optimization = minimize(evaluate, np.log([variance * .6, variance * .3, variance * .1]),
                            method="L-BFGS-B", bounds=[(-12, 3)] * 3,
                            options={"maxiter": max_iterations, "ftol": 1e-9})
    beta, covariance, effects, posterior, effect_design, objective = evaluate(optimization.x, details=True)
    residual, subject, item = np.exp(optimization.x)
    return Fit(beta, covariance, residual, (subject, item), groups, offsets, effects,
               posterior, effect_design, bool(optimization.success), str(optimization.message), objective)


def log_density(y, mean, variance):
    return -.5 * (np.log(2 * np.pi * variance) + (np.asarray(y) - mean)**2 / variance)
