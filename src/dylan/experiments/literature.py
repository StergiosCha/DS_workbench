"""Hash-verified importers for the selected literature battery.

Raw licensed materials stay in the ignored local cache. Imports preserve upstream
IDs, conditions, regions (including empty ones), punctuation and presentation
order. They define no tokenization, scoring denominator or task adapter, and
report source anomalies instead of repairing them.
"""

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from dylan.workbench_paths import WORKING_ROOT, data_path

MANIFEST = "experiments/literature-selection-v1.json"
CACHE = WORKING_ROOT / "build/experiments/literature"
# Local cache names; the manifest pins upstream identity and bytes.
FRACAS_FILE, FINE_FILE = "fracas-greek-current.xml", "fine-materials.docx"
LEVELS = ("section", "subsection", "subsubsection")
NOT_IMPORTED = {
    "nielsen_christiansen": "Reconstructed by the existing hybrid pipeline (dylan.hybrid.sources)",
    "davis_vanschijndel_2020": "Manifest pins the repository commit but no file hashes",
    "natural_stories": "Participant RT table not retrieved; corrected release still to be pinned",
    "dialogue": "Curation task; no normed source dataset",
    "blimp": "Supplementary regression; materials not retrieved or pinned",
}


class SourceError(ValueError):
    pass


def manifest():
    return json.loads(data_path(MANIFEST).read_text())


def verified(path, sha256, url=None, *, fetch=False):
    """Return cached bytes whose SHA-256 matches the manifest; optionally fetch first."""
    path = Path(path)
    if not path.exists() and fetch and url:
        from dylan.hybrid.sources import request

        payload = request(url)
        if hashlib.sha256(payload).hexdigest() != sha256:
            raise SourceError(f"{url} does not match the pinned SHA-256; nothing written")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    if not path.exists():
        raise SourceError(f"{path} is missing; retrieve {url or 'the pinned source'} into the local cache")
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != sha256:
        raise SourceError(f"{path} has SHA-256 {actual}; the manifest pins {sha256}")
    return payload


def _block(source, block_id):
    return next(b for b in source["additional_blocks"] if b["id"] == block_id)


def _text(value):
    # XML/docx layout whitespace only; characters, punctuation and typos are kept.
    return " ".join((value or "").split())


def _sentence(el, where, anomalies):
    """Field texts of one FraCaS sentence; text outside the fields is reported, not merged."""
    if el is None:
        raise SourceError(f"FraCaS {where}: element missing")
    if not len(el):
        return {"text": _text(el.text)}
    if len({c.tag for c in el}) != len(el):
        raise SourceError(f"FraCaS {where}: repeated field")
    stray = [("before the fields", el.text)] + [(f"after <{c.tag}>", c.tail) for c in el] \
        + [(f"nested in <{c.tag}>", "".join(c.itertext())[len(c.text or ""):]) for c in el]
    anomalies += [{"location": where, "issue": f"text {k}, kept out of the fields", "text": _text(t)}
                  for k, t in stray if _text(t)]
    return {c.tag: _text(c.text) for c in el}


def syntaxgym(suite_id, cache=CACHE, *, fetch=False, source=None):
    source = source or manifest()
    quarantined = {q["id"]: q["reason"] for q in source["quarantined"]}
    if suite_id in quarantined:
        raise SourceError(f"{suite_id} is quarantined: {quarantined[suite_id]}")
    core = source["core"]
    entry = next((s for s in core["suites"] if s["id"] == suite_id), None)
    if entry is None:
        raise SourceError(f"{suite_id} is not a selected SyntaxGym suite")
    raw = json.loads(verified(Path(cache) / f"{suite_id}.json", entry["sha256"], entry["url"], fetch=fetch))
    formulas = [p["formula"] for p in raw["predictions"]]
    if raw["region_meta"] != entry["region_metadata"] or formulas != [p["formula"] for p in entry["source_predictions"]]:
        raise SourceError(f"{suite_id}: region metadata or predictions differ from the manifest")
    references = {(int(r), c.strip()) for f in formulas for r, c in re.findall(r"\(\s*(\d+)\s*;\s*%([^%]+)%\s*\)", f)}
    families = []
    for item in raw["items"]:
        raw_conditions = item["conditions"]
        if len({c["condition_name"] for c in raw_conditions}) != len(raw_conditions) or any(
                [r["region_number"] for r in c["regions"]] != [int(k) for k in raw["region_meta"]] for c in raw_conditions):
            raise SourceError(f"{suite_id}:{item['item_number']}: duplicate conditions or irregular regions")
        conditions = [{"name": c["condition_name"], "regions": [
            {"number": r["region_number"], "label": raw["region_meta"][str(r["region_number"])], "content": r["content"]}
            for r in c["regions"]]} for c in raw_conditions]
        if not {c for _, c in references} <= {c["name"] for c in conditions}:
            raise SourceError(f"{suite_id}:{item['item_number']}: a prediction names a missing condition")
        families.append({"id": f"{suite_id}:{item['item_number']}", "item_number": item["item_number"],
                         "conditions": conditions})
    if len({f["id"] for f in families}) != len(families) or len(families) != entry["families"] \
            or sum(len(f["conditions"]) for f in families) != entry["condition_sentences"]:
        raise SourceError(f"{suite_id}: item IDs or counts differ from the manifest")
    return {"source": {"block": "syntaxgym", "id": suite_id, "repository": core["repository"],
                       "commit": core["commit"], "url": entry["url"], "sha256": entry["sha256"],
                       "license": core["upstream_license"], "paper": core["paper"]},
            "phenomenon": entry["phenomenon"], "outcomes": entry["outcomes"],
            "meta": raw["meta"],  # comments record the authors' alternative criteria
            "region_meta": raw["region_meta"], "predictions": raw["predictions"],
            "critical_regions": sorted({r for r, _ in references}), "families": families}


def fracas(cache=CACHE, *, source=None):
    entry = _block(source or manifest(), "fracas")
    root = ET.fromstring(verified(Path(cache) / FRACAS_FILE, entry["greek_sha256"]))
    heading, comments, problems, anomalies = {}, [], [], []
    for node in root:
        level = node.get("class")
        if node.tag == "comment" and level in LEVELS:
            heading = {k: heading[k] for k in LEVELS[:LEVELS.index(level)] if k in heading} | {level: _text(node.text)}
        elif node.tag == "comment" and level is None:
            comments.append(_text(node.text))
        elif node.tag == "problem":
            pid, premises = node.get("id"), node.findall("p")
            if [p.get("idx") for p in premises] != [str(i) for i in range(1, len(premises) + 1)]:
                raise SourceError(f"FraCaS {pid}: premise indices are not consecutive")
            if {c.tag for c in node} - {"p", "q", "h", "a", "note", "why"}:
                raise SourceError(f"FraCaS {pid}: unexpected element")
            problems.append({"id": pid, "fracas_answer": node.get("fracas_answer"),
                             "fracas_nonstandard": node.get("fracas_nonstandard") == "true",
                             "language": node.get("language"), **heading, "preceding_comments": comments,
                             "premises": [_sentence(p, f"{pid}/p{p.get('idx')}", anomalies) for p in premises],
                             **{k: _sentence(node.find(t), f"{pid}/{t}", anomalies)
                                for k, t in (("question", "q"), ("hypothesis", "h"), ("answer", "a"))},
                             "notes": [_text(n.text) for n in node.findall("note")],
                             "why": [_text(n.text) for n in node.findall("why")]})
            comments = []
    if len(problems) != entry["greek_problem_records_verified"] or len({p["id"] for p in problems}) != len(problems):
        raise SourceError("FraCaS problem IDs or count differ from the manifest")
    return {"source": {"block": "fracas", "id": "fracas_greek", "file": entry["greek_file"],
                       "commit": entry["commit"], "sha256": entry["greek_sha256"],
                       "materials_url": entry["materials_url"], "citation": entry["citation"]},
            "outcomes": "authored inference labels; not participant responses",
            "scored_denominator": None, "answer_counts": dict(Counter(p["fracas_answer"] for p in problems)),
            "nonstandard": sum(p["fracas_nonstandard"] for p in problems), "problems": problems,
            "anomalies": anomalies}


def _docx_paragraphs(payload):
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(payload)) as docx:
        root = ET.fromstring(docx.read("word/document.xml"))
    for p in root.iter(w + "p"):
        runs = []
        for r in p.iter(w + "r"):
            b = r.find(f"{w}rPr/{w}b")
            runs.append(("".join(t.text or "" for t in r.iter(w + "t")),
                         b is not None and b.get(w + "val") not in {"0", "false"}))
        text = "".join(t for t, _ in runs)
        if text.strip():
            yield text, all(bold for t, bold in runs if t.strip())


def fine(cache=CACHE, *, fetch=False, source=None):
    entry = _block(source or manifest(), "fine_2013")
    paragraphs = list(_docx_paragraphs(verified(Path(cache) / FINE_FILE, entry["materials_sha256"],
                                                entry["materials_url"], fetch=fetch)))
    blocks, anomalies = [], []
    for raw, bold in paragraphs:
        heading = re.match(r"Block\s*(\d+)", _text(raw))
        if not heading and not blocks:
            if _text(raw).startswith("Appendix"):
                continue
            raise SourceError(f"Fine 2013: text before the first block heading: {_text(raw)!r}")
        if heading:
            head = _text(raw)
            groups = ["rc-first", "filler-first"] if "both groups" in head else \
                ["rc-first"] if "RC-First" in head else ["filler-first"] if "Filler-First" in head else None
            if groups is None:
                raise SourceError(f"Fine 2013: unrecognised block heading {head!r}")
            labels = re.search(r"\{([^}]*)\}", head)
            blocks.append({"id": f"b{heading[1]}-{groups[0] if len(groups) == 1 else 'all'}",
                           "block": int(heading[1]), "groups": groups, "heading": head,
                           "presentation_order": "actual order" in head,
                           "condition_labels": [_text(x) for x in labels[1].split(",")] if labels else None,
                           "events": []})
            continue
        block = blocks[-1]
        item = re.fullmatch(r"(.*?)\{([^}]*)\}(.*)", raw, re.S)
        # Mixed blocks mark items in bold; other blocks hold only items or only fillers.
        expected = bold if block["presentation_order"] and block["condition_labels"] else bool(block["condition_labels"])
        if bool(item) != expected:
            raise SourceError(f"Fine 2013: alternation does not match the block's item marking in {_text(raw)!r}")
        event = {"id": f"fine2013:{block['id']}:{len(block['events']) + 1:02d}", "source_text": _text(raw)}
        if item:
            alternatives = [_text(a) for a in item[2].split(",")]
            if len(alternatives) != len(block["condition_labels"]):
                raise SourceError(f"Fine 2013: alternation does not match labels in {_text(raw)!r}")
            event |= {"role": "item", "alternatives": alternatives, "conditions": [
                {"name": name, "text": _text(f"{item[1]} {alt} {item[3]}")}
                for name, alt in zip(block["condition_labels"], alternatives)]}
            unreduced = [i for i, a in enumerate(alternatives) if re.match(r"(who|that)\b", a)]
            if len(unreduced) == 1 and unreduced != [len(alternatives) - 1]:
                anomalies.append({"event": event["id"], "issue": "declared {ambiguous, unambiguous} order "
                                  "contradicted: the unreduced relative is listed first; labels left as declared"})
        else:
            event["role"] = "filler"
            if re.search(r"\b(who|that) (was|were)\b", raw):
                anomalies.append({"event": event["id"], "issue": "filler contains an unreduced relative like the "
                                  "items but has no alternation or bold; possibly an item, left as a filler"})
        block["events"].append(event)
    return {"source": {"block": "fine_2013", "id": "fine2013_experiment2", "url": entry["materials_url"],
                       "sha256": entry["materials_sha256"], "citation": entry["citation"]},
            "outcomes": "stimuli and block order only; raw participant responses not verified",
            "groups": ["rc-first", "filler-first"],
            "unknown": ["which condition version each participant or list received",
                        "presentation order within block 1"],
            "blocks": blocks, "anomalies": anomalies}


def battery(cache=CACHE, *, fetch=False):
    source = manifest()
    return {"schema": 1, "manifest": MANIFEST,
            "manifest_sha256": hashlib.sha256(data_path(MANIFEST).read_bytes()).hexdigest(),
            "status": "imported_source_materials_no_scores",
            "syntaxgym": [syntaxgym(s["id"], cache, fetch=fetch, source=source) for s in source["core"]["suites"]],
            "fracas": fracas(cache, source=source), "fine_2013": fine(cache, fetch=fetch, source=source),
            "not_imported": NOT_IMPORTED, "quarantined": source["quarantined"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=CACHE)
    parser.add_argument("--output", type=Path, default=WORKING_ROOT / "build/experiments/battery-v1.json")
    parser.add_argument("--fetch", action="store_true", help="download missing pinned files that have a direct URL")
    args = parser.parse_args()
    value = battery(args.cache, fetch=args.fetch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    print(json.dumps({"output": str(args.output),
                      "syntaxgym": {s["source"]["id"]: len(s["families"]) for s in value["syntaxgym"]},
                      "fracas": value["fracas"]["answer_counts"],
                      "fine_2013": {f"{b['block']}:{'+'.join(b['groups'])}": len(b["events"]) for b in value["fine_2013"]["blocks"]},
                      "anomalies": {k: len(value[k]["anomalies"]) for k in ("fracas", "fine_2013")}}))


if __name__ == "__main__":
    main()
