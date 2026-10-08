"""Validate the DS research library and build portable metadata/HTML exports.

No network access, model calls or full-text redistribution. Run --check in CI
to validate references and detect stale generated files without writing.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "docs/research/library"


def read(name):
    return json.loads((LIBRARY / name).read_text())


def validate(papers, analyses, taxonomy, coverage, discovery):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    ids = [p["id"] for p in papers]
    require(len(ids) == len(set(ids)), "Duplicate paper IDs")
    categories = {c["id"] for c in coverage["categories"]}
    topics = {p["id"] for c in coverage["categories"] for p in c["phenomena"]}
    doi_ids = {}
    for paper in papers:
        sid, bib, tags, review = (paper[k] for k in ("id", "bibliographic", "tags", "review"))
        require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", sid), f"Unsafe citation key: {sid}")
        require(bib.get("title") and bib.get("author") and bib.get("issued"), f"Missing metadata: {sid}")
        require(review["status"] in taxonomy["review_statuses"], f"Unknown review status: {sid}")
        require(review["evidence_level"] in taxonomy["evidence_levels"], f"Unknown evidence level: {sid}")
        for field, allowed in (("categories", categories), ("mechanisms", taxonomy["mechanisms"]),
                               ("frameworks", taxonomy["frameworks"]), ("roles", taxonomy["roles"])):
            require(set(tags[field]) <= set(allowed), f"Unknown {field}: {sid}")
        require(tags["languages"] and paper["classification_basis"], f"Missing classification basis: {sid}")
        require(paper["metadata_provenance"], f"Missing metadata provenance: {sid}")
        if paper.get("ttr_integration"):
            require(paper["ttr_integration"] in taxonomy["ttr_integrations"] and "ttr" in tags["frameworks"],
                    f"Unknown or inconsistent TTR integration: {sid}")
        if bib.get("URL"):
            require(bib["URL"].startswith("https://"), f"Non-HTTPS public URL: {sid}")
        if bib.get("DOI"):
            doi = bib["DOI"].lower()
            require(doi not in doi_ids, f"Duplicate DOI: {sid} / {doi_ids.get(doi)}")
            doi_ids[doi] = sid
        for version in paper["versions"]:
            require(re.fullmatch(r"[a-f0-9]{64}", version["sha256"]), f"Bad fingerprint: {sid}")
            require(version["bytes"] > 0 and version["pdf_pages"] > 0, f"Empty source: {sid}")
    # Preserve source IDs and the actual inspected artifacts when migrating the ledger.
    indexed = {p["id"]: p for p in papers}
    for source in coverage["sources"]:
        require(source["id"] in indexed, f"Missing legacy source: {source['id']}")
        require(source["title"] == indexed[source["id"]]["bibliographic"]["title"], f"Legacy title drift: {source['id']}")
    old_artifacts = json.loads((LIBRARY.parent / "ds-source-artifacts.json").read_text())["artifacts"]
    for artifact in old_artifacts:
        require(any(v["sha256"] == artifact["sha256"] for v in indexed[artifact["source_id"]]["versions"]),
                f"Lost inspected version: {artifact['source_id']}")
    require(len({a["id"] for a in analyses}) == len(analyses), "Duplicate analysis IDs")
    for analysis in analyses:
        require(set(analysis["topics"]) <= topics, f"Unknown topic: {analysis['id']}")
        require(set(analysis["mechanisms"]) <= set(taxonomy["mechanisms"]), f"Unknown mechanism: {analysis['id']}")
        require(analysis["sources"], f"Unsourced analysis: {analysis['id']}")
        for citation in analysis["sources"]:
            require(citation["paper"] in indexed and citation["locator"] and citation["version"], f"Invalid source locator: {analysis['id']}")
        for implementation in analysis["implementations"]:
            require(implementation["backend"] in {"classical", "constructive", "ttr"}, "Unknown backend")
            require(implementation["status"] in taxonomy["implementation_statuses"], "Unknown implementation status")
        for path in analysis["code"]:
            resolved = (ROOT / path).resolve()
            require(resolved.is_relative_to(ROOT) and resolved.is_file(), f"Missing/outside code link: {path}")
        for example in analysis["examples"]:
            require(example["origin"] and example["expected"], f"Unattributed example: {analysis['id']}")
    assigned = [c for collection in taxonomy["collections"] for c in collection["categories"]]
    require(set(assigned) == categories and len(assigned) == len(categories), "Collections must cover all categories once")
    seen = set()
    for candidate in discovery["candidates"]:
        require(candidate["doi"] not in seen, "Duplicate discovery DOI")
        seen.add(candidate["doi"])
        if candidate["screening"] == "already_catalogued":
            require(doi_ids.get(candidate["doi"]) == candidate["catalogue_id"], "Wrong discovery/catalogue cross-reference")


def csl_record(paper):
    record = {"id": paper["id"], **deepcopy(paper["bibliographic"])}
    record["keyword"] = ", ".join(f"DS:{key}:{value}" for key in ("categories", "frameworks", "mechanisms") for value in paper["tags"][key])
    if paper.get("ttr_integration"):
        record["keyword"] += ", DS:ttr_integration:" + paper["ttr_integration"]
    record["note"] = "Review: " + paper["review"]["status"] + ". " + paper["review"]["scope"]
    if paper.get("date_note"):
        record["note"] += " " + paper["date_note"]
    return record


def bib_escape(value):
    replacements = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&",
                    "%": r"\%", "_": r"\_", "$": r"\$", "#": r"\#", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in str(value))


def bib_record(record):
    kind = {"article-journal": "article", "book": "book", "chapter": "incollection",
            "paper-conference": "inproceedings", "thesis": "phdthesis"}[record["type"]]
    fields = {"title": record["title"], "author": " and ".join(
        a.get("literal") or (a["family"] + (", " + a["given"] if a.get("given") else "")) for a in record["author"]),
        "year": record["issued"]["date-parts"][0][0]}
    parts = record["issued"]["date-parts"][0]
    if len(parts) > 1:
        fields["date"] = f"{parts[0]:04d}" + "".join(f"-{part:02d}" for part in parts[1:])
    for key, target in (("container-title", "journal" if kind == "article" else "booktitle"),
                        ("publisher", "school" if kind == "phdthesis" else "publisher"),
                        ("page", "pages"), ("volume", "volume"), ("issue", "number"),
                        ("DOI", "doi"), ("URL", "url"), ("keyword", "keywords"), ("note", "note")):
        if record.get(key):
            fields[target] = record[key]
    lines = []
    for key, value in fields.items():
        escaped = bib_escape(value)
        if key == "title":
            escaped = "{" + escaped + "}"  # Preserve DS/TTR and proper-name capitalization.
        lines.append(f"  {key} = {{{escaped}}}")
    return "@" + kind + "{" + record["id"] + ",\n" + ",\n".join(lines) + "\n}\n"


def build(check=False):
    book, cards, taxonomy, discovery = read("papers.json"), read("analyses.json"), read("taxonomy.json"), read("discovery.json")
    coverage = json.loads((LIBRARY.parent / "ds-theoretical-coverage.json").read_text())
    papers, analyses = book["papers"], cards["analyses"]
    validate(papers, analyses, taxonomy, coverage, discovery)
    csl = [csl_record(p) for p in papers]
    payload = {"date": book["date"], "papers": papers, "analyses": analyses, "taxonomy": taxonomy,
               "categories": [{k: c[k] for k in ("id", "title", "phenomena")} for c in coverage["categories"]],
               "discovery": discovery}
    embedded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    template = (LIBRARY / "library-template.html").read_text()
    if template.count("__LIBRARY_DATA__") != 1:
        raise ValueError("Expected one library data placeholder")
    outputs = {"ds-library.csl.json": json.dumps(csl, ensure_ascii=False, indent=2) + "\n",
               "ds-library.bib": "% Generated by scripts/build_ds_library.py; edit papers.json.\n\n" + "\n".join(bib_record(r) for r in csl),
               "index.html": template.replace("__LIBRARY_DATA__", embedded)}
    # A small, static discovery view for the public workbench. Source records
    # remain authoritative; do not ship local artifact paths or full texts.
    public = {"date": book["date"], "scope": book["scope"],
              "categories": [{k: c[k] for k in ("id", "title")} for c in coverage["categories"]],
              "frameworks": taxonomy["frameworks"], "review_statuses": taxonomy["review_statuses"],
              "ttr_integrations": taxonomy["ttr_integrations"],
              "papers": [{k: p[k] for k in ("id", "bibliographic", "tags", "review", "classification_basis", "ttr_integration") if k in p} for p in papers]}
    outputs["../../../workbench/library-data.js"] = (
        "// Generated by scripts/build_ds_library.py; edit the source library records.\n"
        + "window.dsLibraryData = " + json.dumps(public, ensure_ascii=False).replace("<", "\\u003c") + ";\n")
    stale = []
    for filename, content in outputs.items():
        path = LIBRARY / filename
        if check:
            if not path.exists() or path.read_text() != content:
                stale.append(filename)
        else:
            path.write_text(content)
    if stale:
        raise ValueError("Stale generated files: " + ", ".join(stale))
    print(f"Validated {len(papers)} works, {len(analyses)} analysis cards, {len(coverage['categories'])} categories, "
          f"{sum(len(c['phenomena']) for c in coverage['categories'])} topics, "
          f"{sum(len(p['versions']) for p in papers)} fingerprinted versions.")
    print("Review statuses:", dict(Counter(p["review"]["status"] for p in papers)))
    print("Discovery screening:", dict(Counter(c["screening"] for c in discovery["candidates"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate and compare outputs without writing")
    build(parser.parse_args().check)
