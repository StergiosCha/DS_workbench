"""Select bounded left contexts from a fixed, independently chosen UD training corpus."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from dylan.hybrid.traces import DSAdapter, digest


def conllu_sentences(path):
    words, tags, identity = [], [], ""
    with Path(path).open() as stream:
        for line in stream:
            line = line.rstrip("\n")
            if not line:
                if words:
                    yield identity, words, tags
                words, tags, identity = [], [], ""
            elif line.startswith("# sent_id = "):
                identity = line.split(" = ", 1)[1]
            elif not line.startswith("#"):
                fields = line.split("\t")
                if fields[0].isdigit():
                    words.append(fields[1])
                    tags.append(fields[3])
    if words:
        yield identity, words, tags


def build_bank(corpus, *, max_contexts=24, max_words=6):
    adapter = DSAdapter()
    records = [{"id": "empty", "text": "", "pos": [], "source_sentence": None}]
    selected, attempted = set(), set()
    try:
        for identity, words, tags in conllu_sentences(corpus):
            for size in range(1, min(max_words, len(words)) + 1):
                prefix = " ".join(words[:size])
                if prefix.lower() in attempted:
                    continue
                attempted.add(prefix.lower())
                if not adapter.parser.lexicon.lookup(words[size - 1].lower()):
                    break
                result = adapter.probe(prefix, trace=False)
                if result["status"] != "recognized_fragment":
                    break
                key = (tuple(tags[:size]), tuple(p["requirement"] for p in result["state"]["pending"]))
                if key in selected:
                    continue
                selected.add(key)
                records.append({"id": f"ewt:{identity}:{size}", "text": prefix,
                                "pos": tags[:size], "source_sentence": identity,
                                "state_sha256": digest(result["state"])})
                if len(records) >= max_contexts:
                    break
            if len(records) >= max_contexts:
                break
        return {"schema": 1, "source": "UD English EWT r2.15, training split",
                "source_url": "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/r2.15/en_ewt-ud-train.conllu",
                "source_sha256": hashlib.sha256(Path(corpus).read_bytes()).hexdigest(),
                "policy": "first distinct POS/pending-requirement prefix in corpus order; no experimental outcomes used",
                "grammar": adapter.grammar, "grammar_sha256": adapter.fingerprint,
                "max_words": max_words, "contexts": records,
                "prior": "uniform over this fixed finite bank; not a fitted natural-context distribution"}
    finally:
        adapter.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/hybrid/data/contexts.json"))
    parser.add_argument("--max-contexts", type=int, default=24)
    args = parser.parse_args()
    bank = build_bank(args.corpus, max_contexts=args.max_contexts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bank, indent=2))
    counts = {2: Counter(), 3: Counter()}
    for _, _, tags in conllu_sentences(args.corpus):
        for width, counter in counts.items():
            counter.update(" ".join(tags[i:i + width]) for i in range(len(tags) - width + 1))
    (args.output.parent / "pos-frequencies.json").write_text(json.dumps({
        "source": bank["source"], "source_sha256": bank["source_sha256"],
        "counts": {str(n): dict(c) for n, c in counts.items()}}, indent=2))
    print(f"Selected {len(bank['contexts'])} contexts from {bank['source']}")


if __name__ == "__main__":
    main()
