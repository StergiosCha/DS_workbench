"""External source contracts: no-result honesty, bounds, provenance and HTTP routing."""

import json
import threading
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

import pytest

from dylan import research_sources as sources
from dylan.workbench_server import make_server


ENTRY = '<td id="found">1 εγγραφή</td><div id="lemmas"><dl id="1_42"><dt><b>λέξη</b> ουσ. <b>1.</b> Meaning. <i>Example.</i><p>Etymology.</p></dt></dl></div>'
EMPTY = '<div id="warning"><h3>Η αναζήτηση δεν επέστρεψε κανένα αποτέλεσμα.</h3></div>'
ROW = {
    "full_text": "ιξέρω τον.",
    "corpus": "grdd_cypriot",
    "register": "dialectal",
    "mode": "written",
    "year": "",
    "metadata": '{"dialect":"Cypriot"}',
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    sources.catalog.cache_clear()
    monkeypatch.setattr(
        sources, "read_source", lambda *a, **kw: pytest.fail("Unexpected external request")
    )


def test_dictionary_extracts_identifiable_entry_not_page_text(monkeypatch):
    monkeypatch.setattr(
        sources,
        "read_source",
        lambda *a, **kw: "<header>Navigation</header>" + ENTRY + "<p>Footer</p>",
    )
    result = sources.dictionary_lookup({"q": "λέξη"})
    assert result["entries"][0]["headword"] == "λέξη"
    assert result["entries"][0]["text"] == "λέξη ουσ. 1. Meaning. Example.\nEtymology."
    assert result["entries"][0]["url"].endswith("#1_42")
    assert result["total"] == 1 and not result["has_more"]


def test_dictionary_empty_and_source_failure_are_distinct(monkeypatch):
    monkeypatch.setattr(sources, "read_source", lambda *a, **kw: EMPTY)
    assert sources.dictionary_lookup({"q": "άγνωστο"})["entries"] == []
    monkeypatch.setattr(sources, "read_source", lambda *a, **kw: "<h1>Service unavailable</h1>")
    with pytest.raises(sources.SourceError):
        sources.dictionary_lookup({"q": "άγνωστο"})


@pytest.mark.parametrize(
    "html",
    [
        ENTRY.replace("1 εγγραφή", "2 εγγραφές").replace("</dl>", ""),
        ENTRY.replace("1 εγγραφή", "0 εγγραφές"),
        ENTRY.replace("λέξη", ""),
    ],
)
def test_incomplete_dictionary_markup_is_an_error(monkeypatch, html):
    monkeypatch.setattr(sources, "read_source", lambda *a, **kw: html)
    with pytest.raises(sources.SourceError):
        sources.dictionary_lookup({"q": "λέξη"})


def test_dictionary_scope_pagination_and_escaped_content(monkeypatch):
    urls = []

    def read(url, **kw):
        urls.append(url)
        return ENTRY.replace("1 εγγραφή", "12 εγγραφές [1 - 1]").replace(
            "Meaning.", "&lt;img src=x&gt;<script>bad()</script>"
        )

    monkeypatch.setattr(sources, "read_source", read)
    result = sources.dictionary_lookup({"q": "meaning & value", "scope": "entry"})
    assert parse_qs(urlsplit(urls[0]).query)["loptall"] == ["true"]
    assert parse_qs(urlsplit(urls[0]).query)["lq"] == ["meaning & value"]
    assert result["has_more"]
    assert "<img src=x>" in result["entries"][0]["text"]
    assert "bad()" not in result["entries"][0]["text"]


def test_search_preserves_original_metadata_and_query_provenance(monkeypatch):
    urls = []

    def read(url):
        urls.append(url)
        return json.dumps({"results": [ROW], "total": 25})

    monkeypatch.setattr(sources, "read_source", read)
    result = sources.search(
        {"q": "ιξέρω", "db": "dialectal", "corpus": "grdd_cypriot", "limit": "1", "offset": "2"}
    )
    assert result["results"][0]["full_text"] == ROW["full_text"]
    assert result["results"][0]["metadata"] == ROW["metadata"]
    assert result["source_url"] == urls[0]
    assert result["fetched_at"] and len(result["results"][0]["fingerprint"]) == 64
    assert result["has_more"] and result["offset"] == 2
    assert parse_qs(urlsplit(urls[0]).query)["corpus"] == ["grdd_cypriot"]


def test_regex_uses_separate_endpoint_and_qualified_count(monkeypatch):
    urls = []
    monkeypatch.setattr(
        sources, "read_source", lambda url: urls.append(url) or '{"results":[],"total":0}'
    )
    result = sources.search(
        {"q": "τον.*", "db": "dialectal", "corpus": "grdd_cypriot", "kind": "regex"}
    )
    assert "/api/regex?" in urls[0] and "pattern" in parse_qs(urlsplit(urls[0]).query)
    assert not result["total_is_exact"]


def test_hyphenated_index_filter_uses_known_metadata_token_boundaries(monkeypatch):
    row = {**ROW, "corpus": "ud_ud_greek-gud"}
    urls = []

    def read(url):
        urls.append(url)
        if "/api/stats?" in url:
            return json.dumps({"stats": [row]})
        return json.dumps({"results": [row], "total": 1})

    monkeypatch.setattr(sources, "read_source", read)
    result = sources.search({"q": "και", "db": "corpus", "corpus": row["corpus"]})
    assert result["filters"]["corpus"] == "ud_ud_greek-gud"
    assert parse_qs(urlsplit(urls[-1]).query)["corpus"] == ["ud_ud_greek gud"]
    assert result["results"][0]["corpus"] == row["corpus"]


def test_source_results_must_obey_requested_filters(monkeypatch):
    monkeypatch.setattr(
        sources, "read_source", lambda url: json.dumps({"results": [ROW], "total": 1})
    )
    with pytest.raises(sources.SourceError, match="outside the selected filters"):
        sources.search({"q": "a", "db": "dialectal", "corpus": "grdd_pontic"})


@pytest.mark.parametrize(
    "params",
    [
        {"q": ""},
        {"q": "a" * 161},
        {"q": "a\nb"},
        {"q": "a", "db": "http://localhost"},
        {"q": "a", "kind": "bad"},
        {"q": "a", "kind": "regex"},
        {"q": "[", "kind": "regex", "corpus": "grdd_cypriot"},
        {"q": "a", "offset": "-1"},
        {"q": "a", "limit": "51"},
        {"q": "a", "limit": "oops"},
    ],
)
def test_bad_search_does_not_contact_sources(params):
    with pytest.raises(ValueError):
        sources.search(params)


@pytest.mark.parametrize(
    "doc",
    [
        {},
        {"results": [], "total": "0"},
        {"results": [None], "total": 1},
        {"results": [{"full_text": "a"}], "total": 1},
    ],
)
def test_malformed_search_is_not_reported_as_no_matches(monkeypatch, doc):
    monkeypatch.setattr(sources, "read_source", lambda url: json.dumps(doc))
    with pytest.raises(sources.SourceError):
        sources.search({"q": "a"})


def test_no_redirect_to_arbitrary_destination():
    with pytest.raises(sources.SourceError):
        sources.NoRedirect().redirect_request(None, None, 302, "", {}, "http://localhost")


def test_catalog_cache_is_separate_by_database(monkeypatch):
    urls = []
    monkeypatch.setattr(sources, "read_source", lambda url: urls.append(url) or '{"stats":[]}')
    for db in ["corpus", "corpus", "dialectal"]:
        sources.dispatch("/api/research/corpora", {"db": db})
    assert len(urls) == 2


def test_http_routes_preserve_source_error_and_validate_options(monkeypatch):
    monkeypatch.setattr(sources, "read_source", lambda *a, **kw: EMPTY)
    with make_server(0) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/research/dictionary?q=word", timeout=5) as response:
                assert json.load(response)["total"] == 0
                assert response.headers["X-Content-Type-Options"] == "nosniff"
            for path, status in [
                ("dictionary?q=a&q=b", 400),
                ("dictionary?q=a&url=http://localhost", 400),
                ("unknown", 404),
            ]:
                with pytest.raises(HTTPError) as error:
                    urlopen(base + "/api/research/" + path, timeout=5)
                assert error.value.code == status
            monkeypatch.setattr(sources, "read_source", lambda *a, **kw: "<h1>Error</h1>")
            with pytest.raises(HTTPError) as error:
                urlopen(base + "/api/research/dictionary?q=word", timeout=5)
            assert error.value.code == 502
        finally:
            server.shutdown()
            thread.join(timeout=5)
