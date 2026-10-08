"""Check the legacy TTR mirrors; copy from the canonical source only with --write."""

import argparse
import shutil
from dylan.corpus import ROOT

CANONICAL = ROOT / "src/dynamicsyntax/grammars/2015-english-ttr"
MIRRORS = [ROOT / "resources/2015-english-ttr", ROOT / "web/public/grammars/2015-english-ttr"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    differences = []
    for source in sorted(CANONICAL.glob("*.txt")):
        for mirror in MIRRORS:
            target = mirror / source.name
            if not target.exists() or target.read_bytes() != source.read_bytes():
                differences.append(str(target.relative_to(ROOT)))
                if args.write:
                    mirror.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
    print(
        "\n".join(differences) if differences else "Legacy TTR mirrors match the canonical grammar."
    )
    if differences and not args.write:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
