"""Read-only, bounded adapters for Svarna and the Triantafyllidis dictionary.

Source observations are evidence, not grammar rules or grammaticality judgments.
Only the two fixed public services can be contacted through these endpoints.
"""

from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

import certifi

SVARNA = "https://greek-corpus-workbench.wonderfulhill-e1c9f1a0.westeurope.azurecontainerapps.io"
DICTIONARY = (
    "https://www.greek-language.gr/greekLang/modern_greek/tools/lexica/triantafyllides/search.html"
)
DATABASES = {"corpus", "literature", "dialectal"}
ATTRIBUTION = (
    "Λεξικό της κοινής νεοελληνικής · Ινστιτούτο Νεοελληνικών Σπουδών · Κέντρο Ελληνικής Γλώσσας"
)


class SourceError(Exception):
    """A source failure is distinct from a successful search with zero results."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceError("The source address has changed. Open the original source to continue.")


def read_source(url, *, html=False, timeout=20):
    opener = build_opener(
        HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())), NoRedirect()
    )
    req = Request(url, headers={"User-Agent": "DS-Workbench/1.0 (user-directed research lookup)"})
    deadline = time.monotonic() + timeout + 1
    try:
        with opener.open(req, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type != ("text/html" if html else "application/json"):
                raise SourceError(
                    "The source returned an unexpected page. Open the source or retry."
                )
            chunks, size = [], 0
            while chunk := response.read1(65536):
                size += len(chunk)
                if size > 1_500_000 or time.monotonic() > deadline:
                    raise SourceError("The source response exceeded the limit. Narrow your search.")
                chunks.append(chunk)
        return b"".join(chunks).decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError) as exc:
        raise SourceError(
            "The source could not complete the lookup. Retry with a narrower search or open the source."
        ) from exc


def source_json(url, *, reader=None):
    try:
        result = json.loads((reader or read_source)(url))
    except json.JSONDecodeError as exc:
        raise SourceError("The source returned unreadable results. Please retry.") from exc
    if not isinstance(result, dict):
        raise SourceError("The source returned an unexpected result structure.")
    return result


def checked_rows(document, key, fields):
    rows = document.get(key)
    if not isinstance(rows, list) or any(
        not isinstance(row, dict) or any(not isinstance(row.get(f), str) for f in fields)
        for row in rows
    ):
        raise SourceError("The source result structure has changed. Open the source to inspect it.")
    return rows


def database(params):
    db = params.get("db", "corpus")
    if db not in DATABASES:
        raise ValueError("Choose a Svarna database.")
    return db


def query(params):
    q = params.get("q", "").strip()
    if not 1 <= len(q) <= 160 or any(ord(char) < 32 for char in q):
        raise ValueError("Enter a query of 1–160 characters on one line.")
    return q


def integer(params, key, default, maximum):
    try:
        value = int(params.get(key, str(default)))
    except ValueError as exc:
        raise ValueError(f"Invalid {key}.") from exc
    if not (0 if key == "offset" else 1) <= value <= maximum:
        raise ValueError(f"Invalid {key}.")
    return value


@lru_cache(maxsize=16)
def catalog(kind, db, bucket):
    """Cache only public availability/filter metadata, for five minutes."""
    if kind == "databases":
        doc = source_json(SVARNA + "/api/databases")
        rows = checked_rows(doc, "databases", ["name"])
        return {"databases": [row for row in rows if row["name"] in DATABASES]}
    doc = source_json(SVARNA + "/api/stats?" + urlencode({"db": db}))
    rows = checked_rows(doc, "stats", ["corpus", "register", "mode"])
    return {"db": db, "stats": rows}


def search(params, *, reader=None):
    db, q = database(params), query(params)
    kind = params.get("kind", "words")
    if kind not in {"words", "regex"}:
        raise ValueError("Choose words/phrase or regex search.")
    filters = {}
    for key in ("corpus", "register", "mode"):
        if value := params.get(key, ""):
            if len(value) > 120 or any(ord(c) < 32 for c in value):
                raise ValueError(f"Invalid {key} filter.")
            filters[key] = value
    if kind == "regex":
        if not filters.get("corpus"):
            raise ValueError("Choose one corpus or variety for a regex search.")
        try:
            re.compile(q)
        except re.error as exc:
            raise ValueError("The regular expression is invalid.") from exc
    offset = integer(params, "offset", 0, 10000)
    limit = integer(params, "limit", 20, 50)
    indexed_filters = dict(filters)
    if kind == "words" and any("-" in value for value in filters.values()):
        # Svarna currently backslash-escapes hyphens in MATCH filters, which FTS5
        # rejects. A space produces the same unicode61 token boundary inside its
        # phrase quoting. Only adapt known, unambiguous metadata values; preserve
        # original labels in the result and verify the returned observations.
        stats = (checked_rows(source_json(SVARNA + "/api/stats?" + urlencode({"db": db}), reader=reader), "stats", ["corpus", "register", "mode"])
                 if reader else catalog("corpora", db, int(time.time() // 300))["stats"])
        for key, value in filters.items():
            if "-" in value:
                indexed = value.replace("-", " ")
                equivalent = {row[key] for row in stats if row[key].replace("-", " ") == indexed}
                if equivalent != {value}:
                    raise ValueError(
                        "This indexed filter is ambiguous. Use a regex search within the corpus."
                    )
                indexed_filters[key] = indexed
    upstream = {
        "db": db,
        "pattern" if kind == "regex" else "q": q,
        **indexed_filters,
        "limit": limit,
        "offset": offset,
    }
    url = SVARNA + ("/api/regex?" if kind == "regex" else "/api/search?") + urlencode(upstream)
    doc = source_json(url, reader=reader)
    rows = checked_rows(doc, "results", ["full_text", "corpus", "register", "mode"])
    total = doc.get("total")
    if type(total) is not int or total < 0 or len(rows) > limit:
        raise SourceError("Svarna returned an unexpected result count.")
    if any(any(row[key] != value for key, value in filters.items()) for row in rows):
        raise SourceError(
            "Svarna returned examples outside the selected filters. Try a regex search within one corpus."
        )
    fetched = datetime.now(timezone.utc).isoformat()
    results = []
    for row in rows:
        # A content fingerprint, not a claimed stable upstream sentence identifier.
        fingerprint = sha256(
            json.dumps([db, row], ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        results.append({**row, "fingerprint": fingerprint})
    return {
        "source": "Svarna",
        "source_url": url,
        "fetched_at": fetched,
        "db": db,
        "query": q,
        "kind": kind,
        "filters": filters,
        "upstream_filters": indexed_filters,
        "results": results,
        "total": total,
        "offset": offset,
        "limit": limit,
        "total_is_exact": kind == "words",
        "has_more": offset + len(rows) < total and bool(rows) and offset + limit <= 10000,
        "note": "Regex totals can be capped by Svarna's scan limit."
        if kind == "regex"
        else "Counts are matching sentences, not word occurrences. Search uses Svarna's word index; it does not expand inflected forms.",
    }


class DictionaryParser(HTMLParser):
    """Read identifiable dictionary entries, never surrounding page/navigation text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.entry = None
        self.parts = []
        self.head = False
        self.head_seen = False
        self.skip = 0
        self.counting = False
        self.count_parts = []
        self.no_results = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.skip += 1
        if self.skip:
            return
        if tag == "td" and attrs.get("id") == "found":
            self.counting = True
        if tag == "dl" and re.fullmatch(r"1_[0-9]+", attrs.get("id", "")):
            self.entry = {"id": attrs["id"], "headword": ""}
            self.parts = []
            self.head_seen = False
        if self.entry:
            if tag == "b" and not self.head_seen:
                self.head = True
                self.head_seen = True
            if tag in {"p", "br"}:
                self.parts.append("\n")

    def handle_data(self, data):
        if self.skip:
            return
        if "Η αναζήτηση δεν επέστρεψε κανένα αποτέλεσμα." in data:
            self.no_results = True
        if self.counting:
            self.count_parts.append(data)
        if self.entry:
            self.parts.append(data)
            if self.head:
                self.entry["headword"] += data

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "td":
            self.counting = False
        if tag == "b":
            self.head = False
        if tag == "dl" and self.entry:
            text = "\n".join(
                " ".join(line.split()) for line in "".join(self.parts).splitlines()
            ).strip()
            self.entries.append({**self.entry, "text": text})
            self.entry = None
        if tag == "p" and self.entry:
            self.parts.append("\n")


def dictionary_lookup(params, *, reader=None):
    q = query(params)
    scope = params.get("scope", "headword")
    if scope not in {"headword", "entry"}:
        raise ValueError("Choose headword or whole-entry search.")
    url = (
        DICTIONARY
        + "?"
        + urlencode({"lq": q, "dq": "", **({"loptall": "true"} if scope == "entry" else {})})
    )
    parser = DictionaryParser()
    parser.feed((reader or read_source)(url, html=True))
    count = re.fullmatch(
        r"\s*([0-9.,]+)\s+εγγραφ(?:ή|ές)(?:\s+\[[0-9]+\s*-\s*[0-9]+\])?\s*",
        "".join(parser.count_parts),
    )
    if parser.entry is not None or (not parser.entries and not parser.no_results):
        raise SourceError(
            "The dictionary page could not be read. Open the source entry to continue."
        )
    if parser.entries and (
        not count or any(not e["headword"].strip() or not e["text"] for e in parser.entries)
    ):
        raise SourceError("The dictionary result structure has changed. Open the source entry.")
    total = int(re.sub(r"[.,]", "", count[1])) if count else 0
    if total < len(parser.entries) or (total > 0 and not parser.entries):
        raise SourceError(
            "The dictionary returned incomplete results. Open the source to continue."
        )
    entries = [{**entry, "url": url + "#" + entry["id"]} for entry in parser.entries[:20]]
    return {
        "source": "Triantafyllidis",
        "attribution": ATTRIBUTION,
        "query": q,
        "scope": scope,
        "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "total": total,
        "has_more": total > len(entries),
        "note": "Published entry text, with HTML formatting removed. A missing entry is not a judgment about a dialect word.",
    }


def dispatch(endpoint, params):
    if endpoint.startswith("/api/research/english/"):
        from dylan.english_sources import isolated_lookup

        return isolated_lookup(endpoint.removeprefix("/api/research/english/"), params)
    routes = {
        "/api/research/databases": (
            set(),
            lambda p: catalog("databases", "", int(time.time() // 300)),
        ),
        "/api/research/corpora": (
            {"db"},
            lambda p: catalog("corpora", database(p), int(time.time() // 300)),
        ),
        "/api/research/search": (
            {"q", "db", "corpus", "register", "mode", "kind", "limit", "offset"},
            search,
        ),
        "/api/research/dictionary": ({"q", "scope"}, dictionary_lookup),
    }
    if endpoint not in routes:
        raise KeyError(endpoint)
    allowed, handler = routes[endpoint]
    if set(params) - allowed:
        raise ValueError("Unknown lookup option.")
    return handler(params)
