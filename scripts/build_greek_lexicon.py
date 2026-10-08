"""Build inflected Greek lexical hypotheses from the pinned GDT training split.

The held-out test split is never used to build lexical entries. Annotation is
CC BY-NC-SA 3.0, ILSP/Athena RC; retain attribution when redistributing this data.
"""

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import unicodedata

SOURCE_SHA256 = "892cd36cd47372ec0d7ccdbc874af9a6994651cdb0cf2cee6ba93bb01ee83794"
SOURCE_URL = "https://raw.githubusercontent.com/UniversalDependencies/UD_Greek-GDT/r2.17/el_gdt-ud-train.conllu"


def build(source, output):
    content = source.read_bytes()
    if sha256(content).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the pinned UD Greek GDT r2.17 training split.")
    entries = defaultdict(dict)
    finite_forms, ditransitive_frames = defaultdict(dict), {}
    for block in content.decode().split("\n\n"):
        rows, identifier = [], ""
        for line in block.splitlines():
            if line.startswith("# sent_id = "):
                identifier = line.removeprefix("# sent_id = ")
            elif line and not line.startswith("#"):
                fields = line.split("\t")
                if len(fields) == 10 and fields[0].isdigit():
                    rows.append(fields)
        for row in rows:
            _, surface, lemma, pos, _, features, _, _, _, _ = row
            surface, lemma = (unicodedata.normalize("NFC", w.lower()) for w in (surface, lemma))
            if not surface.isalpha() or not lemma.isalpha() or len(surface) > 60:
                continue
            attrs = dict(pair.split("=", 1) for pair in features.split("|") if "=" in pair)
            if pos == "VERB" and attrs.get("VerbForm") == "Fin" and attrs.get("Mood") == "Ind" and attrs.get("Voice") == "Act":
                dependents = [r for r in rows if r[6] == row[0]]
                objects = [r for r in dependents if r[7] == "obj"]
                recipients = [r for r in dependents if r[7] == "iobj"]
                # Positive evidence for this case frame; never turn a generic
                # oblique or a clausal complement into a genitive recipient.
                if (len(objects) == len(recipients) == 1
                        and "Case=Acc" in objects[0][5] and "Case=Gen" in recipients[0][5]
                        and not any(r[7].split(":")[0] in {"ccomp", "xcomp", "csubj", "obl"} for r in dependents)):
                    ditransitive_frames.setdefault(lemma, {"sentence_id": identifier, "surface": surface,
                        "theme": {"surface": objects[0][1], "relation": "obj", "case": "acc"},
                        "recipient": {"surface": recipients[0][1], "relation": "iobj", "case": "gen"}})
                # Reuse the lemma's attested frame only on an independently
                # attested tensed singular indicative form. Dependent perfective
                # forms such as δώσει require separate na/future constructions.
                if attrs.get("Number") == "Sing" and attrs.get("Person") in {"1", "2", "3"} and attrs.get("Tense") in {"Past", "Pres"}:
                    finite_forms[lemma].setdefault(surface, {"features": attrs, "sentence_id": identifier})
            if attrs.get("Number") != "Sing":
                continue
            gender = {"Masc": "m", "Fem": "f", "Neut": "neut"}.get(attrs.get("Gender"))
            case = {"Nom": "nom", "Acc": "acc"}.get(attrs.get("Case"))
            parameters = None
            if pos == "NOUN" and gender and case:
                kind, parameters = "noun", {"case": case, "gender": gender}
            elif pos == "ADJ" and case == "nom" and gender:
                kind, parameters = "adjective", {"case": case, "gender": gender}
            elif pos == "VERB" and attrs.get("VerbForm") == "Fin" and attrs.get("Mood") == "Ind" and attrs.get("Voice") == "Act" and attrs.get("Person") in {"1", "2", "3"}:
                dependents = [r for r in rows if r[6] == row[0]]
                # Clausal/recipient/oblique arguments need their own DS frames.
                if any(r[7].split(":")[0] in {"iobj", "ccomp", "xcomp", "csubj", "obl"} for r in dependents):
                    continue
                objects = [r for r in dependents if r[7] == "obj"]
                if len(objects) > 1 or objects and "Case=Acc" not in objects[0][5]:
                    continue
                kind = "transitive" if objects else "intransitive"
                parameters = {"person": attrs["Person"]}
            if parameters is None:
                continue
            record = {"lemma": lemma, "kind": kind, **parameters, "features": attrs, "sentence_id": identifier}
            key = json.dumps([lemma, kind, parameters], sort_keys=True)
            entries[surface].setdefault(key, record)
    for lemma, frame in ditransitive_frames.items():
        for surface, form in finite_forms[lemma].items():
            parameters = {"person": form["features"]["Person"]}
            record = {"lemma": lemma, "kind": "ditransitive", **parameters, **form, "frame_evidence": frame}
            key = json.dumps([lemma, "ditransitive", parameters], sort_keys=True)
            entries[surface].setdefault(key, record)
    document = {"version": 2, "source": "UD Greek GDT r2.17 · training split", "source_url": SOURCE_URL,
                "source_sha256": SOURCE_SHA256, "license": "CC BY-NC-SA 3.0",
                "attribution": "Greek Dependency Treebank, ILSP / Athena Research Center; Prokopis Prokopidis and Haris Papageorgiou.",
                "note": "Corpus-derived lexical/frame hypotheses. Forms and features are attested annotations; syntactic occurrence does not establish exhaustive lexical valency. Ditransitive candidates pair an attested form with the same lemma's attested accusative obj and genitive iobj frame; the two source occurrences are recorded separately. DS independently checks the instantiated programs.",
                "entries": {k: list(v.values()) for k, v in sorted(entries.items())}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps({"forms": len(entries), "analyses": sum(map(len, entries.values())), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/greek-lexicon/gdt-train.json"))
    args = parser.parse_args()
    build(args.source, args.output)
