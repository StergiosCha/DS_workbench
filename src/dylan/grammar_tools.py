"""Read-only grammar inventories, validation reports and source differences."""

from dataclasses import asdict
import difflib
import json
from pathlib import Path
import re

from loguru import logger
from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon, strip_block_comments
from dylan.tree.label.labels import generic_label_seen

FILES = (
    "computational-actions.txt",
    "lexical-actions.txt",
    "lexicon.txt",
    "lexical-macros.txt",
    "semantics.json",
)


def normalized(path):
    path = Path(path)
    if not path.exists():
        return []
    if path.suffix == ".json":
        return json.dumps(json.loads(path.read_text()), sort_keys=True, indent=2).splitlines()
    return [
        line.strip()
        for line in strip_block_comments(path.read_text().splitlines())
        if line is not None
    ]


def diff_grammars(left, right):
    result = []
    for name in FILES:
        result.extend(
            difflib.unified_diff(
                normalized(Path(left) / name),
                normalized(Path(right) / name),
                fromfile=f"{Path(left).name}/{name}",
                tofile=f"{Path(right).name}/{name}",
                lineterm="",
            )
        )
    return "\n".join(result)


def lint_grammar(path, results=None):
    path = Path(path)
    generic_label_seen.clear()
    warnings = []
    sink = logger.add(lambda message: warnings.append(message.record["message"]), level="WARNING")
    strict_errors = []
    try:
        for loader in (Lexicon, Grammar):
            try:
                loader(path, strict=True)
            except (ValueError, TypeError, RuntimeError) as exc:
                strict_errors.append(str(exc))
        lexicon = Lexicon(path)
        grammar = Grammar(path)
    finally:
        logger.remove(sink)
    undefined = {}
    arity = []
    for number, line in enumerate(
        strip_block_comments((path / "lexicon.txt").read_text().splitlines())
        if (path / "lexicon.txt").exists()
        else [],
        1,
    ):
        if not line or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        word, template, *params = parts
        if template not in lexicon._templates:
            undefined[template] = undefined.get(template, 0) + 1
        elif len(params) != lexicon._templates[template].metavar_count:
            arity.append(
                {
                    "line": number,
                    "word": word,
                    "template": template,
                    "expected": lexicon._templates[template].metavar_count,
                    "actual": len(params),
                }
            )
    source = "\n".join(
        (path / name).read_text()
        for name in ("lexicon.txt", "lexical-actions.txt")
        if (path / name).exists()
    )
    tokens = set(re.findall(r"[A-Za-z][\w]*", source))
    profile = (
        json.loads((path / "semantics.json").read_text())
        if (path / "semantics.json").exists()
        else {}
    )
    matching = [r for r in results or [] if r["grammar"] == path.name]
    used = {
        template
        for r in matching
        if r["ok"] and r["complete"]
        for template in r.get("templates", [])
    }
    return {
        "grammar": str(path),
        "load_stats": asdict(lexicon.load_stats),
        "strict_errors": strict_errors,
        "warnings": sorted(set(warnings)),
        "undefined_templates": undefined,
        "arity_failures": arity,
        "disabled_rules": grammar.disabled_rule_names,
        "generic_labels": sorted(generic_label_seen),
        "unused_predicates": sorted(set(profile.get("predicates", {})) - tokens),
        "dynamic_status": "measured" if matching else "unmeasured",
        "templates_not_seen_on_success": sorted(set(lexicon._templates) - used)
        if matching
        else None,
        "rules": sorted(grammar),
        "templates": sorted(lexicon._templates),
    }
