"""Paragraph completion, context isolation, segmentation, and bounded failure."""

import json
import shutil
import subprocess
import time

import pytest

from dylan import paragraph_workbench as paragraphs
from dylan.action.meta.element import reset_all_meta_bindings
from dylan.workbench_api import parse_request, validate_request


@pytest.fixture(autouse=True)
def clean_bindings():
    reset_all_meta_bindings()
    yield
    reset_all_meta_bindings()


@pytest.mark.parametrize("language,text,expected", [
    ("en", 'Dr. Smith paid 3.50. "Really?" I agree!', ['Dr. Smith paid 3.50.', '"Really?"', 'I agree!']),
    ("en", 'John walks; Mary runs. He sleeps', ['John walks; Mary runs.', 'He sleeps']),
    ("el", 'Ο κ. Γιάννης ήρθε. Είσαι εδώ; Ναι!', ['Ο κ. Γιάννης ήρθε.', 'Είσαι εδώ;', 'Ναι!']),
    ("el", 'Περπατάς;  Εγώ κοιμάμαι.\n', ['Περπατάς;', 'Εγώ κοιμάμαι.']),
    ("en", '  I walk.\n\nYou walk.  ', ['I walk.', 'You walk.']),
])
def test_source_spans_preserve_every_nonspace_character(language, text, expected):
    spans = paragraphs.sentence_spans(text, language)
    assert [s["text"] for s in spans] == expected
    assert all(text[s["start"]:s["end"]] == s["text"] for s in spans)
    assert "".join(c for s in spans for c in s["text"] if not c.isspace()) == "".join(text.split())


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_named_antecedents_persist_and_traces_only_contain_current_sentence(backend):
    result = parse_request({"paragraph": "John walks. He knows Mary. She walks.", "grammar": f"2026-english-{backend}"})
    assert result["complete"] and result["coverage"]["complete"] == 3
    rows = result["sentences"]
    assert rows[1]["result"]["words"][-1]["normalized"] == "know(john, mary)"
    assert rows[2]["result"]["words"][-1]["normalized"] == "walk(mary)"
    assert rows[2]["context_sentences"] == [0, 1]
    assert "john" not in rows[2]["result"]["derivation"]["actions"]
    assert "john" not in rows[2]["result"]["readings"][0]["action_names"]
    assert all(f["word_index"] < len(row["tokens"]) for row in rows for f in row["result"]["words"])


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_failed_sentence_cannot_introduce_an_antecedent_but_later_sentences_run(backend):
    result = parse_request({"paragraph": "Bill walks. John glorp. He walks.", "grammar": f"2026-english-{backend}"})
    assert not result["complete"] and not result["ok"]
    assert result["coverage"] == {"complete": 2, "failed": 1, "total": 3, "all_complete": False}
    assert result["sentences"][1]["failure"]["token"] == "glorp"
    last = result["sentences"][2]
    assert last["context_gaps"] == [1] and last["context_sentences"] == [0]
    assert last["result"]["words"][-1]["normalized"] == "walk(bill)"


@pytest.mark.parametrize("backend", ["classical", "mltt"])
def test_greek_paragraph_keeps_every_sentence_and_distinct_definite_referents(backend, tmp_path):
    result = parse_request({"paragraph": "Είμαι πολύ μαλάκας. Ο άντρας περπατάει. Διαβάζω το βιβλίο. Εγώ σε ξέρω.", "grammar": f"2026-smg-{backend}"})
    assert result["complete"] and len(result["sentences"]) == 4
    assert result["sentences"][-1]["result"]["words"][-1]["normalized"] == "know(speaker, hearer)"
    if backend == "mltt":
        a = result["sentences"][1]["result"]["words"][-1]["normalized"]
        b = result["sentences"][2]["result"]["words"][-1]["normalized"]
        assert "definite_s2_" in a and "definite_s3_" in b
        if shutil.which("coqc"):
            for i, row in enumerate(result["sentences"]):
                path = tmp_path / f"Sentence{i}.v"
                path.write_text(row["result"]["coq"])
                compiled = subprocess.run(["coqc", str(path)], capture_output=True, text=True, timeout=15)
                assert compiled.returncode == 0, compiled.stderr


def test_timeout_is_a_coverage_failure_and_does_not_discard_later_rows(monkeypatch):
    import dylan.workbench_api as api
    original = api.parse_request
    def slow(payload, *args, **kwargs):
        if payload.get("sentence", "").startswith("John"):
            time.sleep(.1)
        return original(payload, *args, **kwargs)
    monkeypatch.setattr(api, "parse_request", slow)
    monkeypatch.setattr(paragraphs, "SENTENCE_SECONDS", .05)
    result = original({"paragraph": "John walks. Bill walks.", "grammar": "2026-english-mltt"})
    assert result["sentences"][0]["status"] == "search_limit"
    assert result["sentences"][1]["complete"]
    assert result["sentences"][1]["context_gaps"] == [0]
    assert result["coverage"]["failed"] == 1


def test_whole_paragraph_budget_retains_unattempted_rows(monkeypatch):
    monkeypatch.setattr(paragraphs, "PARAGRAPH_SECONDS", 0)
    result = parse_request({"paragraph": "John walks. Bill walks.", "grammar": "2026-english-mltt"})
    assert result["coverage"]["failed"] == 2
    assert all(row["status"] == "not_attempted" for row in result["sentences"])


def test_stream_accounts_for_each_sentence_and_is_bounded():
    events = []
    result = parse_request({"paragraph": "John walks. Unknown. Mary walks.", "grammar": "2026-english-mltt"}, events.append)
    assert [e["event"] for e in events] == ["paragraph_start"] + ["paragraph_sentence"] * 3
    assert len(json.dumps(result).encode()) < 500_000
    assert result["coverage"]["total"] == 3


def test_reused_lexical_hypotheses_keep_their_source_and_programs():
    sentence = "Η επιτροπή εγκρίνει την πρόταση."
    result = parse_request({"paragraph": sentence + " " + sentence, "grammar": "2026-smg-mltt", "lexical_mode": "corpus"})
    assert result["complete"]
    later = result["sentences"][1]["result"]
    assert later["lexical"]["entries"]
    assert all(e["reused"] and e["source"] == "corpus" and e["program"] for e in later["lexical"]["entries"])
    assert all(t["source"] == "corpus" for t in later["diagnostics"]["lexical_coverage"] if t["token"] in {"επιτροπή", "εγκρίνει", "πρόταση"})


def test_interrupted_lexical_installation_cannot_poison_next_sentence(monkeypatch):
    import dylan.lexical_expansion as expansion
    original = expansion.expand
    calls = 0
    def interrupted(parser, grammar, tokens, mode, **options):
        nonlocal calls
        calls += 1
        if calls == 1:
            parser.lexicon["glorp"] = list(parser.lexicon["john"])
            parser.semantic_profile["constants"]["bogus"] = "object"
            raise paragraphs.SentenceDeadline("Interrupted lexical installation")
        assert "glorp" not in parser.lexicon
        assert "bogus" not in parser.semantic_profile["constants"]
        return original(parser, grammar, tokens, mode, **options)
    monkeypatch.setattr(expansion, "expand", interrupted)
    result = parse_request({"paragraph": "John walks. Glorp walks.", "grammar": "2026-english-mltt"})
    assert result["sentences"][0]["status"] == "search_limit"
    assert result["sentences"][1]["failure"]["kind"] == "lexicon_gap"
    assert not result["complete"]


@pytest.mark.parametrize("extra", [{"sentence": "x"}, {"dialogue": []}, {"n_best": 2}, {"grammar": "2026-english-ttr"}, {"paragraph": " "}, {"paragraph": "x." * 3001}, {"paragraph": "x. " * 25}, {"paragraph": "x " * 401}])
def test_paragraph_validation(extra):
    with pytest.raises(ValueError):
        validate_request({"paragraph": "John walks.", "grammar": "2026-english-mltt", **extra})
