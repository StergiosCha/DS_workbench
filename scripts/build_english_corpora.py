"""Build local Brown/Gutenberg indexes from installed NLTK archives; no downloads."""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import zipfile


def punkt(model):
    # Load the plain-text Punkt parameters, never a pickled model.
    import nltk
    from nltk.tokenize.punkt import PunktParameters, PunktSentenceTokenizer

    params = PunktParameters()
    params.abbrev_types = set((model / "abbrev_types.txt").read_text().splitlines())
    params.sent_starters = set((model / "sent_starters.txt").read_text().splitlines())
    params.collocations = {
        tuple(line.split("\t")) for line in (model / "collocations.tab").read_text().splitlines()
    }
    params.ortho_context = defaultdict(
        int,
        {
            key: int(value)
            for key, value in (
                line.split("\t") for line in (model / "ortho_context.tab").read_text().splitlines()
            )
        },
    )
    hashes = {
        name: sha256((model / name).read_bytes()).hexdigest()
        for name in (
            "abbrev_types.txt",
            "sent_starters.txt",
            "collocations.tab",
            "ortho_context.tab",
        )
    }
    return PunktSentenceTokenizer(params), {
        "nltk_version": nltk.__version__,
        "punkt_parameters": hashes,
    }


def build(archive, target, name, tokenizer=None, model_info=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_suffix(".building.sqlite3")
    digest = sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as source, sqlite3.connect(staging) as db:
        db.executescript("""
            DROP TABLE IF EXISTS units; DROP TABLE IF EXISTS unit_fts;
            DROP TABLE IF EXISTS documents; DROP TABLE IF EXISTS metadata;
            CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE documents(id TEXT PRIMARY KEY, label TEXT, register TEXT);
            CREATE TABLE units(id INTEGER PRIMARY KEY, document TEXT, text TEXT, raw TEXT,
                               start INTEGER, end INTEGER, line INTEGER);
            CREATE VIRTUAL TABLE unit_fts USING fts5(text, content='units', content_rowid='id',
                                                   tokenize='unicode61');
            CREATE INDEX units_document ON units(document);
        """)
        metadata = {
            "version": "1",
            "source": name,
            "archive_sha256": digest,
            "encoding": "utf-8" if name == "brown" else "latin-1",
            "readme": source.read(f"{name}/README").decode("utf-8"),
            "segmentation": "one nonempty tagged line"
            if name == "brown"
            else "English Punkt character spans",
            "model": json.dumps(model_info or {}, sort_keys=True),
        }
        db.executemany("INSERT INTO metadata VALUES (?,?)", metadata.items())
        if name == "brown":
            categories = dict(
                line.split()
                for line in source.read("brown/cats.txt").decode().splitlines()
                if line.strip()
            )
            files = sorted(categories)
        else:
            files = sorted(
                path.split("/", 1)[1]
                for path in source.namelist()
                if path.startswith("gutenberg/") and path.endswith(".txt")
            )
        for file in files:
            text = source.read(f"{name}/{file}").decode(metadata["encoding"])
            register = categories[file] if name == "brown" else "literature"
            title = (
                f"{file.upper()} · {register}"
                if name == "brown"
                else text.splitlines()[0].strip("[] ")
            )
            db.execute("INSERT INTO documents VALUES (?,?,?)", (file, title, register))
            if name == "brown":
                offset = 0
                for line_no, line in enumerate(text.splitlines(keepends=True), 1):
                    raw = line.strip()
                    if raw:
                        words = [token.rsplit("/", 1)[0] for token in raw.split()]
                        start = offset + line.index(raw)
                        db.execute(
                            "INSERT INTO units(document,text,raw,start,end,line) VALUES (?,?,?,?,?,?)",
                            (file, " ".join(words), raw, start, start + len(raw), line_no),
                        )
                    offset += len(line)
            else:
                for start, end in tokenizer.span_tokenize(text):
                    if text[start:end].strip():
                        db.execute(
                            "INSERT INTO units(document,text,raw,start,end,line) VALUES (?,?,?,?,?,?)",
                            (file, text[start:end], "", start, end, None),
                        )
        db.execute("INSERT INTO unit_fts(unit_fts) VALUES ('rebuild')")
        db.commit()
        count = db.execute("SELECT count(*) FROM units").fetchone()[0]
    staging.replace(target)
    return {"source": name, "documents": len(files), "units": count, "archive_sha256": digest}


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--nltk-data", type=Path, default=Path.home() / "nltk_data")
    args.add_argument("--output", type=Path, default=Path(".ds-workbench/corpora"))
    options = args.parse_args()
    tokenizer, info = punkt(options.nltk_data / "tokenizers/punkt_tab/english")
    for name in ("brown", "gutenberg"):
        print(
            json.dumps(
                build(
                    options.nltk_data / f"corpora/{name}.zip",
                    options.output / f"{name}.sqlite3",
                    name,
                    tokenizer,
                    info if name == "gutenberg" else None,
                )
            )
        )
