import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from dylan.experiments.ccg_engine import CCGEngine, Chart
from dylan.experiments.contracts import Observation, digest
from dylan.experiments.registry import create_engine
from dylan.hybrid import ccg

ROOT = Path(__file__).resolve().parents[1]


def test_ccg_and_custom_engine_do_not_import_ds():
    code = '''
import sys
from dylan.experiments.contracts import Analysis, Configuration, Observation
from dylan.experiments.host import Session
from dylan.experiments.registry import register_grammar
session = Session(Configuration(grammar="ccg-incremental-v1"))
assert session.observe(Observation("John walks"))["analysis"]["complete"]
session.close()
class Third:
    def __init__(self, identifier): self.identifier = identifier
    def analyse(self, observation, *, trace=True):
        return Analysis(self.identifier, observation, "accepted", True, True,
                        (("custom", "cue"),), states=[{"opaque": 42}])
    def close(self): pass
register_grammar("custom", dict(family="Other",language="en",role="test",processing="declared",
                 semantics="opaque",reference="test fixture",max_words=40), Third)
session = Session(Configuration(grammar="custom"))
assert session.observe(Observation("something"))["analysis"]["states"] == [{"opaque": 42}]
assert "dylan.experiments.ds_engine" not in sys.modules
assert "dylan.hybrid.traces" not in sys.modules
assert not any(k.startswith("dylan.parser") for k in sys.modules)
'''
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)


@pytest.mark.parametrize("identifier", ["ccg-original-v1", "ccg-incremental-v1", "ccg-application-v1"])
@pytest.mark.parametrize("text", ["John likes Mary", "will make his", "John and Mary", "John will read the book"])
def test_incremental_chart_matches_reference_combinator_results(identifier, text):
    engine = CCGEngine(identifier)
    result = engine.analyse(Observation(text))
    reference = ccg.parse(text, vocabulary=engine.vocabulary, composition=engine.composition, type_raising=engine.type_raising)
    def signature(values):
        return {(a["category"], a["meaning"]) for a in values}
    assert signature(result.provenance["analyses"]) == signature(reference["analyses"])


def test_lazy_public_exports_keep_existing_classes():
    import dylan
    from dylan.formula.ttr_record_type import TTRRecordType
    from dylan.parser.interactive_context_parser import InteractiveContextParser
    assert dylan.TTRRecordType is TTRRecordType
    assert dylan.InteractiveContextParser is InteractiveContextParser
    assert set(dylan.__all__) <= set(dir(dylan))
    with pytest.raises(AttributeError):
        getattr(dylan, "unknown_export")


@pytest.mark.parametrize("module", ["dylan.hybrid.traces", "dylan.nlp.types", "dylan.action.lexical_action",
                                    "dylan.induction.em_learner.record_type_corpus", "dynamicsyntax"])
def test_ds_modules_import_independently_without_bootstrap_order(module):
    subprocess.run([sys.executable, "-c", f"import {module}"], check=True, capture_output=True, text=True)


def test_prefix_states_are_stable_and_composition_changes_licensing():
    engine = CCGEngine("ccg-incremental-v1")
    prefix = engine.analyse(Observation("John will read"))
    longer = engine.analyse(Observation("John will read the book"))
    assert prefix.states == longer.states[:3]
    assert engine.analyse(Observation("will make his")).supported
    assert not CCGEngine("ccg-application-v1").analyse(Observation("will make his")).supported


def test_ccg_reports_coverage_and_limits_without_grammar_judgments():
    engine = CCGEngine("ccg-incremental-v1")
    assert engine.analyse(Observation("John zzzz")).status == "unsupported_lexicon"
    assert engine.analyse(Observation("John " * 13)).status == "unsupported_length"
    assert engine.analyse(Observation("John John")).status == "no_derivation"
    assert not engine.analyse(Observation("likes", task="sentence")).supported
    assert engine.analyse(Observation("likes", task="fragment")).supported
    chart = Chart(cap=1)
    chart.append("john", engine.vocabulary["john"])
    assert chart.limited


def test_frozen_baseline_sources_have_not_changed():
    reference = json.loads((ROOT / "data/experiments/references-v1.json").read_text())
    for path, expected in reference["files"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path


@pytest.mark.parametrize("index", range(5))
def test_native_ds_adapter_preserves_frozen_states_and_action_traces(index):
    ref = json.loads((ROOT / "data/experiments/references-v1.json").read_text())["cases"][index]
    grammar = "ds-greek-poly-v1" if ref["extensions"] else "ds-greek-v1" if "smg" in ref["grammar"] else "ds-english-v1"
    engine = create_engine(grammar)
    try:
        result = engine.analyse(Observation(ref["text"], task="sentence" if ref["complete"] else "fragment"))
    finally:
        engine.close()
    assert result.status == ref["status"]
    assert result.provenance["grammar_sha256"] == ref["grammar_sha256"]
    assert digest(result.provenance["native_state"]) == ref["state_sha256"]
    fields = ("word", "before", "after", "lexical_candidates", "selected_actions")
    assert digest([{k: f[k] for k in fields} for f in result.states]) == ref["frames_sha256"]
