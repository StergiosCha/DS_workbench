"""Local WordNet candidates with explicit morphology and source frame mappings.

This supplies lexical hypotheses, not grammaticality judgments. No network
access occurs during parsing; scripts/build_wordnet_dictionary.py builds the
optional index from the pinned Princeton WordNet 3.0 archive.
"""

from functools import lru_cache
import json
import os
from pathlib import Path
import re
import sqlite3

SOURCE = "Princeton WordNet 3.0"
ARCHIVE_URL = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet.zip"
ARCHIVE_SHA256 = "cbda5ea6eef7f36a97a43d4a75f85e07fccbb4f23657d27b4ccbc93e2646ab59"
VERSION = 2

# Suppletive/invariant plurals. WordNet exceptions supply the longer irregular
# list; people/person additionally disambiguates the everyday plural from the
# dictionary's collective sense of "a people".
NOUN_PLURALS = {"people": "person", "men": "man", "women": "woman", "children": "child",
                "mice": "mouse", "geese": "goose", "feet": "foot", "teeth": "tooth",
                "oxen": "ox", "sheep": "sheep", "deer": "deer", "fish": "fish"}
# These ontology roots live in noun.Tops, outside noun.person/noun.animal.
NOMINAL_ROOTS = {"00007846": "human", "00015388": "animal"}

# WordNet's published sentence-frame numbers. Unmapped frames stay visible as
# unsupported analyses; a PP or infinitive is never silently dropped.
FRAMES = {
    1: ("intransitive", ["object"]), 2: ("intransitive", ["human"]),
    8: ("transitive", ["human", "object"]), 9: ("transitive", ["human", "human"]),
    10: ("transitive", ["object", "human"]), 11: ("transitive", ["object", "object"]),
    14: ("ditransitive", ["human", "human", "object"]),
    15: ("dative-to", ["human", "human", "object"]),
    26: ("clausal", ["human"]),
}

# WordNet exceptions identify lemmas but do not distinguish past from
# participle. These explicit paradigms add that distinction for common verbs.
IRREGULAR = {
    "be": ("was were", "been"), "begin": ("began", "begun"),
    "break": ("broke", "broken"), "bring": ("brought", "brought"),
    "buy": ("bought", "bought"), "catch": ("caught", "caught"),
    "choose": ("chose", "chosen"), "come": ("came", "come"),
    "do": ("did", "done"), "drink": ("drank", "drunk"),
    "drive": ("drove", "driven"), "eat": ("ate", "eaten"),
    "fall": ("fell", "fallen"), "feel": ("felt", "felt"),
    "find": ("found", "found"), "fly": ("flew", "flown"),
    "forget": ("forgot", "forgotten"), "get": ("got", "got gotten"),
    "give": ("gave", "given"), "go": ("went", "gone"),
    "grow": ("grew", "grown"), "have": ("had", "had"),
    "hear": ("heard", "heard"), "hold": ("held", "held"),
    "keep": ("kept", "kept"), "know": ("knew", "known"),
    "lead": ("led", "led"), "leave": ("left", "left"),
    "lend": ("lent", "lent"), "lose": ("lost", "lost"),
    "make": ("made", "made"), "meet": ("met", "met"),
    "pay": ("paid", "paid"), "read": ("read", "read"),
    "ride": ("rode", "ridden"), "ring": ("rang", "rung"),
    "rise": ("rose", "risen"), "run": ("ran", "run"),
    "say": ("said", "said"), "see": ("saw", "seen"),
    "sell": ("sold", "sold"), "send": ("sent", "sent"),
    "sing": ("sang", "sung"), "sit": ("sat", "sat"),
    "sleep": ("slept", "slept"), "speak": ("spoke", "spoken"),
    "stand": ("stood", "stood"), "swim": ("swam", "swum"),
    "take": ("took", "taken"), "teach": ("taught", "taught"),
    "tell": ("told", "told"), "think": ("thought", "thought"),
    "throw": ("threw", "thrown"), "understand": ("understood", "understood"),
    "wear": ("wore", "worn"), "win": ("won", "won"),
    "write": ("wrote", "written"),
}


def dictionary_path():
    return Path(os.getenv("DS_DICTIONARY_PATH", ".ds-workbench/dictionaries/wordnet.sqlite3"))


def configuration():
    return {"installed": dictionary_path().is_file(), "source": SOURCE,
            "languages": ["English"], "version": VERSION}


@lru_cache(maxsize=4)
def _connect(path, modified):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    meta = dict(connection.execute("SELECT key, value FROM metadata"))
    if meta.get("archive_sha256") != ARCHIVE_SHA256 or meta.get("version") != str(VERSION):
        connection.close()
        raise ValueError("Dictionary index version differs; rebuild the local WordNet index")
    return connection


def _lemmas(surface, pos, connection):
    if pos == "a":
        return [(surface, "invariant")]
    candidates = {(surface, "base" if pos == "v" else "singular")}
    if pos == "n" and surface in NOUN_PLURALS:
        if NOUN_PLURALS[surface] != surface:
            candidates.clear()
        candidates.add((NOUN_PLURALS[surface], "plural"))
    suffixes = [("s", ""), ("ses", "s"), ("xes", "x"), ("zes", "z"),
                ("ches", "ch"), ("shes", "sh"), ("ies", "y")]
    for ending, replacement in suffixes:
        if surface.endswith(ending) and len(surface) > len(ending):
            candidates.add((surface[:-len(ending)] + replacement,
                            "present_3sg" if pos == "v" else "plural"))
    if pos == "v":
        for ending, label in [("ed", "past"), ("ing", "present_participle")]:
            if surface.endswith(ending) and len(surface) > len(ending) + 1:
                stem = surface[:-len(ending)]
                for lemma in {stem, stem + "e", stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else stem}:
                    candidates.add((lemma, label))
                if ending == "ed" and stem.endswith("i"):
                    candidates.add((stem[:-1] + "y", label))
    for row in connection.execute("SELECT lemma FROM exceptions WHERE surface=? AND pos=?", (surface, pos)):
        lemma = row["lemma"]
        if pos == "n":
            candidates.add((lemma, "plural"))
        else:
            past, participle = IRREGULAR.get(lemma, ("", ""))
            labels = []
            if surface in past.split():
                labels.append("past")
            if surface in participle.split():
                labels.append("past_participle")
            candidates.update((lemma, label) for label in labels or ["unspecified"])
    return sorted(candidates, key=lambda item: (item[0] != surface, item[0], item[1]))


def is_plural_of(surface, lemma):
    if NOUN_PLURALS.get(surface) == lemma:
        return True
    if surface == lemma:
        return False
    regular = lemma + ("es" if lemma.endswith(("s", "x", "z", "ch", "sh")) else "s")
    if len(lemma) > 1 and lemma.endswith("y") and lemma[-2] not in "aeiou":
        regular = lemma[:-1] + "ies"
    if surface == regular:
        return True
    path = dictionary_path()
    if path.is_file():
        connection = _connect(str(path), path.stat().st_mtime_ns)
        return connection.execute("SELECT 1 FROM exceptions WHERE surface=? AND pos='n' AND lemma=?", (surface, lemma)).fetchone() is not None
    return False


def candidates(surface):
    """Return all indexed senses/frames and the supported proposal subset."""
    from dylan.lexical_expansion import PROTECTED, SURFACE, proposal

    if surface in PROTECTED or not SURFACE.fullmatch(surface):
        return [], []
    path = dictionary_path()
    if not path.is_file():
        return [], []
    connection = _connect(str(path), path.stat().st_mtime_ns)
    analyses, entries, seen = [], [], set()
    for pos in ("n", "v", "a"):
        for lemma, inflection in _lemmas(surface, pos, connection):
            for row in connection.execute(
                "SELECT * FROM senses WHERE lemma=? AND pos=? ORDER BY rank, synset", (lemma, pos)
            ):
                frames = json.loads(row["frames"])
                analysis = {"lemma": lemma, "pos": pos, "inflection": inflection,
                            "synset": row["synset"], "gloss": row["gloss"], "frames": frames}
                analyses.append(analysis)
                if pos == "n" and surface == "people" and row["synset"] != "00007846":
                    # The body/grammatical-category senses pluralize as persons,
                    # not people. Suppletion is sense-specific here.
                    analysis["unsupported_reason"] = "This sense of person takes persons, not people."
                    continue
                mappings = []
                if pos == "n" and inflection in {"singular", "plural"}:
                    parent = NOMINAL_ROOTS.get(row["synset"], {5: "animal", 18: "human"}.get(row["lexfile"], "object"))
                    mappings = [("plural-noun" if inflection == "plural" else "noun", [parent])]
                elif pos == "a":
                    # Attributive-only senses retain their WordNet (a) marker
                    # and therefore are not returned by this exact-lemma query.
                    # Arbitrary dictionary adjectives are not assumed intersective.
                    mappings = [("predicative-adjective", ["object"])]
                elif pos == "v" and inflection in {"base", "present_3sg", "past"}:
                    mappings = [FRAMES[frame] for frame in frames if frame in FRAMES]
                for template, domains in mappings:
                    # Different senses and valencies never redefine one predicate.
                    suffix = pos if pos in {"n", "a"} else "v" + "".join(d[0] for d in domains) + ("c" if template == "clausal" else "")
                    symbol = f"{lemma.replace('-', '_')}_{suffix}{row['synset']}"
                    if len(symbol) > 40 or not re.fullmatch(r"[a-z][a-z0-9_]*", symbol):
                        continue
                    key = (template, symbol, tuple(domains))
                    if key in seen:
                        continue
                    seen.add(key)
                    entries.append(proposal(surface, lemma, template, domains, symbol=symbol,
                                            evidence=f"{SOURCE} {pos}{row['synset']}: {row['gloss'][:170]}"))
    return entries, analyses
