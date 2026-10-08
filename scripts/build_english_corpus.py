"""Harvest cited English fixtures, preserving unknown judgments as not_stated."""

import ast
import re
from pathlib import Path

from dylan.corpus import ROOT, write_rows
from dylan.workbench_api import EXAMPLES
from build_clitic_corpus import row

SOURCES = [
    "tests/test_native_semantics.py",
    "tests/test_native_negation.py",
    "tests/test_clause_embedding.py",
    "tests/test_relatives.py",
    "tests/test_dialogue_workbench.py",
    "tests/test_dynamicsyntax_parse.py",
    "tests/test_lexical_expansion.py",
    "tests/test_effect_trace.py",
    "src/dylan/workbench_api.py",
]


def sentence(value):
    return (
        isinstance(value, str)
        and bool(re.fullmatch(r"[A-Za-z][A-Za-z ,.'?!-]+[.?!]", value))
        and 2 <= len(value.split()) <= 20
    )


def tags(text):
    found = []
    # Fixture tagging, not a syntactic classifier: require a nominal head so
    # historical wh-question probes do not become relative-clause evidence.
    relative = re.search(r"\b(?:man|dog|woman|doctor|patient|stone) (?:who|which|that)\b", text)
    if relative:
        found.append("relative_obj" if re.search(r"\b(?:who|which|that) (?:john|mary|bill)\b", text)
                     else "relative_subj")
    if re.search(r"\b(?:john|mary|bill)\b", text):
        found.append("name")
    if ("that" in text.split() and not relative) or "thinks" in text or "says" in text:
        found.append("complement")
    if text.startswith("every "):
        found.append("universal_subj")
    if "every " in text[6:]:
        found.append("universal_obj")
    if re.search(r"\b(?:a|an)\b", text):
        found.append("indefinite")
    if re.search(r"\b(?:black|red|blue|yellow|green|grey)\b", text):
        found.append("adjective")
    if "quickly" in text:
        found.append("adverb")
    if "not" in text.split():
        found.append("negation")
    if text.endswith("?"):
        found.append("yes_no")
    return found or ["name"]


def main():
    rows, seen = [], set()
    identities = set()
    for relative in SOURCES:
        tree = ast.parse((ROOT / relative).read_text())
        positive = {}
        negative = set()
        for node in ast.walk(tree):
            # These tables explicitly assert a complete parse and its meaning.
            if isinstance(node, ast.FunctionDef) and node.name in {
                "test_constructive_composition_and_real_coq_export",
                "test_recursive_composition",
                "test_constructive_closure_is_local_and_typechecks",
                "test_do_support_negates_the_local_clause",
                "test_relative_meanings_and_coq",
            }:
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and len(decorator.args) > 1
                        and isinstance(decorator.args[1], ast.List)
                    ):
                        for item in decorator.args[1].elts:
                            if (
                                isinstance(item, ast.Tuple)
                                and len(item.elts) > 1
                                and all(isinstance(x, ast.Constant) for x in item.elts[:2])
                            ):
                                text, meaning = (x.value for x in item.elts[:2])
                                if sentence(text):
                                    positive[text] = meaning
            if isinstance(node, ast.FunctionDef) and node.name == "test_relative_gap_controls":
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and len(decorator.args) > 1
                            and isinstance(decorator.args[1], ast.List)):
                        negative.update(item.value for item in decorator.args[1].elts
                                        if isinstance(item, ast.Constant) and sentence(item.value))
        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
                name = (
                    node.func.id
                    if isinstance(node.func, ast.Name)
                    else node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else ""
                )
                if name in {"parse", "run", "_parse"} and sentence(node.args[0].value):
                    candidates.append(node.args[0])
            if (
                isinstance(node, ast.Tuple)
                and node.elts
                and isinstance(node.elts[0], ast.Constant)
                and sentence(node.elts[0].value)
            ):
                candidates.append(node.elts[0])
        for node in ast.walk(tree):
            if isinstance(node, ast.List):
                candidates.extend(
                    item
                    for item in node.elts
                    if isinstance(item, ast.Constant) and sentence(item.value)
                )
        for node in candidates:
            text = node.value
            if text in seen:
                continue
            seen.add(text)
            native = relative != "tests/test_dynamicsyntax_parse.py"
            identity = f"english:{Path(relative).stem}:{node.lineno}"
            if identity in identities:
                identity += f":col-{node.col_offset}"
            identities.add(identity)
            item = row(
                identity,
                {"file": relative, "label": f"line-{node.lineno}", "line": node.lineno},
                text,
                "licensed" if text in positive else "not_stated",
                "english",
                tags=tags(text),
                notes="Regression fixture; a parser-failure assertion is not a grammaticality judgment.",
            )
            item["grammars"] = (
                ["2026-english-mltt", "2026-english-classical"] if native else ["2015-english-ttr"]
            )
            if text in positive:
                # Stable lexical predicates are meaningful across the two semantic modes.
                predicates = sorted(set(re.findall(r"\b([a-z]+)\(", positive[text])))
                item["expected"]["semantics_substrings"] = [p + "(" for p in predicates]
                item["expected"].update(ok=True, complete=True)
            if text in negative:
                item["expected"].update(ok=False, complete=False)
                item["notes"] += " Explicit gap-control rejection; includes unsupported English constructions."
            rows.append(item)
    lines = (ROOT / "src/dylan/workbench_api.py").read_text().splitlines()
    for n, example in enumerate(EXAMPLES):
        text = example["sentence"]
        line = next(i for i, s in enumerate(lines, 1) if text in s)
        item = row(
            f"english:ttr-starter:{n}",
            {"file": "src/dylan/workbench_api.py", "label": "EXAMPLES", "line": line},
            text,
            "licensed",
            "english",
            tags=tags(text),
        )
        item["grammars"] = ["2015-english-ttr"]
        item["expected"].update(ok=True, complete=True)
        rows.append(item)
    audit = ROOT / "docs/design/engine-requirements-2026-09-27.md"
    line, probe = next(
        (i, text)
        for i, text in enumerate(audit.read_text().splitlines(), 1)
        if text.startswith("Probe runs")
    )
    for grammar, segment in [
        (
            "2015-english-ttr",
            probe.split("2015-english-ttr accepted", 1)[1].split("resources/2026", 1)[0],
        ),
        ("2015-english-ttr-robot", probe.split("2015-english-ttr-robot accepted", 1)[1]),
    ]:
        for n, surface in enumerate(re.findall(r"`([^`]+)`", segment)):
            if len(surface.split()) < 2 or not re.fullmatch(r"[a-z .?!]+", surface):
                continue
            item = row(
                f"english:audit:{grammar}:{n}",
                {"file": str(audit.relative_to(ROOT)), "label": "probe-runs", "line": line},
                surface,
                "not_stated",
                "english",
                tags=tags(surface),
                notes="Historical parser probe, not an independent grammaticality judgment.",
            )
            item["grammars"] = [grammar]
            rows.append(item)
    path = ROOT / "data/BabyDS/class1_train_100.txt"
    for line, text in enumerate(path.read_text().splitlines(), 1):
        if not text.startswith("GoldSent"):
            continue
        text = text.split(":", 1)[1].strip()
        item = row(
            f"english:babyds:{line}",
            {"file": str(path.relative_to(ROOT)), "label": "GoldSent", "line": line},
            text,
            "licensed",
            "english",
            tags=["imperative"]
            + (["definite"] if " the " in text else ["indefinite"])
            + (
                ["adjective"]
                if any(c in text.split() for c in ["red", "blue", "green", "yellow", "grey"])
                else []
            ),
            notes="Gold utterance from the BabyDS training corpus; grammaticality is not inferred from this parser.",
        )
        item["grammars"] = ["2015-english-ttr-robot"]
        rows.append(item)
    write_rows(ROOT / "data/english/corpus.jsonl", rows)
    print(
        f"{len(rows)} English rows; {sum(r['judgment']['status'] == 'not_stated' for r in rows)} with no independent judgment"
    )


if __name__ == "__main__":
    main()
