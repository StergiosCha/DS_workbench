"""Controlled comparisons and explicit synthetic recovery; optional research dependencies."""

import argparse
from collections import defaultdict
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from dylan.experiments.contracts import Configuration, digest
from dylan.experiments.measurement import Measurement
from dylan.experiments.study import prepare, prototype, replay_schedule
from dylan.hybrid.mixed_model import fit, log_density


def configurations(study):
    return [Configuration(grammar=g, memory=m, measurement=o, representation=study["representation"], decay=study["decay"])
            for g, m, o in itertools.product(study["grammars"], study["memories"], study["measurements"])]


def label(config):
    return "/".join((config.grammar, config.memory, config.measurement))


def feature_rows(study, prepared, participants):
    rows = {}
    for grammar, memory in itertools.product(study["grammars"], study["memories"]):
        config = Configuration(grammar=grammar, memory=memory, representation=study["representation"], decay=study["decay"])
        rows[grammar, memory] = [row for participant in participants
                                for row in replay_schedule(study, participant, config, prepared[grammar])]
    return rows


def simulate(rows, config, *, seed=20261029):
    """Known generative parameters; output can never masquerade as human data."""
    rng = np.random.default_rng(seed)
    subjects = {p: rng.normal(0, .12) for p in sorted({r["participant"] for r in rows})}
    items = {f: rng.normal(0, .08) for f in sorted({r["family"] for r in rows})}
    shift = Measurement(config.measurement).shift
    responses = []
    for row in rows:
        if row["activation"] is None:
            continue
        mu = np.log(.9) - .3 * row["activation"] + .001 * row["order"]
        rt = shift + np.exp(mu + subjects[row["participant"]] + items[row["family"]] + rng.normal(0, .18))
        responses.append({"participant": row["participant"], "family": row["family"], "rt_seconds": float(rt),
                          "data_kind": "synthetic"})
    return responses


def design(rows):
    # Condition, lag, their interaction and exposure order are shared controls.
    # The activation column is the only representational/model-specific input.
    return np.array([[1., r["order"], r["lag"], float(r["condition"] == "matched"),
                      r["lag"] * float(r["condition"] == "matched"), r["activation"]] for r in rows])


def standardize(train, test):
    center, scale = train.mean(axis=0), train.std(axis=0)
    keep = scale > 1e-10
    keep[0] = True
    center[0], scale[0] = 0., 1.
    return (train[:, keep] - center[keep]) / scale[keep], (test[:, keep] - center[keep]) / scale[keep]


def rt_log_density(rt, mean, variance, shift=0.):
    transformed = np.log(np.asarray(rt) - shift)
    return log_density(transformed, mean, variance) - transformed


def compare(study, prepared_rows, coverage, responses, *, data_kind, seed=20261029):
    if data_kind not in {"synthetic", "human", "rehearsal"}:
        raise ValueError("Response provenance is required")
    if any(r.get("data_kind") != data_kind for r in responses):
        raise ValueError("Mixed or inconsistent response provenance")
    lookup = {(r["participant"], r["family"]): r for r in responses}
    if len(lookup) != len(responses):
        raise ValueError("Duplicate participant/family responses")
    # All configurations see the same eligible rows, including identical
    # outcome-domain exclusions for the two measurement functions.
    common = set(coverage["common_families"])
    reference = next(iter(prepared_rows.values()))
    identities = [(r["participant"], r["family"], r["order"]) for r in reference]
    if any([(r["participant"], r["family"], r["order"]) for r in values] != identities
           for values in prepared_rows.values()):
        raise ValueError("Configuration observations are not aligned")
    if set(lookup) - {(r["participant"], r["family"]) for r in reference}:
        raise ValueError("Responses contain observations outside the design")
    kept, excluded = [], defaultdict(int)
    for i, row in enumerate(reference):
        response = lookup.get((row["participant"], row["family"]))
        reason = "unsupported_family" if row["family"] not in common else "missing_response" if response is None else None
        if reason is None:
            rt = response["rt_seconds"]
            if type(rt) not in {int, float} or not np.isfinite(rt) or rt <= .15:
                reason = "outside_common_rt_domain"
        if reason:
            excluded[reason] += 1
        else:
            kept.append(i)
    rows = [reference[i] for i in kept]
    participants = sorted({r["participant"] for r in rows}, key=lambda p: hashlib.sha256(f"{seed}:{p}".encode()).hexdigest())
    report = {"data_kind": data_kind, "n": len(rows), "participants": len(participants),
              "families": len({r["family"] for r in rows}), "exclusions": dict(excluded),
              "split": "3 folds holding out whole participants; lexical families shared",
              "metric": "predictive log density on RT in seconds, including transform Jacobian",
              "status": "evaluated", "models": {}}
    if len(participants) < 6 or report["families"] < 6:
        report["status"] = "insufficient_independent_groups"
        return report
    assignment = {p: i % 3 for i, p in enumerate(participants)}
    folds = np.array([assignment[r["participant"]] for r in rows])
    rt = np.array([lookup[r["participant"], r["family"]]["rt_seconds"] for r in rows])
    subjects = np.array([str(r["participant"]) for r in rows])
    items = np.array([r["family"] for r in rows])
    predictions, designs, fit_cache = {}, {}, {}
    for config in configurations(study):
        selected = [prepared_rows[config.grammar, config.memory][i] for i in kept]
        x = design(selected)
        key = label(config)
        shift = Measurement(config.measurement).shift
        y = np.log(rt - shift)
        densities, means = np.zeros(len(rows)), np.zeros(len(rows))
        diagnostics = []
        for fold in range(3):
            train, test = folds != fold, folds == fold
            x_train, x_test = standardize(x[train], x[test])
            fit_key = (shift, fold, digest(x_train.tolist()), digest(x_test.tolist()))
            if fit_key not in fit_cache:
                fitted = fit(x_train, y[train], subjects[train], items[train])
                mu, variance = fitted.predict(x_test, subjects[test], items[test])
                fit_cache[fit_key] = (fitted, mu, variance)
            fitted, mu, variance = fit_cache[fit_key]
            densities[test] = rt_log_density(rt[test], mu, variance, shift)
            means[test] = shift + np.exp(mu + variance / 2)
            diagnostics.append({"fold": fold, "train": int(train.sum()), "test": int(test.sum()),
                "rank": int(np.linalg.matrix_rank(x_train)), "columns": x_train.shape[1],
                "converged": fitted.converged, "message": fitted.message,
                "residual_variance": fitted.residual_variance, "group_variances": list(fitted.group_variances)})
        report["models"][key] = {"configuration": config.to_dict(), "mean_log_density": float(densities.mean()),
                                 "rmse_ms": float(np.sqrt(np.mean((rt - means)**2)) * 1000),
                                 "converged": all(d["converged"] for d in diagnostics), "diagnostics": diagnostics}
        predictions[key], designs[key] = densities, (shift, digest(x.tolist()))
    baseline = label(Configuration(grammar=study["grammars"][0], memory="none-v1"))
    indices = [np.flatnonzero(subjects == str(p)) for p in participants]
    rng = np.random.default_rng(seed)
    bootstrap_indices = rng.integers(0, len(indices), size=(300, len(indices)))
    for name, values in predictions.items():
        differences = values - predictions[baseline]
        sums = np.array([differences[idx].sum() for idx in indices])
        counts = np.array([len(idx) for idx in indices])
        draws = sums[bootstrap_indices].sum(axis=1) / counts[bootstrap_indices].sum(axis=1)
        report["models"][name]["gain_over_baseline"] = {"mean": float(differences.mean()),
                                                         "interval_95": np.quantile(draws, [.025, .975]).tolist()}
    equivalent = defaultdict(list)
    for key, value in designs.items():
        equivalent[value].append(key)
    report["identical_design_groups"] = [group for group in equivalent.values() if len(group) > 1]
    report["baseline"] = baseline
    report["uncertainty"] = "300 participant bootstrap resamples of fixed held-out predictions; no refitting per draw"
    report["interpretation"] = "Synthetic recovery cannot establish human predictive adequacy" if data_kind == "synthetic" else "Exploratory response comparison; stimulus review and sampling limits still apply"
    return report


def run_pilot(output, *, participants=36, repetitions=3):
    if not 6 <= participants <= 500 or not 1 <= repetitions <= 20:
        raise ValueError("Recovery bounds: 6–500 participants, 1–20 repetitions")
    output.mkdir(parents=True, exist_ok=True)
    study = prototype()
    prepared, coverage = prepare(study)
    _, legacy = prepare(study, grammars=["ccg-original-v1"])
    sources = list(Path(__file__).parent.glob("*.py"))
    sources.append(Path(__file__).parent.parent / "__init__.py")
    sources.append(Path(__file__).parent.parent / "parser" / "__init__.py")
    sources += [Path(__file__).parent.parent / "hybrid" / name
                for name in ("mixed_model.py", "ccg.py", "terms.py", "traces.py")]
    # Freeze the full protocol before generating outcomes or fitting anything.
    protocol = {"schema": 1, "study": study, "study_sha256": digest(study),
                "configurations": [c.to_dict() for c in configurations(study)],
                "participants_per_simulation": participants, "recovery_repetitions": repetitions,
                "provenance": "synthetic design pilot; not preregistered, not a human experiment",
                "software_sha256": {str(p.relative_to(Path(__file__).parent.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sources},
                "grammar_fingerprints": {g: {k: v for k, v in next(iter(analyses.values())).provenance.items()
                                              if k.endswith("sha256")} for g, analyses in prepared.items()},
                "parameters": {"intercept": "log(.9)", "activation_slope": -.3, "order_slope": .001,
                               "subject_sd": .12, "item_sd": .08, "residual_sd": .18}}
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    rows = feature_rows(study, prepared, list(range(participants)))
    truths = [Configuration(grammar="ds-english-v1", memory="exponential-v1"),
              Configuration(grammar="ccg-incremental-v1", memory="count-v1"),
              Configuration(grammar="ccg-incremental-v1", memory="exponential-v1", measurement="shifted-lognormal-v1")]
    recovery, primary = [], None
    for truth in truths:
        for repetition in range(repetitions):
            seed = study["seed"] + repetition
            responses = simulate(rows[truth.grammar, truth.memory], truth, seed=seed)
            result = compare(study, rows, coverage, responses, data_kind="synthetic", seed=seed)
            run_file = f"recovery-{truth.grammar}-{truth.memory}-{truth.measurement}-{repetition}.json"
            (output / run_file).write_text(json.dumps(result, indent=2, allow_nan=False))
            if primary is None:
                primary = result
                (output / "synthetic-responses.json").write_text(json.dumps(responses))
            if result["status"] == "evaluated":
                eligible = [k for k, v in result["models"].items() if v["converged"]]
                if not eligible:
                    recovery.append({"generator": label(truth), "repetition": repetition,
                                     "status": "no_converged_models", "best": [], "report": run_file})
                    continue
                ranked = sorted(eligible, key=lambda k: result["models"][k]["mean_log_density"], reverse=True)
                best = result["models"][ranked[0]]["mean_log_density"]
                tied = [k for k in ranked if best - result["models"][k]["mean_log_density"] < 1e-6]
                recovery.append({"generator": label(truth), "repetition": repetition, "seed": seed, "best": tied,
                    "status": "evaluated", "report": run_file, "report_sha256": digest(result),
                    "nonconverged": [k for k, v in result["models"].items() if not v["converged"]],
                    "generator_converged": result["models"][label(truth)]["converged"],
                    "generator_gain_from_best": result["models"][label(truth)]["mean_log_density"] - best,
                    "all_fits_converged": all(v["converged"] for v in result["models"].values())})
            print(f"Recovery {label(truth)} repetition {repetition + 1}: {result['status']}", flush=True)
    report = {"schema": 1, "date": "2026-10-29", "status": "synthetic_design_pilot", "protocol": protocol,
              "coverage": coverage, "legacy_ccg_coverage": legacy, "comparison": primary, "recovery": recovery,
              "limitations": ["No newly collected human responses", "Authored stimuli lack independent review",
                "Memory features predict RT through a fitted observation model; no mechanistic latency claim",
                "Reference grammars are bounded implementation fragments", "Model recovery is assessed only on this small design",
                "Boundary, POS and length covary in the two prime conditions", "Shared item families limit generalization claims",
                "All items are intended positive; independent negative controls are still needed",
                "DS cues exclude context-only actions; CCG cues include the supplied context in full-span derivations",
                "Non-converged fits are reported but excluded from recovery winners; small score gaps do not establish identification"]}
    report["recovery_summary"] = {"exact_generator_best": sum(r["generator"] in r["best"] for r in recovery),
                                  "runs": len(recovery), "interpretation": "Descriptive recovery on this design only; no power or human superiority claim"}
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/experiments/pilot"))
    parser.add_argument("--participants", type=int, default=36)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--export", type=Path, help="Write aggregate report and frozen study for the local UI")
    args = parser.parse_args()
    report = run_pilot(args.output, participants=args.participants, repetitions=args.repetitions)
    if args.export:
        args.export.mkdir(parents=True, exist_ok=True)
        (args.export / "pilot-report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
        (args.export / "study-v1.json").write_text(json.dumps(report["protocol"]["study"], ensure_ascii=False, indent=2))
    print(json.dumps({"status": report["status"], "common_families": len(report["coverage"]["common_families"]),
                      "recovery_runs": len(report["recovery"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
