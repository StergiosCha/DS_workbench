"""Generate bounded lexical ambiguity and mutually exclusive optional choices."""

from pathlib import Path
import shutil


def generate(source, target, k=1, m=0):
    source, target = Path(source), Path(target)
    shutil.copytree(source, target)
    lexicon = target / "lexicon.txt"
    lines = lexicon.read_text().splitlines()
    lexicon.write_text(
        "\n".join(
            line
            for line in lines
            for _ in range(k if line.strip() and not line.lstrip().startswith("//") else 1)
        )
        + "\n"
    )
    rules = target / "computational-actions.txt"
    with rules.open("a") as out:
        for i in range(m):
            out.write(
                f"\nprobe-{i}\nIF ?Ty(mltt:Prop)\n   ¬[+PROBE]\nTHEN put([+PROBE])\n     put([+PROBE{i}])\nELSE abort\n"
            )
    return target
