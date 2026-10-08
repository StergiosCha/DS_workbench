"""Validate sourced lexical candidates and merge only a reviewed content hash."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon


def candidate_hash(candidate):
    fields = {key: candidate.get(key) for key in ("grammar", "row", "source", "declarations")}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def prepare_candidates(candidates, grammar_root, *, include_pending=False):
    """Return validated replacement texts; no shipped file changes here."""
    grammar_root = Path(grammar_root).resolve()
    groups = defaultdict(list)
    seen = set()
    for candidate in candidates:
        if candidate["id"] in seen:
            raise ValueError(f"Duplicate candidate id: {candidate['id']}")
        seen.add(candidate["id"])
        source = candidate.get("source", {})
        if not source.get("file") or not any(k in source for k in ("line", "page")):
            raise ValueError("Candidate needs a source locator")
        review = candidate.get("review", {})
        approved = review.get("status") == "approved"
        if approved and (not review.get("reviewer") or review.get("hash") != candidate_hash(candidate)):
            raise ValueError("Approval is missing or does not match this candidate's content")
        if not approved and not include_pending:
            continue
        row = candidate["row"]
        if not row.strip() or "\n" in row or "\r" in row or "//" in row:
            raise ValueError("Candidate must contain one lexical row")
        directory = (grammar_root / candidate["grammar"]).resolve()
        if not directory.is_relative_to(grammar_root) or not directory.is_dir():
            raise ValueError("Candidate must target an existing grammar directory")
        groups[directory].append(candidate)
    replacements = {}
    for directory, entries in groups.items():
        lexical = (directory / "lexicon.txt").read_text()
        theory = json.loads((directory / "semantics.json").read_text())
        rows = set(line.strip() for line in lexical.splitlines())
        for candidate in entries:
            if candidate["row"] not in rows:
                lexical += candidate["row"] + "\n"
                rows.add(candidate["row"])
            for category, declarations in candidate.get("declarations", {}).items():
                if category not in {"constants", "predicates", "modifiers", "subtyping"}:
                    raise ValueError(f"Unsupported declaration category: {category}")
                destination = theory.setdefault(category, {})
                for symbol, value in declarations.items():
                    if symbol in destination and destination[symbol] != value:
                        raise ValueError(f"Conflicting declaration: {symbol}")
                    destination[symbol] = value
        semantic = json.dumps(theory, ensure_ascii=False, indent=2) + "\n"
        with tempfile.TemporaryDirectory(prefix="ds-lexicon-review-") as temporary:
            staged = Path(temporary) / "grammar"
            shutil.copytree(directory, staged)
            (staged / "lexicon.txt").write_text(lexical)
            (staged / "semantics.json").write_text(semantic)
            Lexicon(staged, strict=True)
            Grammar(staged, strict=True)
        replacements[directory / "lexicon.txt"] = lexical
        replacements[directory / "semantics.json"] = semantic
    return replacements
