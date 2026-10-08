"""Compile the standalone Beamer deck, optionally with presenter notes."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/ds-workbench-slides.tex"
BUILD = Path(tempfile.gettempdir()) / "ds-workbench-slides-latex"


def build(notes=False):
    executable = shutil.which("xelatex")
    if not executable:
        raise SystemExit("XeLaTeX is required (TeX Live or MacTeX with Beamer and Unicode fonts).")
    BUILD.mkdir(parents=True, exist_ok=True)
    outputs = []
    for with_notes in ([False, True] if notes else [False]):
        name = "ds-workbench-slides" + ("-notes" if with_notes else "")
        source = r"\def\DSnotes{1}\input{ds-workbench-slides.tex}" if with_notes else SOURCE.name
        command = [executable, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
                   f"-output-directory={BUILD}", f"-jobname={name}", source]
        for run in range(2):
            completed = subprocess.run(command, cwd=SOURCE.parent, text=True, capture_output=True)
            (BUILD / f"{name}-run-{run + 1}.txt").write_text(completed.stdout + completed.stderr)
            if completed.returncode:
                raise SystemExit(f"XeLaTeX failed; see {BUILD / (name + '-run-' + str(run + 1) + '.txt')}")
        log = (BUILD / (name + ".log")).read_text(errors="replace")
        overfull = re.findall(r"Overfull \\[hv]box[^\n]*", log)
        missing = re.findall(r"Missing character:[^\n]*", log)
        if overfull or missing:
            raise SystemExit(json.dumps({"document": name, "overfull": overfull,
                                         "missing_characters": missing, "log": str(BUILD / (name + ".log"))}, indent=2))
        target = SOURCE.parent / (name + ".pdf")
        shutil.copyfile(BUILD / (name + ".pdf"), target)
        outputs.append(str(target))
    print(json.dumps({"source": str(SOURCE), "pdfs": outputs, "build_logs": str(BUILD),
                      "overfull_boxes": 0, "missing_characters": 0}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes", action="store_true", help="Also create a PDF with speaker notes beside each slide.")
    build(parser.parse_args().notes)
