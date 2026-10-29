from copy import deepcopy
import hashlib
import io
import json
import zipfile

import pytest

from dylan.experiments import literature
from dylan.experiments.literature import CACHE, SourceError, battery, fine, fracas, manifest, syntaxgym, verified

cached = pytest.mark.skipif(not (CACHE / literature.FINE_FILE).exists(),
                            reason="raw literature materials are local-only (build/experiments/literature)")


def suite_source(tmp_path, items, predictions="[(2;%a%) > (2;%b%)]"):
    raw = {"meta": {"name": "toy", "metric": "sum"}, "region_meta": {"1": "Start", "2": "Verb"},
           "predictions": [{"type": "formula", "formula": predictions}], "items": items}
    payload = json.dumps(raw).encode()
    (tmp_path / "toy.json").write_bytes(payload)
    source = deepcopy(manifest())
    source["core"]["suites"] = [{"id": "toy", "phenomenon": "toy", "url": "https://example.test/toy.json",
                                 "sha256": hashlib.sha256(payload).hexdigest(), "families": len(items),
                                 "condition_sentences": sum(len(i["conditions"]) for i in items),
                                 "region_metadata": raw["region_meta"], "outcomes": "toy",
                                 "source_predictions": raw["predictions"]}]
    return source


def toy_item(number, names=("a", "b"), second=""):
    return {"item_number": number, "conditions": [
        {"condition_name": n, "regions": [{"region_number": 1, "content": "The dog"},
                                          {"region_number": 2, "content": second if i else "barks"}]}
        for i, n in enumerate(names)]}


def test_suite_import_preserves_ids_regions_and_empty_content(tmp_path):
    value = syntaxgym("toy", tmp_path, source=suite_source(tmp_path, [toy_item(7), toy_item(9)]))
    assert [f["id"] for f in value["families"]] == ["toy:7", "toy:9"]
    assert value["critical_regions"] == [2]
    assert value["families"][0]["conditions"][1]["regions"][1] == {"number": 2, "label": "Verb", "content": ""}


@pytest.mark.parametrize("items", [
    [toy_item(1), toy_item(1)],                    # duplicate upstream IDs
    [toy_item(1, names=("a", "a"))],               # duplicate condition
    [toy_item(1, names=("a", "c"))],               # prediction names a missing condition
    [{"item_number": 1, "conditions": [{"condition_name": n, "regions": [
        {"region_number": 1, "content": "x"}, {"region_number": 3, "content": "y"}]} for n in "ab"]}],
])
def test_suite_integrity_failures(tmp_path, items):
    with pytest.raises(SourceError):
        syntaxgym("toy", tmp_path, source=suite_source(tmp_path, items))


def test_hash_mismatch_missing_file_and_unselected_suites_fail(tmp_path):
    source = suite_source(tmp_path, [toy_item(1)])
    (tmp_path / "toy.json").write_text("{}")
    with pytest.raises(SourceError, match="SHA-256"):
        syntaxgym("toy", tmp_path, source=source)
    with pytest.raises(SourceError, match="example.test"):
        syntaxgym("toy", tmp_path / "absent", source=source)
    with pytest.raises(SourceError, match="quarantined"):
        syntaxgym("fgd_hierarchy", tmp_path)
    with pytest.raises(SourceError, match="not a selected"):
        syntaxgym("npz_unknown", tmp_path)


def test_fetch_verifies_before_writing(tmp_path, monkeypatch):
    import dylan.hybrid.sources as sources

    monkeypatch.setattr(sources, "request", lambda url: b"tampered")
    with pytest.raises(SourceError, match="nothing written"):
        verified(tmp_path / "x.json", hashlib.sha256(b"pinned").hexdigest(), "https://example.test/x", fetch=True)
    assert not (tmp_path / "x.json").exists()
    monkeypatch.setattr(sources, "request", lambda url: b"pinned")
    assert verified(tmp_path / "x.json", hashlib.sha256(b"pinned").hexdigest(), "https://example.test/x",
                    fetch=True) == b"pinned"


def docx(paragraphs):
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join("<w:p>" + "".join(f"<w:r>{'<w:rPr><w:b/></w:rPr>' if bold else ''}<w:t xml:space=\"preserve\">"
                                     f"{text}</w:t></w:r>" for text, bold in runs) + "</w:p>" for runs in paragraphs)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipped:
        zipped.writestr("word/document.xml", f'<w:document xmlns:w="{w}"><w:body>{body}</w:body></w:document>')
    return buffer.getvalue()


def fine_source(tmp_path, paragraphs):
    payload = docx(paragraphs)
    (tmp_path / literature.FINE_FILE).write_bytes(payload)
    source = deepcopy(manifest())
    next(b for b in source["additional_blocks"] if b["id"] == "fine_2013")["materials_sha256"] = \
        hashlib.sha256(payload).hexdigest()
    return source


def test_fine_bold_marking_and_order_flags(tmp_path):
    source = fine_source(tmp_path, [
        [("Appendix S2", True)],
        [("Block 2 Items {ambiguous, unambiguous} (in bold) and fillers for both groups", True),
         (" (in the actual order used in the experiment)", False)],
        [("The cat sat.", False)],
        [("The dog {who was fed, served} the bone left.", True)],
        [("The boys who were fed the snacks slept.", False)],
    ])
    value = fine(tmp_path, source=source)
    events = value["blocks"][0]["events"]
    assert value["blocks"][0]["groups"] == ["rc-first", "filler-first"] and value["blocks"][0]["presentation_order"]
    assert [e["role"] for e in events] == ["filler", "item", "filler"]
    assert events[1]["conditions"][0] == {"name": "ambiguous", "text": "The dog who was fed the bone left."}
    assert [a["event"] for a in value["anomalies"]] == [events[1]["id"], events[2]["id"]]


def test_fine_rejects_unmarked_alternation(tmp_path):
    source = fine_source(tmp_path, [
        [("Block 2 Items {ambiguous, unambiguous} (in bold) and fillers for both groups (in the actual order)", True)],
        [("The dog {watched, who was seen} left.", False)],
    ])
    with pytest.raises(SourceError, match="item marking"):
        fine(tmp_path, source=source)


def fracas_source(tmp_path, problems):
    payload = f"<fracas-problems><comment class='section'> 1 QUANTIFIERS </comment>" \
              f"<comment> Q As are Bs </comment>{problems}</fracas-problems>".encode()
    (tmp_path / literature.FRACAS_FILE).write_bytes(payload)
    source = deepcopy(manifest())
    entry = next(b for b in source["additional_blocks"] if b["id"] == "fracas")
    entry["greek_sha256"], entry["greek_problem_records_verified"] = hashlib.sha256(payload).hexdigest(), 1
    return source


def test_fracas_reports_text_outside_fields_and_keeps_comments(tmp_path):
    source = fracas_source(tmp_path, "<problem id='001' fracas_answer='yes'>"
                           "<p idx='1'><translit> Enas <ipa> 'enas </ipa></translit><english> A man. </english></p>"
                           "<q><english> Q? </english></q><h>&gt;<ipa> h </ipa>.</h><a><english> Yes </english></a>"
                           "</problem>")
    value = fracas(tmp_path, source=source)
    problem = value["problems"][0]
    assert problem["section"] == "1 QUANTIFIERS" and problem["preceding_comments"] == ["Q As are Bs"]
    assert problem["premises"][0] == {"translit": "Enas", "english": "A man."}
    assert [(a["location"], a["text"]) for a in value["anomalies"]] == [("001/p1", "'enas"), ("001/h", ">"), ("001/h", ".")]


def test_fracas_missing_hypothesis_fails_cleanly(tmp_path):
    source = fracas_source(tmp_path, "<problem id='001' fracas_answer='yes'><p idx='1'>x</p><q>y</q><a>z</a></problem>")
    with pytest.raises(SourceError, match="001/h"):
        fracas(tmp_path, source=source)


@cached
def test_cached_battery_matches_manifest_and_known_source_anomalies():
    value = battery()
    source = manifest()
    assert sum(len(s["families"]) for s in value["syntaxgym"]) == source["core"]["families"] == 253
    assert sum(len(f["conditions"]) for s in value["syntaxgym"] for f in s["families"]) == 956
    npz = value["syntaxgym"][0]["families"][0]["conditions"]
    assert [r["content"] for r in npz[0]["regions"]][2:4] == ["", " the woman"]
    assert [r["content"] for r in npz[2]["regions"]][2] == ","
    assert value["fracas"]["answer_counts"] == {"yes": 203, "no": 33, "unknown": 98, "undef": 12}
    assert value["fracas"]["nonstandard"] == 41 and value["fracas"]["scored_denominator"] is None
    assert [a["location"] for a in value["fracas"]["anomalies"]] == ["015/p1", "146/h", "247/h"]
    assert "#Prediction" in value["syntaxgym"][0]["meta"]["comment"]
    blocks = value["fine_2013"]["blocks"]
    assert [(b["id"], len(b["events"]), sum(e["role"] == "item" for e in b["events"])) for b in blocks] == [
        ("b1-rc-first", 16, 16), ("b1-filler-first", 16, 0), ("b2-all", 30, 9), ("b3-all", 25, 10)]
    assert [a["event"] for a in value["fine_2013"]["anomalies"]] == ["fine2013:b1-rc-first:01", "fine2013:b2-all:22"]


@cached
def test_fracas_problem_fields():
    problems = fracas()["problems"]
    first = problems[0]
    assert first["id"] == "001" and first["subsection"] == "1.1 Conservativity"
    assert first["premises"][0]["english"] == "An Italian became the world's greatest tenor."
    assert all(p["premises"] and "subsubsection" not in p for p in problems if p["section"].startswith("1 "))
