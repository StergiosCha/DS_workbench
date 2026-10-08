"""Native mathematical exports use their own terms and need no TTR styles."""

import shutil

import pytest

from dynamicsyntax import parse
from dylan.formula.mltt.terms import parse_expr


@pytest.mark.parametrize("backend,symbol", [("mltt", r"\Sigma"), ("classical", r"\varepsilon")])
def test_to_latex_semantics_document_native(backend, symbol, tmp_path):
    result = parse("a man walks.", f"2026-english-{backend}")
    exported = result.to_latex("semantics", write_tex=tmp_path / "meaning.tex")
    assert symbol in exported.tex
    assert "dsttr.sty" not in exported.tex
    assert "mathit{walk}" in exported.tex
    assert exported.tex_path.read_text() == exported.tex
    if shutil.which("latexmk") or shutil.which("pdflatex"):
        compiled = result.to_latex("semantics", compile_tex=True, pdf_out=tmp_path / "meaning.pdf")
        assert compiled.exit_code == 0 and compiled.pdf_path.is_file()


@pytest.mark.parametrize("source,symbol", [
    ("lam(x,arrow(human,Prop),x)", r"\lambda"),
    ("pi(x,man,walk(x))", r"\Pi"),
    ("and(walk(john),shout(mary))", r"\land"),
    ("fst(pair(john,unit))", r"\pi_1"),
    ("tau(x,e,man(x))", r"\tau"),
    ("pred_name", r"pred\_name"),
])
def test_native_tex_operators_and_escaping(source, symbol):
    assert symbol in parse_expr(source).to_tex()
