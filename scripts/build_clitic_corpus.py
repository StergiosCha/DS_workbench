"""Build cited clitic rows without deriving judgments from parser outcomes.

The PDF extractor only admits complete three-line example/gloss/translation
blocks. Ambiguous notation is queued for review instead of guessed.
"""

import argparse
import hashlib
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from dylan.corpus import ROOT, write_rows
from dylan.greek_workbench import CASES

PDF = Path("/Users/graogro/Dropbox/chatzikyriakidis-phdthesis.pdf")
TEX = Path("/Users/graogro/Dropbox/TEX/benjaminsvolume.tex")


def ascii_form(text):
    text = text.translate(
        str.maketrans(
            {
                "γ": "g",
                "Γ": "g",
                "δ": "d",
                "∆": "d",
                "Δ": "d",
                "θ": "th",
                "Θ": "th",
                "χ": "ch",
                "Σ": "s",
                "æ": "ae",
            }
        )
    )
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    ).lower()


def grammars(dialect, extended=None):
    code = extended or dialect
    return (
        [f"2026-{code}-{b}" for b in ("mltt", "classical")]
        if code in {"smg", "cypriot", "pontic", "grico"}
        else [f"2026-{code}-mltt"]
    )


def row(
    identity,
    source,
    surface,
    status,
    dialect,
    *,
    extended=None,
    tags=None,
    gloss="",
    notes="",
    expected=None,
):
    return {
        "id": identity,
        "source": source,
        "surface": surface,
        "ascii": ascii_form(surface),
        "dialect": dialect,
        "dialect_extended": extended,
        "environment": "not_stated",
        "environment_extended": None,
        "phenomena": sorted(set(tags or ["placement"])),
        "gloss": gloss,
        "judgment": {"status": status, "source": dict(source)},
        "expected": expected
        or {
            "ok": None,
            "complete": None,
            "failure_kind": None,
            "semantics_substrings": [],
            "coq_compiles": None,
        },
        "executable": None,
        "human_labels": {"annotator": None, "date": None},
        "model_labels": None,
        "notes": notes,
        "grammars": grammars(dialect, extended),
    }


def cases_rows():
    source_path = ROOT / "src/dylan/greek_workbench.py"
    lines = source_path.read_text().splitlines()
    for case in CASES:
        line = next(i for i, s in enumerate(lines, 1) if f'"id": "{case["id"]}"' in s)
        for field, status in [
            ("sentence", "licensed"),
            ("reverse", "starred"),
            ("ascii", "licensed"),
            ("reverse_ascii", "starred"),
        ]:
            item = row(
                f"cases:{case['id']}:{field}",
                {"file": "src/dylan/greek_workbench.py", "label": case["id"], "line": line},
                case[field],
                status,
                case["dialect"],
                tags=[
                    "placement",
                    {
                        "finite": "placement",
                        "negation": "negation",
                        "imperative": "imperative",
                        "na": "na",
                    }.get(case["environment"], case["environment"]),
                ],
                gloss=case["gloss"],
                notes="Adapted illustration of the cited placement pattern; see CASES source note.",
                expected={
                    "ok": status == "licensed",
                    "complete": status == "licensed",
                    "failure_kind": None if status == "licensed" else "constraint_violation",
                    "semantics_substrings": [],
                    "coq_compiles": None,
                },
            )
            item["environment"] = case["environment"]
            yield item


def expand_positions(surface):
    """Expand an explicitly forbidden optional position, moving the same clitic.

    Never create a doubled clitic by retaining both positions. Mismatched forms
    and slash alternatives require human transcription and return no variants.
    """
    whole_star = surface.startswith("*")
    base = surface[1:] if whole_star else surface
    if (
        "/" in base
        or "#" in base
        or "?" in base[:-1]
        or re.search(r"\([^)]*[^a-zA-ZγδθΓ∆Θ\s*][^)]*\)", base)
    ):
        return []
    marked = list(re.finditer(r"\(\*([A-Za-zγδθΓ∆Θ]+)\)", base))
    if marked:
        clean = re.sub(r"\(\*[^)]+\)", "", base)
        clean = re.sub(r"\(([A-Za-zγδθΓ∆Θ]+)\)", r"\1", clean)
        variants = [(" ".join(clean.split()), "starred" if whole_star else "licensed")]
        for mark in marked:
            token = mark[1]
            before, after = base[: mark.start()], base[mark.end() :]
            before = re.sub(r"\(\*[^)]+\)", "", before)
            after = re.sub(r"\(\*[^)]+\)", "", after)
            before = re.sub(r"\(([A-Za-zγδθΓ∆Θ]+)\)", r"\1", before)
            after = re.sub(r"\(([A-Za-zγδθΓ∆Θ]+)\)", r"\1", after)
            pattern = re.compile(r"\b" + re.escape(token) + r"\b", re.I)
            if len(pattern.findall(before + " " + after)) != 1:
                return []
            moved = pattern.sub("", before) + " " + token + " " + pattern.sub("", after)
            variants.append((" ".join(moved.split()), "starred"))
        return variants
    # Embedded optional segments/alternatives are preserved in the review queue.
    if any(c in base for c in "()*"):
        return []
    return [(" ".join(base.split()), "starred" if whole_star else "licensed")]


def thesis_rows(pdf):
    queued, rows = [], []
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "thesis.txt"
        subprocess.run(["pdftotext", "-layout", str(pdf), str(output)], check=True)
        pages = output.read_text().split("\f")
    for page_no, page in enumerate(pages, 1):
        lines = page.splitlines()
        for i, line in enumerate(lines[:-2]):
            match = re.match(r"\s*\(([2-6]\.\d+)\)\s+(.+)", line)
            if not match or not re.search(
                r"\b(?:CL|SG|PL|NOM|ACC|GEN|NEG|SUBJ|IMP|GER|INF|FUT|DAT)\b", lines[i + 1]
            ):
                continue
            if not lines[i + 2].strip().startswith(("‘", "'", "’", "“")):
                queued.append(
                    {
                        "label": match[1],
                        "page": page_no,
                        "reason": "multiline example needs transcription",
                        "excerpt": "\n".join(lines[i : i + 8]),
                    }
                )
                continue
            label, raw = match[1], " ".join(match[2].split())
            gloss, translation = lines[i + 1].strip(), lines[i + 2].strip()
            chapter, number = map(int, label.split("."))
            dialect, extended = (
                ("smg", None)
                if chapter in (2, 3, 6)
                else ("cypriot", None)
                if chapter == 4
                else ("pontic", None)
            )
            if (
                "GSG" in translation
                and "SMG" not in translation
                or chapter == 3
                and 130 <= number <= 134
            ):
                dialect, extended = "smg", "grico"
            elif "[CG]" in translation:
                dialect = "cypriot"
            elif (
                "[PG" in translation
                or chapter == 6
                and number in {*range(57, 64), *range(150, 160)}
            ):
                dialect = "pontic"
            for language in ("Spanish", "Italian", "French", "Catalan"):
                if language in translation:
                    dialect, extended = "not_stated", language.lower()
            if chapter == 3 and number in (76, 77):
                dialect = "mainland"
            if chapter == 3 and number in (113, 114):
                dialect, extended = "not_stated", "italian"
            if chapter == 6 and number in (40, 43):
                dialect, extended = "not_stated", "latin"
            if chapter == 6 and 133 <= number <= 149:
                dialect = "cypriot"
            if chapter == 6 and number in (111, 112):
                dialect, extended = "not_stated", "french"
            if chapter == 6 and number in (10, 63):
                dialect, extended = "pontic", "romeyka"
            variants = expand_positions(raw)
            if not variants:
                queued.append(
                    {
                        "label": label,
                        "page": page_no,
                        "reason": "ambiguous notation needs transcription",
                        "excerpt": "\n".join(lines[i : i + 3]),
                    }
                )
                continue
            tags = ["placement"]
            if chapter == 2:
                tags = (
                    ["svo"]
                    if number == 50
                    else ["vso"]
                    if number == 51
                    else ["relative"]
                    if number == 80
                    else ["htld"]
                    if number == 95
                    else ["dp_case"]
                )
            if "NEG" in gloss:
                tags.append("negation")
            if "SUBJ" in gloss:
                tags.append("na")
            if "IMP" in gloss.replace("I MP", "IMP"):
                tags.append("imperative")
            if "GER" in gloss:
                tags.append("gerund")
            if "NOM" in gloss or "the.ACC" in gloss:
                tags.append("dp_case")
            if len(re.findall(r"CL", gloss)) > 1:
                tags.append("cluster")
            if chapter == 6 and (number <= 12 or 51 <= number <= 63):
                tags.append("pcc")
            if chapter == 6 and 64 <= number <= 71:
                tags.append("ethical_dative")
            if "CLLD" in translation:
                tags.append("clld")
            if "HTLD" in translation:
                tags.append("htld")
            if "CD]" in translation:
                tags.append("doubling")
            if dialect == "mainland":
                tags.append("diachronic")
            for n, (surface, status) in enumerate(variants):
                source = {
                    "file": pdf.name,
                    "label": f"({label})",
                    "page": page_no,
                    "page_kind": "PDF page (1-based)",
                    "sha256": digest,
                }
                item = row(
                    f"thesis:{label}:{n}",
                    source,
                    surface,
                    status,
                    dialect,
                    extended=extended,
                    tags=tags,
                    gloss=gloss + " / " + translation,
                    notes="Mechanical source transcription; human review pending. Variety uses explicit example label where available, otherwise chapter context.",
                )
                item["source_excerpt"] = "\n".join(lines[i : i + 3])
                rows.append(item)
    return rows, queued


def detex(value):
    for name, symbol in [
        ("gamma", "γ"),
        ("Gamma", "Γ"),
        ("delta", "δ"),
        ("Delta", "∆"),
        ("theta", "θ"),
        ("Theta", "Θ"),
    ]:
        value = value.replace("\\" + name, symbol)
    value = re.sub(r"\\['=]\{([^}]+)\}", r"\1", value)
    value = re.sub(r"\\textsc\{([^}]+)\}", r"\1", value)
    return " ".join(value.replace("$", "").replace("{", "").replace("}", "").split())


def expanded_pontic_rows(pdf):
    """Explicitly expand the verb and final-n alternatives of thesis (6.57)."""
    source = {"file": pdf.name, "label": "(6.57)", "page": 282,
              "page_kind": "PDF page (1-based)",
              "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}
    for verb in ("Eδikse", "eδeknise"):
        for tail in ("ese", "esen"):
            yield row(
                f"thesis:6.57:{ascii_form(verb)}:{tail}", source,
                f"{verb} m {tail}", "licensed", "pontic",
                tags=["placement", "cluster", "pcc"],
                gloss="showed.3SG me.CL you.CL / S/he/it showed you to me.",
                notes=("Expanded from Eδikse/eδeknise m ese(n). The preceding prose "
                       "restricts this weak-PCC pattern to some Pontic speakers. "
                       "Human transcription review pending; tense semantics is absent."),
                expected={"ok": True, "complete": True, "failure_kind": None,
                          "semantics_substrings": ["show(pro, hearer, speaker)"],
                          "coq_compiles": True},
            )


def complete_intro_parses(rows, pdf):
    """Include the two p.57 examples whose translation is shared across lines."""
    by_id = {item["id"]: item for item in rows}
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    for number, surface, order, gloss in [
        ("2.50", "O Γiorγos xtipise to Γiani", "svo",
         "the.NOM George.NOM hit.3SG the.ACC John.ACC"),
        ("2.51", "Xtipise o Γiorγos to Γiani", "vso",
         "hit.3SG the.NOM George.NOM the.ACC John.ACC"),
    ]:
        identity = f"thesis:{number}:0"
        item = by_id.get(identity)
        if item is None:
            source = {"file": pdf.name, "label": f"({number})", "page": 57,
                      "page_kind": "PDF page (1-based)", "sha256": digest}
            item = row(identity, source, surface, "licensed", "smg", tags=["dp_case", order],
                       gloss=gloss + " / George hit John.",
                       notes=("The translation following (2.51) is shared with (2.50). "
                              "The accompanying p.57 analysis abstracts over determiner semantics. "
                              "Human transcription review pending."))
            item["source_excerpt"] = f"({number}) {surface}\n{gloss}\n‘George hit John’ [shared translation]"
            rows.append(item)
        # Retain existing source text, review metadata and explicit expectations.
        expected = item.setdefault("expected", {})
        for key, value in {"ok": True, "complete": True, "coq_compiles": True}.items():
            if expected.get(key) is None:
                expected[key] = value
        if not expected.get("semantics_substrings"):
            expected["semantics_substrings"] = ["hit(giorgos, giannis)"]
    return rows


def manuscript_rows(tex):
    rows, queued = [], []
    source = tex.read_text()
    pattern = re.compile(r"\\gll\s+([^\n]+)\n(.*?)\\gl(?:t|n)(.*?)\\glend", re.S)
    for n, match in enumerate(pattern.finditer(source), 1):
        line = source[: match.start()].count("\n") + 1
        raw, gloss, translation = map(detex, match.groups())
        dialect = (
            "smg"
            if line < 157
            else "cypriot"
            if line < 210
            else "pontic"
            if line < 235
            else "koine"
        )
        variants = expand_positions(raw)
        if not variants or "\\" in raw:
            queued.append(
                {
                    "line": line,
                    "reason": "TeX notation needs transcription",
                    "excerpt": match.group(0),
                }
            )
            continue
        for variant, (surface, status) in enumerate(variants):
            item = row(
                f"chapter:{line}:{variant}",
                {"file": tex.name, "label": f"gll-{n}", "line": line},
                surface,
                status,
                dialect,
                gloss=gloss + " / " + translation,
                tags=["placement"] + (["diachronic"] if dialect == "koine" else []),
                notes="Literal manuscript example; optional forbidden positions expanded without clitic doubling. Human review pending.",
            )
            item["source_excerpt"] = match.group(0)
            rows.append(item)
    return rows, queued


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=PDF)
    parser.add_argument("--manuscript", type=Path, default=TEX)
    args = parser.parse_args()
    rows = list(cases_rows())
    thesis, queue = thesis_rows(args.pdf)
    chapter, tex_queue = manuscript_rows(args.manuscript)
    diagnostics = [
        "το ζουζουνίζει μπλα.",
        "το τον ξέρω.",
        "ξέρω ξέρω.",
        "το γράφει.",
        "na grapse to.",
        "to grapsi.",
    ]
    source_lines = (ROOT / "tests/test_greek_workbench.py").read_text().splitlines()
    for n, surface in enumerate(diagnostics):
        line = next(i for i, text in enumerate(source_lines, 1) if surface in text)
        rows.append(
            row(
                f"diagnostic:{n}",
                {"file": "tests/test_greek_workbench.py", "label": "diagnostic", "line": line},
                surface,
                "not_stated",
                "smg",
                notes="Diagnostic fixture; no independent grammaticality judgment is asserted.",
            )
        )
    prose_lines = (ROOT / "docs/design/thesis-clitic-system.md").read_text().splitlines()
    for n, surface in enumerate(["exo to desi", "mi dos mu to", "to mu dosane"]):
        line = next(i for i, text in enumerate(prose_lines, 1) if surface in text)
        rows.append(
            row(
                f"prose:{n}",
                {
                    "file": "docs/design/thesis-clitic-system.md",
                    "label": "starred-prose",
                    "line": line,
                },
                surface,
                "starred",
                "smg",
                tags=["climbing"] if n == 0 else ["cluster"],
                notes="Whole starred string in the thesis extraction; abstract pattern labels and bare clusters are not treated as complete sentences.",
            )
        )
    rows.extend(chapter)
    rows.extend(thesis)
    rows.extend(expanded_pontic_rows(args.pdf))
    complete_intro_parses(rows, args.pdf)
    write_rows(ROOT / "data/greek-clitics/corpus.jsonl", rows)
    write_rows(ROOT / "data/greek-clitics/transcription_queue.jsonl", queue + tex_queue)
    print(
        f"{len(rows)} rows, {sum(r['judgment']['status'] == 'starred' for r in rows)} starred; {len(queue) + len(tex_queue)} source blocks queued for review"
    )


if __name__ == "__main__":
    main()
