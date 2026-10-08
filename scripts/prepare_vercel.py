"""Stage only the DS runtime, grammars, public evidence and read-only indexes."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def prepare(target):
    target.mkdir(parents=True, exist_ok=True)
    manifest = {}

    def copy(source, relative):
        if source.is_symlink():
            raise ValueError(f"Refusing symlink in deployment inputs: {source}")
        if not source.is_file():
            raise FileNotFoundError(f"Required deployment input is missing: {source}")
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        manifest[relative.as_posix()] = sha256(dest.read_bytes()).hexdigest()

    for name in ("dylan", "dynamicsyntax"):
        for path in (ROOT / "src" / name).rglob("*"):
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix in {".py", ".txt", ".sty", ".json"}
            ):
                copy(path, path.relative_to(ROOT))
    # setup.py normally installs this repository folder as dynamicsyntax.resources.
    for path in (ROOT / "resources").rglob("*"):
        if (
            path.is_file()
            and path.suffix in {".py", ".txt", ".json"}
            and "__pycache__" not in path.parts
        ):
            copy(path, Path("src/dynamicsyntax/resources") / path.relative_to(ROOT / "resources"))
    for path in (ROOT / "workbench").iterdir():
        if path.suffix in {".html", ".js", ".css", ".svg"}:
            copy(path, path.relative_to(ROOT))
    for name in ("brown", "gutenberg"):
        copy(ROOT / f".ds-workbench/corpora/{name}.sqlite3", Path(f"data/corpora/{name}.sqlite3"))
    copy(ROOT / ".ds-workbench/dictionaries/wordnet.sqlite3", Path("data/wordnet.sqlite3"))
    copy(ROOT / "data/greek-clitics/corpus.jsonl", Path("data/greek-clitics/corpus.jsonl"))
    copy(ROOT / "data/greek-lexicon/gdt-train.json", Path("data/greek-lexicon/gdt-train.json"))
    copy(ROOT / "data/coverage/paragraph-baseline.json", Path("data/coverage/paragraph-baseline.json"))
    copy(ROOT / "data/coverage/open-text-results.json", Path("data/coverage/open-text-results.json"))
    copy(ROOT / "LICENSE", Path("LICENSE"))
    for path in (ROOT / "deploy/vercel").iterdir():
        if path.name in {
            "app.py",
            "vercel.json",
            "requirements.txt",
            ".python-version",
            ".vercelignore",
        }:
            copy(path, Path(path.name))
    # Keep only generated inputs and Vercel's project link, never stray local data.
    for path in target.rglob("*"):
        relative = path.relative_to(target)
        if (
            path.is_file()
            and relative.parts[0] != ".vercel"
            and relative.as_posix() not in manifest
            and relative.name != "manifest.json"
        ):
            raise ValueError(
                f"Unexpected file in staging directory: {relative}. Use a fresh output directory."
            )
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    size = sum((target / name).stat().st_size for name in manifest)
    print(
        json.dumps(
            {"directory": str(target), "files": len(manifest), "size_mib": round(size / 1024**2, 2)}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".ds-workbench/vercel")
    prepare(parser.parse_args().output.resolve())
