"""Build the theory-to-implementation research report as standalone TeX/PDF."""
from pathlib import Path
import tempfile

import build_walkthrough_latex as renderer


def main():
    renderer.SOURCE = renderer.ROOT / "docs/research/ds-theoretical-coverage.md"
    renderer.TEX = renderer.SOURCE.with_suffix(".tex")
    renderer.PDF = renderer.SOURCE.with_suffix(".pdf")
    renderer.BUILD = Path(tempfile.gettempdir()) / "ds-theoretical-coverage-latex"
    preamble = renderer.PREAMBLE.split(r"\begin{document}")[0]
    preamble = preamble.replace("docs/workbench-walkthrough.md by scripts/build_walkthrough_latex.py",
                                "docs/research/ds-theoretical-coverage.md by scripts/build_ds_research_report.py")
    preamble = preamble.replace("Complete Technical Walkthrough", "Theoretical Coverage and Implementation")
    preamble = preamble.replace("Technical walkthrough", "Theory and implementation")
    renderer.PREAMBLE = preamble + r"""\begin{document}
\begin{titlepage}
\thispagestyle{empty}
\vspace*{20mm}
{\small\color{DSmuted}DYNAMIC SYNTAX LABORATORY\par}
\vspace{14mm}
{\fontsize{33}{38}\selectfont\bfseries\color{DSgreen}Dynamic Syntax\par}
\vspace{5mm}
{\Large Theoretical coverage and an implementation programme\par}
\vspace{10mm}
{\color{DSgreen}\rule{\linewidth}{0.7pt}}
\vspace{8mm}
{\large A source-led map of construction families, semantic obligations,
current workbench coverage and the next implementation stages.\par}
\vspace{10mm}
18 categories; 91 tracked topics. Topics are research entries, not a count of
implemented or independently verified analyses.\par
\vspace{8mm}
First implementation: named-head English nonrestrictive relatives through
LINK, head copying, MERGE and supplemental assertion in Classical and
Constructive DS.\par
\vfill
Research and implementation audit: 6--7 October 2026.\par
Targeted literature review; version and evidence boundaries stated throughout.\par
\end{titlepage}
\pagenumbering{roman}
\tableofcontents
\clearpage
\pagenumbering{arabic}
"""
    renderer.main()


if __name__ == "__main__":
    main()
