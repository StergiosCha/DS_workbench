"""Local corpus search and WordNet browsing, in bounded read-only workers."""

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from urllib.parse import urlencode

from dylan.research_sources import SourceError, integer, query

NAMES = {"brown": "Brown corpus", "gutenberg": "Gutenberg selections"}
WORDNET_URL = "https://wordnet.princeton.edu/"
# WordNet sentence-frame descriptions, indexed by their published frame numbers.
FRAME_TEXT = (
    None,
    "Something VERB",
    "Somebody VERB",
    "It is VERBing",
    "Something is VERBing PP",
    "Something VERB something Adjective/Noun",
    "Something VERB Adjective/Noun",
    "Somebody VERB Adjective",
    "Somebody VERB something",
    "Somebody VERB somebody",
    "Something VERB somebody",
    "Something VERB something",
    "Something VERB to somebody",
    "Somebody VERB on something",
    "Somebody VERB somebody something",
    "Somebody VERB something to somebody",
    "Somebody VERB something from somebody",
    "Somebody VERB somebody with something",
    "Somebody VERB somebody of something",
    "Somebody VERB something on somebody",
    "Somebody VERB somebody PP",
    "Somebody VERB something PP",
    "Somebody VERB PP",
    "Somebody's (body part) VERB",
    "Somebody VERB somebody to INFINITIVE",
    "Somebody VERB somebody INFINITIVE",
    "Somebody VERB that CLAUSE",
    "Somebody VERB to somebody",
    "Somebody VERB to INFINITIVE",
    "Somebody VERB whether INFINITIVE",
    "Somebody VERB somebody into V-ing something",
    "Somebody VERB something with something",
    "Somebody VERB INFINITIVE",
    "Somebody VERB VERB-ing",
    "It VERB that CLAUSE",
    "Something VERB INFINITIVE",
)


def corpus_path(name):
    return Path(os.getenv("DS_ENGLISH_CORPORA", ".ds-workbench/corpora")) / f"{name}.sqlite3"


@contextmanager
def connect(path, *, wordnet=False):
    if not path.is_file():
        raise SourceError(
            "The local WordNet index is not installed."
            if wordnet
            else "The local English corpus index is not installed. Run scripts/build_english_corpora.py."
        )
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        meta = dict(db.execute("SELECT key,value FROM metadata"))
        from dylan.lexical_dictionary import VERSION as WORDNET_VERSION
        if meta.get("version") != str(WORDNET_VERSION if wordnet else 1):
            raise SourceError("The local source index version is unsupported. Rebuild the index.")
        if wordnet:
            from dylan.lexical_dictionary import ARCHIVE_SHA256

            if meta.get("archive_sha256") != ARCHIVE_SHA256:
                raise SourceError("The WordNet index source differs from the expected archive.")
        yield db, meta
    except sqlite3.Error as exc:
        raise SourceError(
            "The local source index could not be read. Rebuild it and retry."
        ) from exc
    finally:
        db.close()


def database(params):
    name = params.get("db", "brown")
    if name not in NAMES:
        raise ValueError("Choose Brown or Gutenberg.")
    return name


def catalog(params):
    name = database(params)
    with connect(corpus_path(name)) as (db, meta):
        rows = db.execute(
            "SELECT d.id,d.label,d.register,count(u.id) AS count FROM documents d JOIN units u ON u.document=d.id GROUP BY d.id ORDER BY d.id"
        )
        return {
            "db": name,
            "source": NAMES[name],
            "language": "en",
            "stats": [
                {
                    "corpus": r["id"],
                    "label": r["label"],
                    "register": r["register"],
                    "mode": "written",
                    "sentence_count": r["count"],
                }
                for r in rows
            ],
            "archive_sha256": meta["archive_sha256"],
        }


def observation(row, name, meta, match="", match_start=-1):
    fields = dict(row)
    provenance = {
        "document": fields["document"],
        "title": fields["label"],
        "unit_id": fields["id"],
        "archive_sha256": meta["archive_sha256"],
        "start": fields["start"],
        "end": fields["end"],
        "encoding": meta["encoding"],
        "segmentation": meta["segmentation"],
        "sentence_model": json.loads(meta.get("model", "{}")),
    }
    if name == "brown":
        provenance.update(
            {
                "line": fields["line"],
                "tagged_source": fields["raw"],
                "text_representation": "POS tags removed; tokens joined with single spaces.",
            }
        )
    else:
        provenance["text_representation"] = (
            "Exact character span from the installed NLTK Gutenberg text."
        )
    source_url = "/api/research/english/passage?" + urlencode({"db": name, "id": fields["id"]})
    return {
        "full_text": fields["text"],
        "corpus": fields["document"],
        "label": fields["label"],
        "register": fields["register"],
        "mode": "written",
        "year": "",
        "match": match,
        "match_start": match_start,
        "source_url": source_url,
        "metadata": provenance,
        "fingerprint": sha256(
            f"{meta['archive_sha256']}:{name}:{fields['id']}:{fields['text']}".encode()
        ).hexdigest(),
    }


SELECT = "SELECT u.*,d.label,d.register FROM units u JOIN documents d ON d.id=u.document "


def search(params):
    name, q = database(params), query(params)
    kind = params.get("kind", "words")
    if kind not in {"words", "regex"}:
        raise ValueError("Choose words/phrase or regex search.")
    limit, offset = integer(params, "limit", 20, 50), integer(params, "offset", 0, 10000)
    filters = {key: params[key] for key in ("corpus", "register", "mode") if params.get(key)}
    if any(len(v) > 160 for v in filters.values()):
        raise ValueError("Invalid corpus filter.")
    if filters.get("mode", "written") != "written":
        raise ValueError("The installed English corpora use written mode.")
    where, values = [], []
    for key, field in (("corpus", "d.id"), ("register", "d.register")):
        if filters.get(key):
            where.append(field + "=?")
            values.append(filters[key])
    if kind == "regex":
        if not filters.get("corpus") and not filters.get("register"):
            raise ValueError("Choose a document, book or genre for a regex search.")
        try:
            pattern = re.compile(q, re.IGNORECASE)
        except re.error as exc:
            raise ValueError("The regular expression is invalid.") from exc
    else:
        # A literal phrase, never user-supplied FTS syntax/operators.
        where.append("u.id IN (SELECT rowid FROM unit_fts WHERE unit_fts MATCH ?)")
        values.append('"' + q.replace('"', '""') + '"')
    clause = " WHERE " + " AND ".join(where) if where else ""
    with connect(corpus_path(name)) as (db, meta):
        results, total = [], 0
        if kind == "words":
            total = db.execute(
                "SELECT count(*) FROM units u JOIN documents d ON d.id=u.document" + clause, values
            ).fetchone()[0]
            rows = db.execute(
                SELECT + clause + " ORDER BY u.id LIMIT ? OFFSET ?", [*values, limit, offset]
            )
            for row in rows:
                # Display highlighting is optional; index tokenization defines matching.
                highlight = re.search(
                    r"(?<!\w)" + re.escape(q) + r"(?!\w)", row["text"], re.IGNORECASE
                )
                results.append(
                    observation(
                        row,
                        name,
                        meta,
                        highlight[0] if highlight else "",
                        highlight.start() if highlight else -1,
                    )
                )
        else:
            for row in db.execute(SELECT + clause + " ORDER BY u.id", values):
                match = pattern.search(row["text"])
                if match:
                    if offset <= total < offset + limit:
                        results.append(observation(row, name, meta, match[0], match.start()))
                    total += 1
        return {
            "source": NAMES[name],
            "language": "en",
            "db": name,
            "query": q,
            "kind": kind,
            "filters": filters,
            "results": results,
            "total": total,
            "total_is_exact": True,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(results) < total and offset + limit <= 10000,
            "source_url": "/api/research/english/search?" + urlencode(params),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "archive_sha256": meta["archive_sha256"],
            "note": (
                "Counts are corpus sentence units, not word occurrences. Brown text has POS tags removed; tokens are separated by spaces."
                if name == "brown"
                else "Counts are automatically segmented sentence spans. Headings, poetry and dialogue may have imperfect boundaries; original text and offsets are preserved."
            ),
        }


def passage(params):
    name = database(params)
    identifier = integer(params, "id", 1, 10000000)
    with connect(corpus_path(name)) as (db, meta):
        row = db.execute(SELECT + " WHERE u.id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("This passage is not in the local index.")
        return {
            "source": NAMES[name],
            "observation": observation(row, name, meta),
            "source_readme": meta["readme"],
        }


def dictionary(params):
    from dylan.lexical_dictionary import SOURCE, _lemmas, dictionary_path

    q = query(params)
    scope = params.get("scope", "headword")
    if scope not in {"headword", "entry"}:
        raise ValueError("Choose a word/lemma or definition search.")
    needle = q.lower().replace(" ", "_")
    entries, seen = [], set()
    with connect(dictionary_path(), wordnet=True) as (db, meta):
        if scope == "entry":
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = db.execute(
                "SELECT * FROM senses WHERE gloss LIKE ? ESCAPE '\\' ORDER BY pos,synset,lemma",
                (f"%{escaped}%",),
            )
            found = ((r, "definition search") for r in rows)
        else:
            found = []
            for pos in ("n", "v", "a"):
                for lemma, inflection in _lemmas(needle, pos, db):
                    rows = db.execute(
                        "SELECT * FROM senses WHERE lemma=? AND pos=? ORDER BY rank,synset",
                        (lemma, pos),
                    )
                    found.extend((r, inflection) for r in rows)
        for row, inflection in found:
            identity = (row["pos"], row["synset"])
            if identity in seen:
                continue
            seen.add(identity)
            if len(entries) >= 60:
                continue
            synonyms = [
                r[0].replace("_", " ")
                for r in db.execute(
                    "SELECT DISTINCT lemma FROM senses WHERE pos=? AND synset=? ORDER BY lemma",
                    identity,
                )
            ]
            frames = json.loads(row["frames"])
            entries.append(
                {
                    "id": f"{row['pos']}:{row['synset']}",
                    "headword": row["lemma"].replace("_", " "),
                    "pos": {"n": "noun", "v": "verb", "a": "adjective"}[row["pos"]],
                    "synset": row["synset"],
                    "text": row["gloss"],
                    "synonyms": synonyms,
                    "inflection": inflection,
                    "frames": [
                        {
                            "id": f,
                            "text": FRAME_TEXT[f] if 0 < f < len(FRAME_TEXT) else f"Frame {f}",
                        }
                        for f in frames
                    ],
                    "url": WORDNET_URL,
                }
            )
        return {
            "source": SOURCE,
            "language": "en",
            "query": q,
            "scope": scope,
            "source_url": WORDNET_URL,
            "entries": entries,
            "total": len(seen),
            "has_more": len(seen) > len(entries),
            "attribution": SOURCE + " · Princeton University",
            "archive_sha256": meta["archive_sha256"],
            "note": "The installed index covers nouns, verbs and adjectives. Adjective position markers are retained when a sense excludes ordinary predication. Glosses retain WordNet's examples; frames describe the selected lemma. Morphological matches are candidate analyses, not contextual sense judgments. Up to 60 senses are shown.",
        }


def dispatch(action, params):
    routes = {
        "corpora": ({"db"}, catalog),
        "search": ({"db", "q", "kind", "corpus", "register", "mode", "offset", "limit"}, search),
        "dictionary": ({"q", "scope"}, dictionary),
        "passage": ({"db", "id"}, passage),
    }
    if action not in routes:
        raise KeyError(action)
    allowed, handler = routes[action]
    if set(params) - allowed:
        raise ValueError("Unknown English source option.")
    return handler(params)


def isolated_lookup(action, params):
    if action not in {"corpora", "search", "dictionary", "passage"}:
        raise KeyError(action)
    try:
        worker = subprocess.run(
            [sys.executable, "-m", "dylan.english_sources"],
            input=json.dumps({"action": action, "params": params}),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if worker.returncode:
            raise SourceError("The local source worker stopped. Check the installed indexes.")
        result = json.loads(worker.stdout)
    except subprocess.TimeoutExpired as exc:
        raise SourceError(
            "English search reached the 15-second limit. Narrow the query or choose a simpler regex."
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceError("The English source worker could not return results.") from exc
    if "error" in result:
        raise (ValueError if result.get("invalid") else SourceError)(result["error"])
    return result


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    try:
        answer = dispatch(payload["action"], payload["params"])
    except (ValueError, SourceError) as exc:
        answer = {"error": str(exc), "invalid": isinstance(exc, ValueError)}
    print(json.dumps(answer, ensure_ascii=False))
