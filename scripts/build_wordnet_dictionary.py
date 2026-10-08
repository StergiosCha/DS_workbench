"""Build the optional local dictionary from a hash-pinned WordNet archive."""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

from dylan.lexical_dictionary import ARCHIVE_SHA256, SOURCE, VERSION, dictionary_path


def build(archive, target):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Archive does not match the pinned WordNet 3.0 source")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_suffix(".building.sqlite3")
    with zipfile.ZipFile(archive) as source, sqlite3.connect(staging) as db:
        db.executescript("""
            DROP TABLE IF EXISTS metadata; DROP TABLE IF EXISTS senses; DROP TABLE IF EXISTS exceptions;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE senses (lemma TEXT, pos TEXT, synset TEXT, lexfile INTEGER,
                                 rank INTEGER, frames TEXT, gloss TEXT);
            CREATE TABLE exceptions (surface TEXT, pos TEXT, lemma TEXT);
        """)
        db.executemany("INSERT INTO metadata VALUES (?,?)", [
            ("source", SOURCE), ("version", str(VERSION)), ("archive_sha256", ARCHIVE_SHA256),
            ("license", source.read("wordnet/LICENSE").decode()),
        ])
        for pos, suffix in [("n", "noun"), ("v", "verb"), ("a", "adj")]:
            ranks = {}
            for line in source.read(f"wordnet/index.{suffix}").decode().splitlines():
                if not line or line.startswith(" "):
                    continue
                bits = line.split()
                count, pointers = int(bits[2]), int(bits[3])
                offsets = bits[6 + pointers:6 + pointers + count]
                ranks.update(((bits[0], offset), rank) for rank, offset in enumerate(offsets))
            for line in source.read(f"wordnet/data.{suffix}").decode().splitlines():
                if not line or line.startswith(" "):
                    continue
                header, gloss = line.split("|", 1)
                bits = header.split()
                offset, lexfile, _, count = bits[:4]
                count = int(count, 16)
                # Keep attributive-only (a) and immediately-postnominal (ip)
                # markers. Strip (p) only: it explicitly allows predication.
                words = [bits[4 + 2 * i].removesuffix("(p)") for i in range(count)]
                cursor = 4 + 2 * count
                cursor += 1 + 4 * int(bits[cursor])
                frames = {i: [] for i in range(1, count + 1)}
                if pos == "v":
                    frame_count = int(bits[cursor])
                    cursor += 1
                    for _ in range(frame_count):
                        marker, frame, word = bits[cursor:cursor + 3]
                        assert marker == "+"
                        word = int(word, 16)
                        for i in frames if word == 0 else [word]:
                            frames[i].append(int(frame))
                        cursor += 3
                db.executemany("INSERT INTO senses VALUES (?,?,?,?,?,?,?)", [
                    (lemma, pos, offset, int(lexfile), ranks.get((lemma, offset), 999),
                     json.dumps(frames[i]), gloss.strip())
                    for i, lemma in enumerate(words, 1)
                ])
            for line in source.read(f"wordnet/{suffix}.exc").decode().splitlines():
                word, *lemmas = line.split()
                db.executemany("INSERT INTO exceptions VALUES (?,?,?)", [(word, pos, lemma) for lemma in lemmas])
        db.executescript("CREATE INDEX senses_lemma ON senses(lemma,pos); CREATE INDEX exception_surface ON exceptions(surface,pos);")
        counts = dict(db.execute("SELECT pos, count(DISTINCT lemma) FROM senses GROUP BY pos"))
        db.commit()
    staging.replace(target)
    print(json.dumps({"path": str(target), "source": SOURCE, "lemma_counts": counts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=dictionary_path())
    args = parser.parse_args()
    build(args.archive, args.output)
