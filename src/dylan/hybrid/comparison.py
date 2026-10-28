"""Frozen held-out comparisons; unsupported DS families are never imputed as success."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from dylan.hybrid.dataset import write_jsonl
from dylan.hybrid.mixed_model import fit, log_density
from dylan.hybrid.predictors import build

BASE = ["prime_string_frequency", "prime_unigram_frequency", "prime_bigram_frequency",
        "target_string_frequency", "target_unigram_frequency", "target_bigram_frequency",
        "prime_characters", "target_characters", "prime_words", "target_words",
        "semantic_similarity", "trial_order", "lexical_overlap", "lexical_recency", "constituent_condition"]
POS = ["pos2_overlap", "pos3_overlap", "pos2_recency", "pos3_recency", "pos2_frequency", "pos3_frequency"]
TREE = ["tree_overlap", "tree_recency"]
ACTION = ["action_overlap", "action_recency", "state_overlap", "state_recency"]
MODELS = {"M0": BASE, "M1": BASE + POS, "M2": BASE + TREE,
          "M3": BASE + ACTION, "M4": BASE + POS + ACTION,
          "M1-bigrams": BASE + [x for x in POS if "pos2" in x],
          "M1-trigrams": BASE + [x for x in POS if "pos3" in x],
          "M3-actions": BASE + [x for x in ACTION if "action" in x],
          "M3-states": BASE + [x for x in ACTION if "state" in x]}


def family_components(records, *, pattern=False):
    """Union families sharing a displayed string (or target POS in pattern tests)."""
    parent = {r["family"]: r["family"] for r in records}

    def root(family):
        while parent[family] != family:
            parent[family] = parent[parent[family]]
            family = parent[family]
        return family

    owners = {}
    for row in records:
        keys = [row["pos_target"]] if pattern else [row["prime"], row["target"]]
        for key in keys:
            if key in owners:
                first, second = root(row["family"]), root(owners[key])
                parent[max(first, second)] = min(first, second)
            owners[key] = row["family"]
    return {f: root(f) for f in parent}


def folds(records, regime="family", seed=20261028, count=3):
    components = family_components(records, pattern=regime == "pattern")
    keys = [(f"s{r['study']}:p{r['subject']}" if regime == "participant" else components[r["family"]]) for r in records]
    unique = sorted(set(keys), key=lambda k: hashlib.sha256(f"{seed}:{k}".encode()).hexdigest())
    mapping = {key: i % count for i, key in enumerate(unique)}
    return np.array([mapping[k] for k in keys]), keys


def design(records, columns):
    return np.asarray([[1., *[r["features"][c] for c in columns],
                        *[float(r["study"] == s) for s in [2, 3, 4]]] for r in records])


def standardize(train, test):
    center, scale = train.mean(axis=0), train.std(axis=0)
    keep = scale > 1e-10
    keep[0] = True
    center[0], scale[0] = 0., 1.
    return (train[:, keep] - center[keep]) / scale[keep], (test[:, keep] - center[keep]) / scale[keep]


def logistic(train, y, test):
    # Companion accuracy model; regularized fixed-effects logistic regression.
    # It is distinct from the crossed-intercept RT model and reported as such.
    penalty = np.ones(train.shape[1])
    penalty[0] = 0

    def objective(beta):
        scores = train @ beta
        value = np.logaddexp(0, scores).sum() - y @ scores + .5 * (penalty * beta**2).sum()
        gradient = train.T @ (expit(scores) - y) + penalty * beta
        return value, gradient

    result = minimize(objective, np.zeros(train.shape[1]), jac=True, method="L-BFGS-B",
                      options={"maxiter": 150})
    return np.clip(expit(test @ result.x), 1e-8, 1 - 1e-8), bool(result.success)


def evaluate(records, models, regime, *, fold_count=3):
    rt_records = [r for r in records if r["included"]]
    assignments, groups = folds(rt_records, regime, count=fold_count)
    if len(set(groups)) < fold_count * 2:
        return {"status": "insufficient_independent_groups", "groups": len(set(groups))}
    y = np.log([r["rt_seconds"] for r in rt_records])
    subjects = np.array([f"s{r['study']}:p{r['subject']}" for r in rt_records])
    items = np.array([r["family"] for r in rt_records])
    scores, diagnostics, per_row = {}, {}, {}
    for name in models:
        matrix = design(rt_records, MODELS[name])
        density, predicted, variances = np.zeros(len(y)), np.zeros(len(y)), np.zeros(len(y))
        diagnostics[name] = []
        for fold in range(fold_count):
            train, test = assignments != fold, assignments == fold
            x_train, x_test = standardize(matrix[train], matrix[test])
            fitted = fit(x_train, y[train], subjects[train], items[train])
            mu, variance = fitted.predict(x_test, subjects[test], items[test])
            density[test], predicted[test], variances[test] = log_density(y[test], mu, variance), mu, variance
            diagnostics[name].append({"fold": fold, "train": int(train.sum()), "test": int(test.sum()),
                "design_columns": int(x_train.shape[1]), "design_rank": int(np.linalg.matrix_rank(x_train)),
                "converged": fitted.converged, "message": fitted.message,
                "residual_variance": fitted.residual_variance, "group_variances": fitted.group_variances})
        scores[name] = {"mean_log_predictive_density": float(density.mean()),
                        "log_rt_rmse": float(np.sqrt(np.mean((y - predicted)**2))),
                        "converged_all_folds": all(d["converged"] for d in diagnostics[name])}
        scores[name]["rank_deficient"] = any(d["design_rank"] < d["design_columns"] for d in diagnostics[name])
        per_row[name] = density
        # Contrasts are descriptive means of held-out conditional predictions,
        # not a new causal estimate or a substitute for published posterior contrasts.
        contrasts = defaultdict(lambda: defaultdict(list))
        for i, row in enumerate(rt_records):
            cell = f"s{row['study']}:{row['pattern'] or row.get('constituent') or 'all'}"
            condition = {"exp": "experimental", "con": "control"}.get(row["condition"], row["condition"])
            contrasts[cell][condition].append(float(np.exp(predicted[i] + variances[i] / 2) * 1000))
        scores[name]["heldout_predicted_cell_differences_ms"] = {
            key: float(np.mean(cells["experimental"]) - np.mean(cells["control"]))
            for key, cells in contrasts.items() if cells["experimental"] and cells["control"]}
        print(f"{regime} {name}: held-out log density {density.mean():.6f}", flush=True)
    rng = np.random.default_rng(20261028)
    group_indices = {group: np.flatnonzero(np.array(groups) == group) for group in sorted(set(groups))}
    for name in models:
        differences = per_row[name] - per_row["M0"]
        sums = np.array([differences[indices].sum() for indices in group_indices.values()])
        counts = np.array([len(indices) for indices in group_indices.values()])
        resamples = rng.integers(0, len(sums), size=(500, len(sums)))
        bootstrap = sums[resamples].sum(axis=1) / counts[resamples].sum(axis=1)
        scores[name]["gain_over_M0"] = {"mean": float(differences.mean()),
            "group_bootstrap_95": np.quantile(bootstrap, [.025, .975]).tolist()}
    return {"status": "evaluated", "n": len(rt_records), "groups": len(set(groups)),
            "singleton_subjects": sum(n == 1 for n in Counter(subjects).values()),
            "subject_count": len(set(subjects)),
            "models": scores, "diagnostics": diagnostics,
            "uncertainty": "500 held-out-group bootstrap resamples; fitted models fixed, not refitted per resample"}


def accuracy_evaluation(records, models, regime, fold_count=3):
    records = [r for r in records if r["participant_eligible"]]
    assignments, _ = folds(records, regime, count=fold_count)
    y = np.asarray([r["correct"] for r in records])
    results = {}
    for name in models:
        matrix, predictions, converged = design(records, MODELS[name]), np.zeros(len(y)), []
        for fold in range(fold_count):
            train, test = assignments != fold, assignments == fold
            if not train.any() or not test.any():
                return {"status": "insufficient_groups"}
            x_train, x_test = standardize(matrix[train], matrix[test])
            predictions[test], ok = logistic(x_train, y[train], x_test)
            converged.append(ok)
        results[name] = {"brier": float(np.mean((predictions - y)**2)),
                         "mean_log_likelihood": float(np.mean(y * np.log(predictions) + (1-y) * np.log1p(-predictions))),
                         "converged_all_folds": all(converged)}
    return {"status": "evaluated", "n": len(y), "model": "regularized fixed-effects logistic companion", "models": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("build/hybrid/data"))
    parser.add_argument("--audit", type=Path, default=Path("build/hybrid/audit"))
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/comparison"))
    parser.add_argument("--regimes", nargs="+", choices=["family", "participant", "pattern"], default=["family", "participant", "pattern"])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    protocol = {"schema": 2, "seed": 20261028, "folds": 3, "memory_decay": .8,
                "models": MODELS, "outcome": "log RT, marginal-ML Gaussian crossed participant/item intercepts",
                "primary_metric": "held-out pointwise predictive log density",
                "regimes": args.regimes, "status": "exploratory reanalysis of published data; not preregistered",
                "frequency": "published raw lexical counts and independent EWT training POS counts, log1p; study intercepts absorb lexical corpus scaling constants",
                "tree_baseline": "declared bounded POS CFG, completed and right-frontier fragments; not gold trees"}
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    feature_path = args.output / "predictors.jsonl"
    records = build(args.data, args.audit)
    write_jsonl(feature_path, records)
    coverage = json.loads((args.audit / "coverage-summary.json").read_text())
    matched = set(coverage["fully_supported_matched_families"])
    cohorts = {"all": (records, ["M0", "M1", "M2", "M1-bigrams", "M1-trigrams"]),
               "ds_matched": ([r for r in records if r["family"] in matched], list(MODELS))}
    report = {"protocol": protocol, "coverage": coverage, "cohorts": {}}
    for cohort, (rows, models) in cohorts.items():
        report["cohorts"][cohort] = {}
        for regime in args.regimes:
            if not rows:
                result = {"status": "unsupported", "reason": "no fully supported matched families"}
            else:
                result = evaluate(rows, models, regime)
                result["accuracy"] = accuracy_evaluation(rows, models, regime)
            report["cohorts"][cohort][regime] = result
            (args.output / "comparison-report.json").write_text(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
