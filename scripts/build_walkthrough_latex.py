"""Render the complete Markdown walkthrough as standalone LaTeX and a PDF.

Requires pandoc and XeLaTeX. Run from any directory. The generated .tex embeds
its diagram and needs no external images or custom style files.
"""

from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/workbench-walkthrough.md"
TEX = SOURCE.with_suffix(".tex")
PDF = SOURCE.with_suffix(".pdf")
BUILD = Path(tempfile.gettempdir()) / "ds-workbench-walkthrough-latex"

PREAMBLE = r"""% !TeX program = xelatex
% Generated from docs/workbench-walkthrough.md by scripts/build_walkthrough_latex.py.
% Compile twice with XeLaTeX for the contents and hyperlinks.
% This source is standalone; the process diagram is drawn in TikZ.
\documentclass[11pt,a4paper]{article}
\usepackage[margin=24mm,headheight=15pt,headsep=8mm,footskip=12mm]{geometry}
\usepackage{fontspec}
\usepackage{unicode-math}
\IfFontExistsTF{STIXGeneral}
  {\setmainfont{STIXGeneral}}
  {\setmainfont{Libertinus Serif}}
\IfFontExistsTF{Menlo}
  {\setmonofont[Scale=0.82]{Menlo}}
  {\setmonofont[Scale=0.86]{DejaVu Sans Mono}}
\setmathfont{STIX Two Math}
\usepackage{microtype}
\usepackage{amsmath}
\usepackage{graphicx,booktabs,longtable,array,calc}
\usepackage{fvextra}
\usepackage{newunicodechar}
\newunicodechar{⊤}{\ensuremath{\top}}
\usepackage{xcolor}
\definecolor{DSgreen}{HTML}{294F43}
\definecolor{DSmuted}{HTML}{56655F}
\definecolor{DSpale}{HTML}{F1F5F2}
\usepackage{xurl}
\usepackage[colorlinks=true,linkcolor=DSgreen,urlcolor=DSgreen,filecolor=DSgreen,
  pdftitle={DS Workbench: Complete Technical Walkthrough},
  pdfsubject={Dynamic Syntax, Classical and Constructive semantics, TTR, architecture and coverage},
  bookmarksnumbered=true]{hyperref}
\urlstyle{tt}
\usepackage{bookmark}
\usepackage{titlesec,needspace,etoolbox}
\usepackage{fancyhdr}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\textcolor{DSmuted}{DS Workbench}}
\fancyhead[R]{\small\textcolor{DSmuted}{Technical walkthrough}}
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.3pt}
\renewcommand{\footrulewidth}{0pt}
\titleformat{\section}{\Large\bfseries\color{DSgreen}}{\thesection}{0.65em}{}
\titlespacing*{\section}{0pt}{2.0ex plus 1ex minus .2ex}{1.0ex}
\pretocmd{\section}{\Needspace{7\baselineskip}}{}{}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4.5pt plus 1pt}
\setlength{\emergencystretch}{2em}
\setlength{\LTpre}{8pt}
\setlength{\LTpost}{8pt}
\BeforeBeginEnvironment{longtable}{\Needspace{13\baselineskip}}
\AtBeginEnvironment{longtable}{\small\setlength{\tabcolsep}{5pt}\renewcommand{\arraystretch}{1.16}}
\providecommand{\tightlist}{\setlength{\itemsep}{2pt}\setlength{\parskip}{0pt}}
\widowpenalty=10000
\clubpenalty=10000
\raggedbottom
\begin{document}
\begin{titlepage}
\thispagestyle{empty}
\vspace*{19mm}
{\small\color{DSmuted}\MakeUppercase{Dynamic Syntax Laboratory}\par}
\vspace{13mm}
{\fontsize{36}{41}\selectfont\bfseries\color{DSgreen}DS Workbench\par}
\vspace{4mm}
{\Large Complete technical walkthrough\par}
\vspace{9mm}
{\color{DSgreen}\rule{\linewidth}{0.7pt}}
\vspace{6mm}
{\large Syntax as the growth of transparent semantic representations\par}
\vspace{12mm}
\begin{minipage}{0.90\linewidth}
The DynamicSyntax Python package and its DyLan foundation; the engine, grammar
and application extensions built on it; Classical, Constructive and TTR
interpretations; lexical assistance, corpus integration and verification;
current limitations and a prioritized plan for broader coverage.
\end{minipage}
\vfill
{\color{DSmuted}Checked against the working source on 4 October 2026.\par}
\vspace{3mm}
\href{https://ds-workbench.vercel.app/}{ds-workbench.vercel.app}
\end{titlepage}
\pagenumbering{roman}
\tableofcontents
\clearpage
\pagenumbering{arabic}
"""

DIAGRAM = r"""\begin{figure}[htbp]
\centering
\begin{tikzpicture}[
  box/.style={draw=DSgreen,rounded corners=2pt,fill=DSpale,
    text width=42mm,minimum height=12mm,align=center,inner sep=4pt,font=\small},
  edge/.style={-{Stealth[length=2mm]},draw=DSgreen,thick},
  note/.style={font=\footnotesize,fill=white,inner sep=2pt,text=DSmuted}]
\node[box] (input) at (0,0) {Input and selected grammar};
\node[box] (entries) at (0,-1.65) {Reviewed entries and dictionary/corpus candidates};
\node[box] (ds) at (0,-3.30) {DS parsing and semantic composition};
\node[box] (success) at (0,-5.00) {Complete derivation:\\meaning, assumptions and provenance};
\node[box] (sources) at (7,0) {Retrieve Greek source evidence if enabled};
\node[box] (model) at (7,-1.65) {Model proposes vocabulary, clause relations or corrections};
\node[box] (validate) at (7,-3.30) {Validate schema, citations, features and templates};
\node[box] (compile) at (7,-5.00) {Compile the selected grammar's lexical programs};
\node[box,text width=63mm] (failure) at (3.5,-7.10) {Visible incomplete result:\\budget exhausted or construction unsupported};
\draw[edge] (input) -- (entries);
\draw[edge] (entries) -- (ds);
\draw[edge] (ds) -- node[note,left] {complete} (success);
\draw[edge] (entries.east) -- (3.5,-1.65) -- (3.5,0) -- (sources.west);
\draw[edge] (ds.east) -- (3.5,-3.30) -- (3.5,0);
\node[note,text width=24mm,align=center] at (3.5,0.95) {assistance needed};
\draw[edge] (sources) -- (model);
\draw[edge] (model) -- (validate);
\draw[edge] (validate) -- (compile);
\draw[edge] (compile.south) -- (7,-6.05) -- (-3,-6.05) -- (-3,-3.30) -- (ds.west);
\node[note] at (5.25,-6.05) {bounded retry};
\draw[edge,dashed] (ds.south east) -- (3.5,-4.25) -- (failure.north);
\end{tikzpicture}
\caption{Missing vocabulary can trigger assistance before the first DS attempt;
an incomplete derivation can trigger a correction. Optional Greek retrieval
supplies evidence for the proposal. Compilation and DS execution still determine
whether a derivation completes. Calls and retries are bounded.}
\end{figure}
"""


def transform(value):
    if isinstance(value, list):
        return [transform(item) for item in value]
    if not isinstance(value, dict):
        return value
    kind, content = value.get("t"), value.get("c")
    if kind == "Header":
        level, attrs, inlines = content
        if level >= 2:
            if level == 2 and inlines and inlines[0].get("t") == "Str" and re.fullmatch(r"\d+\.", inlines[0]["c"]):
                inlines = inlines[2:]
            return {"t": "Header", "c": [level - 1, attrs, transform(inlines)]}
    if kind == "CodeBlock":
        attrs, source = content
        if "mermaid" in attrs[1]:
            return {"t": "RawBlock", "c": ["latex", DIAGRAM]}
        # Command characters allow the missing monospace top glyph to be drawn
        # with the math font while preserving all literal code characters.
        escaped = "".join({"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
                           "⊤": r"\ensuremath{\top}"}.get(c, c) for c in source)
        raw = (r"\begin{Verbatim}[fontsize=\small,breaklines=true,breakanywhere=true,"
               r"commandchars=\\\{\},frame=single,rulecolor=\color{DSmuted},framesep=5pt]"
               + "\n" + escaped + "\n" + r"\end{Verbatim}")
        return {"t": "RawBlock", "c": ["latex", raw]}
    if kind == "Code":
        source = content[1]
        if re.fullmatch(r"[A-Za-z0-9_./:-]+", source) and (len(source) > 16 or "/" in source):
            return {"t": "RawInline", "c": ["latex", r"\nolinkurl{" + source + "}"]}
    if kind == "Table":
        count = len(content[2])
        widths = {2: [0.30, 0.70], 3: [0.27, 0.365, 0.365],
                  4: [0.17, 0.27, 0.28, 0.28]}[count]
        content[2] = [[align, {"t": "ColWidth", "c": width}]
                      for (align, _), width in zip(content[2], widths)]
    return {key: transform(item) for key, item in value.items()}


def main():
    doc = json.loads(subprocess.run(
        ["pandoc", str(SOURCE), "-t", "json"], check=True, capture_output=True, text=True
    ).stdout)
    doc["blocks"] = doc["blocks"][1:]  # The cover replaces the Markdown title.
    body = subprocess.run(
        ["pandoc", "-f", "json", "-t", "latex", "--no-highlight", "--number-sections"],
        input=json.dumps(transform(doc)), capture_output=True, text=True, check=True
    ).stdout
    TEX.write_text(PREAMBLE + body + "\n\\end{document}\n")
    BUILD.mkdir(parents=True, exist_ok=True)
    for run in range(3):
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error",
             "-output-directory", str(BUILD), str(TEX)],
            cwd=TEX.parent, capture_output=True, text=True
        )
        (BUILD / f"pass-{run + 1}.txt").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"XeLaTeX failed; inspect {BUILD / f'pass-{run + 1}.txt'}")
    log = (BUILD / TEX.with_suffix(".log").name).read_text(errors="replace")
    if "Missing character:" in log:
        raise RuntimeError(f"A font is missing characters; inspect {BUILD}")
    shutil.copyfile(BUILD / PDF.name, PDF)
    print(json.dumps({"latex": str(TEX), "pdf": str(PDF), "build_logs": str(BUILD),
                      "overfull_boxes": log.count("Overfull ")}, indent=2))


if __name__ == "__main__":
    main()
