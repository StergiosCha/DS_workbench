"""Generate native, reproducible LingEmbed examples without model calls."""

import argparse
import json
from pathlib import Path

from dylan.experiments.contracts import Observation
from dylan.experiments.lingembed import export_analysis
from dylan.experiments.registry import create_engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/lingembed/examples"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    examples = [("ds-english", "ds-english-v1", "John likes Mary"),
                ("ccg-english", "ccg-incremental-v1", "John likes Mary"),
                ("ds-greek", "ds-greek-v1", "ο άνθρωπος περπατάει")]
    for name, identifier, text in examples:
        engine = create_engine(identifier)
        try:
            analysis = engine.analyse(Observation(text, task="sentence"))
            assert analysis.supported, (identifier, analysis.status)
            exported = export_analysis(analysis)
            (args.output / f"{name}.json").write_text(
                json.dumps(exported, ensure_ascii=False, indent=2) + "\n")
        finally:
            engine.close()
    print(f"Exported {len(examples)} native traces to {args.output}")


if __name__ == "__main__":
    main()
