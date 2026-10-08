"""Check local release archives for required handover files and private paths."""

import argparse
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

PRIVATE_PARTS = {".claude", ".codex", ".cursor", ".agents", ".ds-workbench", ".vercel",
                 ".git", ".venv", "__pycache__"}


def check(directory):
    wheels = sorted(directory.glob("*.whl"))
    sources = sorted(directory.glob("*.tar.gz"))
    assert wheels and sources, "Build both a wheel and source distribution."
    for archive in [*wheels, *sources]:
        if archive.suffix == ".whl":
            with zipfile.ZipFile(archive) as stream:
                names = stream.namelist()
            required = ["dynamicsyntax/workbench_assets/index.html",
                        "dynamicsyntax/workbench_assets/app.js",
                        "dynamicsyntax/workbench_data/greek-lexicon/gdt-train.json",
                        "dynamicsyntax/grammars/2026-english-mltt/semantics.json",
                        "dylan/workbench_paths.py"]
            assert all(name in names for name in required), archive
            assert any(name.endswith("licenses/LICENSE") for name in names), archive
        else:
            with tarfile.open(archive) as stream:
                names = [str(PurePosixPath(name).relative_to(PurePosixPath(name).parts[0]))
                         for name in stream.getnames()]
            required = ["CONTRIBUTING.md", "docs/community/extending.md",
                        "examples/community/extend_grammar.py", "scripts/check_installed_workbench.py",
                        "scripts/build_nonrestrictive_extensions.py", "tests/test_nonrestrictive_relatives.py",
                        "workbench/index.html", "licenses/DyLan-LGPL-3.0.txt", "uv.lock"]
            assert all(name in names for name in required), archive
        for name in names:
            path = PurePosixPath(name)
            assert not PRIVATE_PARTS.intersection(path.parts), (archive, name)
            assert path.name != "HANDOVER.md", (archive, name)
            assert not path.name.startswith(".env"), (archive, name)
            assert ".sqlite3" not in path.name, (archive, name)
        print(f"Checked {archive.name}: {len(names)} entries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    check(parser.parse_args().directory)
