"""Compile attested Greek forms into existing, typed DS lexical templates."""

from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
import unicodedata

GRAMMARS = {"2026-smg-classical", "2026-smg-mltt"}
SOURCE_HASH = "892cd36cd47372ec0d7ccdbc874af9a6994651cdb0cf2cee6ba93bb01ee83794"
from dylan.workbench_paths import data_path

PATH = data_path("greek-lexicon/gdt-train.json")
TRANSLITERATION = dict(zip("αβγδεζηθικλμνξοπρστυφχψως", ("a", "v", "g", "d", "e", "z", "i", "th", "i", "k", "l", "m", "n", "x", "o", "p", "r", "s", "t", "y", "f", "ch", "ps", "o", "s")))


@lru_cache(maxsize=1)
def source():
    data = json.loads(PATH.read_text())
    if data.get("version") != 2 or data.get("source_sha256") != SOURCE_HASH:
        raise ValueError("Rebuild the Greek lexical index from the pinned training source.")
    return data


def configuration():
    return {"installed": PATH.is_file(), "grammars": sorted(GRAMMARS),
            "source": "UD Greek GDT r2.17 · training split", "license": "CC BY-NC-SA 3.0",
            "coverage": "Corpus-derived hypotheses for attested singular nouns, predicative adjectives and active indicative verbs, including attested accusative-theme/genitive-recipient frames shared across a lemma's tensed singular forms. Case/person forms use DS templates; new closed classes, plurals, passive forms and arbitrary verb valencies are not inferred. Tense meaning and full adjective agreement are not modeled."}


def expand(parser, tokens, controls=()):
    report = {"mode": "corpus", "status": "corpus", "entries": [], "notices": [], "remaining": []}
    unknown = list(dict.fromkeys(t for t in tokens if t not in parser.lexicon and t not in controls))
    report["originally_missing"] = unknown
    try:
        data = source()
    except (OSError, ValueError) as exc:
        report.update(status="unavailable", remaining=unknown, notices=[str(exc)])
        return report
    theory = deepcopy(parser.semantic_profile)
    planned = []
    for word in unknown:
        if not word.isalpha():
            continue
        for row in data["entries"].get(word, []):
            lemma, kind = row["lemma"], row["kind"]
            if not lemma.isalpha():
                raise ValueError("Invalid lemma in Greek corpus index.")
            stem = "".join(TRANSLITERATION.get(c, c if c.isascii() else "u" + format(ord(c), "x")) for c in unicodedata.normalize("NFD", lemma) if not unicodedata.combining(c))
            symbol = "el_" + stem + "_" + sha256(lemma.encode()).hexdigest()[:6] + {"noun": "_n", "adjective": "_a", "transitive": "_v2", "intransitive": "_v1", "ditransitive": "_v3"}[kind]
            arity = {"transitive": 2, "ditransitive": 3}.get(kind, 1)
            templates = []
            if kind in {"noun", "adjective"}:
                case, gender = row["case"], row["gender"]
                if case not in {"nom", "acc"} or gender not in {"m", "f", "neut"}:
                    raise ValueError("Invalid Greek noun features.")
                if kind == "noun":
                    theory["subtyping"][symbol] = ["object"]
                    if theory["backend"] == "classical":
                        theory["predicates"][symbol] = ["object"]
                    templates.append(("common-noun", [symbol, case, gender]))
                    if case == "nom":
                        templates.append(("nominal-predicate", [symbol]))
                else:
                    theory["predicates"][symbol] = ["object"]
                    templates.append(("predicative-adjective", [symbol]))
            else:
                person = row["person"]
                if person not in {"1", "2", "3"}:
                    raise ValueError("Invalid Greek verb person.")
                subject = {"1": "speaker", "2": "hearer", "3": "pro"}[person]
                theory["predicates"][symbol] = ["object"] * arity
                if kind == "ditransitive":
                    frame = row.get("frame_evidence", {})
                    if frame.get("theme", {}).get("case") != "acc" or frame.get("recipient", {}).get("case") != "gen":
                        raise ValueError("Ditransitive candidates require accusative/genitive frame evidence.")
                    templates.append(("verb-ditransitive", [symbol, subject, person, "sg"]))
                else:
                    templates.append(("verb-finite", [symbol, subject, person, "sg"]) if kind == "transitive" else ("verb-intransitive", [symbol, subject, person]))
            for template, params in templates:
                action = parser.lexicon.instantiate_template(word, template, params)
                entry = {"surface": word, "lemma": lemma, "template": template, "symbol": symbol,
                         "domains": ["object"] * arity,
                         "morphology": "; ".join(f"{k}={v}" for k, v in sorted(row["features"].items())),
                         "source": "corpus", "evidence": f"{data['source']}, {row['sentence_id']}; lemma {lemma}.",
                         "source_url": data["source_url"], "license": data["license"],
                         "validation": "Attested feature values and approved DS template parameters checked; corpus analysis remains a lexical hypothesis.",
                         "program": list(action._source_lines)}
                if kind == "ditransitive":
                    entry["frame_evidence"] = deepcopy(frame)
                    entry["evidence"] += f" Frame hypothesis from {frame['sentence_id']}: {frame['surface']} with accusative obj {frame['theme']['surface']} and genitive iobj {frame['recipient']['surface']}; reused across this lemma's attested forms. Argument order: subject, theme, recipient."
                action.metadata = {k: v for k, v in entry.items() if k != "program"}
                planned.append((word, action, entry))
    # All instantiations succeed before either the lexicon or theory is changed.
    for word, action, entry in planned:
        parser.lexicon.setdefault(word, []).append(action)
        report["entries"].append(entry)
    parser.lexicon.invalidate_vocab_cache()
    parser.semantic_profile = theory
    report["remaining"] = [word for word in unknown if word not in parser.lexicon]
    report["notices"] = [data["note"]]
    return report
