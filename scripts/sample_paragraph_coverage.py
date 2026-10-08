"""Freeze a reproducible unseen-text sample before running the DS parser.

English units are real blank-line paragraphs. GDT does not preserve Greek
paragraph boundaries: Greek units are three consecutive sentences from one
held-out document, explicitly labelled as passages instead of original paragraphs.
No lexical or parsing outcome is used in sampling.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import zipfile

from dylan.paragraph_workbench import sentence_spans

GREEK_HASH = "30cb5881ce6f8ba628de88853a4c105e716a365e8fcd9024a85befe41165c260"


def sample(english, greek, count, seed):
    rng = random.Random(seed)
    candidates = []
    english_digest = sha256(english.read_bytes()).hexdigest()
    with zipfile.ZipFile(english) as archive:
        for filename in sorted(archive.namelist()):
            if not filename.endswith(".txt"):
                continue
            text = archive.read(filename).decode("latin-1")
            for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]*)*", text):
                passage = match.group().strip()
                if 40 <= len(passage.split()) <= 160 and 2 <= len(sentence_spans(passage, "en")) <= 8:
                    candidates.append({"language": "en", "unit": "original paragraph", "text": passage,
                        "document": filename, "source_start": match.start(), "source_end": match.end(),
                        "source_url": "https://www.nltk.org/nltk_data/", "source_archive_sha256": english_digest,
                        "source_encoding": "latin-1", "license": "Project Gutenberg source notices apply; public-domain literature in the US."})
    rows = rng.sample(candidates, count)
    content = greek.read_bytes()
    if sha256(content).hexdigest() != GREEK_HASH:
        raise ValueError("Expected pinned Greek GDT r2.17 test split.")
    docs, current = [], []
    for block in content.decode().split("\n\n"):
        fields = dict(line[2:].split(" = ", 1) for line in block.splitlines() if line.startswith("# ") and " = " in line)
        if "newdoc id" in fields and current:
            docs.append(current)
            current = []
        if fields.get("text"):
            current.append(fields)
    if current:
        docs.append(current)
    candidates = []
    for doc in docs:
        for i in range(0, len(doc) - 2, 3):
            selected = doc[i:i+3]
            passage = " ".join(s["text"] for s in selected)
            if 40 <= len(passage.split()) <= 160:
                candidates.append({"language": "el", "unit": "three consecutive source sentences; original paragraph boundaries unavailable",
                    "text": passage, "sentence_ids": [s["sent_id"] for s in selected],
                    "source_url": "https://raw.githubusercontent.com/UniversalDependencies/UD_Greek-GDT/r2.17/el_gdt-ud-test.conllu",
                    "source_sha256": GREEK_HASH, "license": "CC BY-NC-SA 3.0",
                    "attribution": "Greek Dependency Treebank, ILSP/Athena RC; Prokopidis and Papageorgiou."})
    rows.extend(rng.sample(candidates, count))
    for i, row in enumerate(rows):
        row["id"] = f"{row['language']}-{i+1}"
        row["text_sha256"] = sha256(row["text"].encode()).hexdigest()
    return {"seed": seed, "selection": "Uniform without replacement after length (40–160 whitespace tokens) and unit-boundary filters; no grammar or lexical filtering.",
        "note": "A small engineering baseline, not a representative population accuracy estimate. Once inspected, freeze this sample as regression data and use fresh text for future held-out claims.",
        "passages": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("english", type=Path)
    parser.add_argument("greek", type=Path)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20261001)
    parser.add_argument("--output", type=Path, default=Path("data/coverage/unseen-passages.json"))
    args = parser.parse_args()
    args.output.write_text(json.dumps(sample(args.english, args.greek, args.count, args.seed), ensure_ascii=False, indent=2) + "\n")
    print(str(args.output))
