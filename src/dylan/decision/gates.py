"""Versioned calibration evidence for opt-in live ordering."""

import hashlib
import json
import os
from pathlib import Path


def family_hash(idea):
    filename = {1: "entry_v1.py", 2: "fanout_v1.py", 9: "triage_v1.py"}[idea]
    root = Path(__file__).parent
    return hashlib.sha256((root / "questions" / filename).read_bytes()
                          + (root / "state.py").read_bytes()
                          + (root / "ranking.py").read_bytes()
                          + (root / "client.py").read_bytes()).hexdigest()


def grammar_hash(grammar):
    from dynamicsyntax._session import resolved_grammar_path

    digest = hashlib.sha256()
    with resolved_grammar_path(grammar) as root:
        for path in sorted(Path(root).iterdir()):
            if path.suffix in {".txt", ".json"}:
                digest.update(path.name.encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def gate_path():
    return Path(os.getenv("DS_DECISION_GATES", ".ds-workbench/decision/calibration.json"))


def qualifies(evidence, idea):
    """Agreement alone does not justify adding network latency to DS search."""
    if (evidence.get("parity") is not True or evidence.get("backtracks_reduced") is not True
            or evidence.get("missing", 0) or evidence.get("replay_hits", 0) == 0):
        return False
    if idea == 1:
        return evidence.get("n", 0) >= 40 and evidence.get("agreement", 0) >= 0.85
    if idea == 2:
        return evidence.get("n", 0) >= 30 and evidence.get("gain", 0) >= 0.10
    return False


def evaluation_summary(grammar, model, provider):
    """Expose current aggregate evidence, without prompts or sentence text."""
    try:
        report = json.loads(gate_path().with_name("evaluation.json").read_text())
        if not isinstance(report, dict):
            return {}
        families = {}
        for idea in (1, 2):
            row = report.get(f"{grammar}:{idea}", {})
            if (isinstance(row, dict) and row.get("model") == model and row.get("provider") == provider
                    and row.get("family_hash") == family_hash(idea)
                    and row.get("grammar_hash") == grammar_hash(grammar)):
                families[str(idea)] = {key: row[key] for key in (
                    "n", "agreement", "gain", "parity", "baseline_backtracks", "replay_backtracks", "eligible")}
        return families
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def measured_gate(grammar, idea, model, provider="typesafe"):
    try:
        document = json.loads(gate_path().read_text())
        if not isinstance(document, dict):
            return False
        evidence = document.get(f"{grammar}:{idea}", {})
        if not isinstance(evidence, dict):
            return False
        if (evidence.get("model") != model or evidence.get("provider") != provider
                or evidence.get("family_hash") != family_hash(idea)
                or evidence.get("grammar_hash") != grammar_hash(grammar)):
            return False
        return qualifies(evidence, idea)
    except (OSError, ValueError, KeyError, TypeError):
        return False
