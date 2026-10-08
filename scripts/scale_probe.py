"""Measure parser search scaling with a reproducible k-by-m grammar fixture."""

import argparse
import importlib.util
import json
import tempfile
import time
from pathlib import Path
from dylan.corpus import ROOT
from dylan.parser.interactive_context_parser import InteractiveContextParser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/design/search-scaling.md")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "scale_generator", ROOT / "tests/fixtures/scale/generate.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    results = []
    for k, m, top in [
        (1, 0, 0),
        (2, 0, 0),
        (4, 0, 0),
        (8, 0, 0),
        (8, 0, 3),
        (1, 3, 0),
        (1, 6, 0),
        (4, 6, 0),
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            path = generator.generate(
                ROOT / "src/dynamicsyntax/grammars/2026-english-mltt", Path(tmp) / "grammar", k, m
            )
            p = InteractiveContextParser(path, top_n=top)
            started = time.perf_counter()
            try:
                r = p.parse("every doctor examined a patient.")
                results.append(
                    {
                        "k": k,
                        "m": m,
                        "top_n": top,
                        "ok": r.ok,
                        "ms": round((time.perf_counter() - started) * 1000, 2),
                        "stats": r.stats.to_dict(),
                    }
                )
            finally:
                p.close()
    lines = [
        "# Search scaling",
        "",
        "Measured with `scripts/scale_probe.py` and the committed synthetic fixture. k duplicates each lexical row; m adds mutually exclusive optional choices. Counts exclude display replay. Timings are machine-dependent.",
        "",
        "| k | m | top_n | ok | tuples | computational attempts | lexical attempts | max children | ms |",
        "|---:|---:|---:|:---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        s = r["stats"]
        lines.append(
            f"| {r['k']} | {r['m']} | {r['top_n']} | {r['ok']} | {s['tuples']} | {s['computational_execs']} | {s['lexical_execs']} | {max(s['children_built_per_word'], default=0)} | {r['ms']} |"
        )
    args.output.write_text("\n".join(lines) + "\n")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
