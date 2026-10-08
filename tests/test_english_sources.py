"""Local source contracts: literal search, source fidelity and bounded workers."""

from hashlib import sha256
import sqlite3
import subprocess
import zipfile

import pytest

from dylan import english_sources as sources
from dylan.lexical_dictionary import ARCHIVE_SHA256, VERSION
from dylan.research_sources import SourceError
from scripts.build_english_corpora import build


@pytest.fixture
def corpora(tmp_path, monkeypatch):
    monkeypatch.setenv("DS_ENGLISH_CORPORA", str(tmp_path))
    archive = tmp_path / "brown.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr("brown/README", "Brown test attribution")
        source.writestr("brown/cats.txt", "ca01 news\ncb01 fiction\n")
        source.writestr(
            "brown/ca01", "\n John/np knows/vbz you/pp ./.\nThe/at river/nn bank/nn ./.\n"
        )
        source.writestr(
            "brown/cb01",
            "John/np lends/vbz a/at book/nn ./.\nbankers/nns run/vb the/at bank/nn ./.\n",
        )
    build(archive, tmp_path / "brown.sqlite3", "brown")
    return tmp_path


def test_phrase_pagination_and_tagged_source(corpora):
    first = sources.search({"q": "bank", "limit": "1"})
    second = sources.search({"q": "bank", "limit": "1", "offset": "1"})
    assert first["total"] == 2 and first["has_more"]
    assert not second["has_more"]
    row = first["results"][0]
    assert row["full_text"] == "The river bank ."
    assert row["metadata"]["tagged_source"] == "The/at river/nn bank/nn ./."
    assert row["metadata"]["line"] == 3
    assert (
        row["metadata"]["archive_sha256"]
        == sha256((corpora / "brown.zip").read_bytes()).hexdigest()
    )
    assert row["fingerprint"] != second["results"][0]["fingerprint"]
    assert sources.search({"q": "RIVER bank"})["total"] == 1


def test_exact_filters_and_literal_fts(corpora):
    assert sources.search({"q": "bank", "register": "news"})["total"] == 1
    assert sources.search({"q": "bank", "register": "news", "corpus": "cb01"})["total"] == 0
    assert sources.search({"q": "bank OR lends"})["total"] == 0
    assert sources.search({"q": "John.*book", "kind": "regex", "register": "fiction"})["total"] == 1


def test_word_highlight_uses_matched_token_not_earlier_substring(corpora):
    row = sources.search({"q": "bank", "register": "fiction"})["results"][0]
    assert row["match"] == "bank"
    assert row["match_start"] == row["full_text"].rindex("bank")
    assert row["match_start"] > row["full_text"].index("bank")


def test_gutenberg_offsets_and_encoding(corpora):
    original = "[Book]\n\nMr. Brown drank café.\nHe left."

    class Spans:
        def span_tokenize(self, text):
            yield text.index("Mr."), text.index("\nHe")
            yield text.index("He left"), len(text)

    archive = corpora / "gutenberg.zip"
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr("gutenberg/README", "Gutenberg test attribution")
        source.writestr("gutenberg/book.txt", original.encode("latin-1"))
    build(archive, corpora / "gutenberg.sqlite3", "gutenberg", Spans(), {"test": "spans"})
    row = sources.search({"q": "café", "db": "gutenberg"})["results"][0]
    meta = row["metadata"]
    assert row["full_text"] == original[meta["start"] : meta["end"]]
    assert meta["encoding"] == "latin-1" and meta["sentence_model"] == {"test": "spans"}
    assert "tagged_source" not in meta
    passage = sources.passage({"db": "gutenberg", "id": str(meta["unit_id"])})
    assert passage["observation"]["full_text"] == row["full_text"]
    assert passage["source_readme"] == "Gutenberg test attribution"


def test_catalog_and_search_leave_index_unchanged(corpora):
    path = corpora / "brown.sqlite3"
    before = sha256(path.read_bytes()).hexdigest()
    catalog = sources.catalog({})
    assert len(catalog["stats"]) == 2
    assert sum(row["sentence_count"] for row in catalog["stats"]) == 4
    sources.search({"q": "bank"})
    assert sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize(
    "params",
    [
        {"db": "../secret", "q": "word"},
        {"q": ""},
        {"q": "[", "kind": "regex", "corpus": "ca01"},
        {"q": "word", "kind": "regex"},
        {"q": "word", "limit": "51"},
        {"q": "word", "offset": "-1"},
        {"q": "word", "mode": "spoken"},
    ],
)
def test_invalid_search(corpora, params):
    with pytest.raises(ValueError):
        sources.search(params)


def test_missing_index_is_not_empty_results(tmp_path, monkeypatch):
    monkeypatch.setenv("DS_ENGLISH_CORPORA", str(tmp_path))
    with pytest.raises(SourceError, match="not installed"):
        sources.search({"q": "bank"})


def test_timeout_returns_error_not_partial_results(monkeypatch):
    def timeout(args, **kwargs):
        assert kwargs["timeout"] == 15
        raise subprocess.TimeoutExpired(args, 15)

    monkeypatch.setattr(sources.subprocess, "run", timeout)
    with pytest.raises(SourceError, match="15-second"):
        sources.isolated_lookup("search", {"q": "pattern"})


@pytest.fixture
def wordnet(tmp_path, monkeypatch):
    path = tmp_path / "wordnet.sqlite3"
    monkeypatch.setenv("DS_DICTIONARY_PATH", str(path))
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE senses(lemma TEXT, pos TEXT, synset INTEGER, lexfile INTEGER, rank INTEGER, frames TEXT, gloss TEXT);
            CREATE TABLE exceptions(surface TEXT, pos TEXT, lemma TEXT);
        """)
        db.executemany(
            "INSERT INTO metadata VALUES (?,?)",
            [("version", str(VERSION)), ("archive_sha256", ARCHIVE_SHA256)],
        )
        db.executemany(
            "INSERT INTO senses VALUES (?,?,?,?,?,?,?)",
            [
                ("bank", "n", 1, 0, 1, "[]", "a financial institution"),
                ("depository", "n", 1, 0, 1, "[]", "a financial institution"),
                ("bank", "n", 2, 0, 2, "[]", "the sloping land beside water"),
                ("lend", "v", 3, 0, 1, "[14,15]", "give temporarily"),
                ("ice_cream", "n", 4, 0, 1, "[]", "frozen dessert"),
            ],
        )


def test_wordnet_senses_synonyms_morphology_and_frames(wordnet):
    bank = sources.dictionary({"q": "bank"})
    assert bank["total"] == 2
    assert bank["entries"][0]["synonyms"] == ["bank", "depository"]
    lend = sources.dictionary({"q": "lends"})["entries"][0]
    assert lend["headword"] == "lend" and lend["inflection"]
    assert lend["frames"][1] == {"id": 15, "text": "Somebody VERB something to somebody"}
    assert sources.dictionary({"q": "ice cream"})["total"] == 1


def test_definition_search_deduplicates_synsets_and_escapes_wildcards(wordnet):
    assert sources.dictionary({"q": "financial", "scope": "entry"})["total"] == 1
    assert sources.dictionary({"q": "%", "scope": "entry"})["total"] == 0


def test_isolated_worker_reads_index_and_validates_options(corpora):
    assert sources.isolated_lookup("search", {"q": "bank"})["total"] == 2
    with pytest.raises(ValueError, match="Unknown English source option"):
        sources.isolated_lookup("search", {"q": "bank", "path": "/tmp"})
