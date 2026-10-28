"""Export an attributed, aggregate-only evidence snapshot for the research lab."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


LIMITATIONS = [
    "The original preprocessing is reproduced; posterior contrasts are recomputed from archived fitted draws, not newly fitted models.",
    "Our held-out comparisons are exploratory Gaussian models of log RT, not the paper's Bayesian shifted-lognormal model.",
    "The primary lexical-family comparison has uncertainty spanning zero for both full POS-sequence and CFG additions.",
    "The dictionary-expanded DS audit supports only two complete families (233 retained trials). It cannot support held-out-family or pattern comparisons.",
    "Every participant in that DS subset contributes one retained observation: participant and residual variances cannot be separately identified. Its fixed-effect designs are also rank deficient. Tiny score differences there are not evidence for an architecture.",
    "A fixed bank of 24 corpus prefixes and first-success bounded parsing are coverage probes, not a probability model of arbitrary English contexts.",
    "The CFG is a declared small POS grammar; DS action/state features are lossy projections. Neither is an exhaustive account of structural representation.",
    "Unrecognized earlier inputs contribute lexical/POS history but no DS features. DS structural recency therefore has incomplete history coverage.",
    "Bootstrap intervals resample held-out groups with fitted models fixed; they omit model-refitting and selection uncertainty.",
    "The main article abstract, supplement and public analysis materials were accessible; this work does not claim access to the subscription-only full article.",
]


def export(root, destination):
    paths = {
        "preprocessing": "data/preprocessing-report.json",
        "posterior": "reproduction/posterior-reproduction.json",
        "coverage_original": "audit/coverage-summary.json",
        "coverage_dictionary": "audit-dictionary/coverage-summary.json",
        "comparison": "comparison-final/comparison-report.json",
        "source_manifest": "sources/manifest.json",
        "context_bank": "data/contexts.json",
    }
    objects, hashes = {}, {}
    for name, relative in paths.items():
        raw = (root / relative).read_bytes()
        hashes[relative] = hashlib.sha256(raw).hexdigest()
        objects[name] = json.loads(raw)
    studies = objects["preprocessing"]["studies"]
    comparison = objects["comparison"]
    matched = set(objects["coverage_dictionary"]["fully_supported_matched_families"])
    cells = defaultdict(list)
    for line in (root / "comparison-final/predictors.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["included"] and row["family"] in matched:
            cells[(row["family"], row["condition"], row["prime"], row["target"])].append(row)
    examples = []
    for (family, condition, prime, target), rows in sorted(cells.items()):
        examples.append({"family": family, "condition": condition, "prime": prime, "target": target,
                         "pos_prime": rows[0]["pos_prime"], "pos_target": rows[0]["pos_target"],
                         "retained_trials": len(rows),
                         "human_mean_rt_ms": sum(row["rt_seconds"] for row in rows) / len(rows) * 1000,
                         "mean_features": {key: sum(row["features"][key] for row in rows) / len(rows)
                                           for key in ("pos2_overlap", "pos3_overlap", "tree_overlap", "action_overlap", "state_overlap")}})
    live = {}
    for name in ("jev", "llm"):
        path = root / "assistance" / f"live-{name}.json"
        if path.exists():
            record = json.loads(path.read_text())
            provider = record.get("provider", {})
            live[name] = {"status": record["status"],
                          "provider": provider.get("provider") or record.get("record", {}).get("provider"),
                          "model": provider.get("model") or record.get("record", {}).get("model"),
                          "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "scope": "one live integration check; not linguistic validation or calibration"}
    supported = root / "assistance/live-jev-supported-prefix.json"
    if supported.exists():
        record = json.loads(supported.read_text())
        live["jev_supported_prefix"] = {"status": record["status"], "prefix": record["record"]["state"].get("observed_prefix"),
            "prefix_status": record["record"]["state"]["prefix_status"], "model": record["record"]["model"],
            "artifact_sha256": hashlib.sha256(supported.read_bytes()).hexdigest(),
            "scope": "integration check; not a calibrated improvement claim"}
    parser_check = root / "assistance/live-parser-comparison.json"
    if parser_check.exists():
        live["parser_comparison"] = {"artifact_sha256": hashlib.sha256(parser_check.read_bytes()).hexdigest(), "runs": []}
        for record in json.loads(parser_check.read_text()):
            result = record["jev_comparison"]
            live["parser_comparison"]["runs"].append({"grammar": record["grammar"],
                "same_inventory": result["same_inventory"], "live_calls": result["live_calls"],
                "complete_without": result["without_jev"]["complete"], "complete_with": result["with_jev"]["complete"],
                "meaning_without": result["without_jev"]["meaning"], "meaning_with": result["with_jev"]["meaning"],
                "note": result["note"]})
    summary = {"schema": 1, "date": "2026-10-28", "status": "exploratory_research_snapshot",
        "article": {"authors": "Yngwie A. Nielsen & Morten H. Christiansen", "title": "Evidence for the representation of non-hierarchical structures in language",
                    "doi": "10.1038/s41562-025-02387-z", "url": "https://www.nature.com/articles/s41562-025-02387-z"},
        "sources": [
            {"name": "Authors' public project", "url": "https://osf.io/ymndq/", "license": "data CC BY 4.0; code MIT, per upstream license.txt"},
            {"name": "UD English EWT r2.15 training corpus", "url": "https://github.com/UniversalDependencies/UD_English-EWT/tree/r2.15", "license": "CC BY-SA 4.0"},
            {"name": "Kolliakou (2004), Monadic definites and polydefinites", "url": "https://doi.org/10.1017/S0022226704002531", "scope": "theoretical reference, not a claim to reproduce the full analysis"}],
        "participants": sum(s["participants"] for s in studies),
        "retained_trials": sum(s["included_pairs"] for s in studies),
        "preprocessing": objects["preprocessing"], "posterior": objects["posterior"],
        "coverage": {"original": objects["coverage_original"], "dictionary": objects["coverage_dictionary"]},
        "protocol": comparison["protocol"], "comparisons": comparison["cohorts"], "matched_examples": examples,
        "assistance_checks": live, "limitations": LIMITATIONS,
        "artifact_sha256": hashes,
        "context_protocol": {key: value for key, value in objects["context_bank"].items() if key != "contexts"},
        "code_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}}
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "source-manifest.json").write_bytes((root / "sources/manifest.json").read_bytes())
    (destination / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    lines = ["# Hybrid syntax evidence snapshot", "", "Exploratory reanalysis, 2026-10-28. Generated by `python -m dylan.hybrid.report`.", "",
             f"{summary['participants']} participants; {summary['retained_trials']} retained prime–target pairs. All four preprocessing checks match.", "",
             "## Archived posterior reproduction", "", "Contrasts below use saved posterior draws; intervals are 95% posterior intervals. Negative values mean faster experimental targets.", "",
             "| Study | Contrast | Median ms | 95% interval ms |", "|---|---|---:|---|" ]
    for study in summary["posterior"]["studies"]:
        for name, value in study["contrasts"].items():
            lines.append(f"| {study['study']} | {name} | {value['estimate_ms']:.2f} | [{value['lower_ms']:.2f}, {value['upper_ms']:.2f}] |")
    lines += ["", "## Primary held-out lexical-family comparison", "", "Mean predictive log-density gain over M0; 500 held-out-group bootstrap resamples. Not posterior evidence ratios.", "",
              "| Model | Gain | 95% interval |", "|---|---:|---|"]
    for name, value in summary["comparisons"]["all"]["family"]["models"].items():
        gain = value["gain_over_M0"]
        lines.append(f"| {name} | {gain['mean']:.6f} | [{gain['group_bootstrap_95'][0]:.6f}, {gain['group_bootstrap_95'][1]:.6f}] |")
    lines += ["", "## Interpretation and limits", "", *[f"- {limit}" for limit in LIMITATIONS], "", "## Sources", "",
              f"- [Nielsen & Christiansen]({summary['article']['url']}).", *[f"- [{s['name']}]({s['url']})." for s in summary["sources"]], "",
              "`summary.json` contains aggregate scores, diagnostics, artifact hashes and the protocol. `source-manifest.json` preserves downloaded member identities, CRCs, SHA256 values and upstream metadata; whole-archive hashes are not claimed verified. Raw participant observations and full traces remain in ignored `build/hybrid/`.", "",
              "The few stimulus strings and derived study aggregates reuse Nielsen and Christiansen's public data under CC BY 4.0; upstream code is MIT, per its license.txt. The independent UD EWT corpus is CC BY-SA 4.0. See the linked original sources for attribution and terms.", ""]
    (destination / "README.md").write_text("\n".join(lines))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("build/hybrid"))
    parser.add_argument("--output", type=Path, default=Path("data/hybrid"))
    args = parser.parse_args()
    result = export(args.root, args.output)
    print(json.dumps({"output": str(args.output), "participants": result["participants"], "trials": result["retained_trials"]}))


if __name__ == "__main__":
    main()
