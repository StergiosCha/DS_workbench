"""Explicit compatible packages. Factories import only the chosen grammar engine."""

from dylan.experiments.contracts import Configuration
from dylan.experiments.memory import Memory
from dylan.experiments.measurement import Measurement

GRAMMARS = {
    "ds-english-v1": {"family": "DS", "language": "en", "role": "reference",
        "processing": "native incremental first-success search", "semantics": "native Classical",
        "reference": "DS Workbench c285928; maintained native English fragment", "max_words": 40},
    "ds-greek-v1": {"family": "DS", "language": "el", "role": "reference",
        "processing": "native incremental first-success search", "semantics": "native Classical",
        "reference": "DS Workbench c285928; maintained native SMG fragment", "max_words": 40},
    "ds-greek-poly-v1": {"family": "DS", "language": "el", "role": "hybrid",
        "processing": "native DS plus typed agreement and polydefinite construction", "semantics": "native Classical",
        "reference": "c285928 opt-in polydefinite fragment", "max_words": 40},
    "ccg-original-v1": {"family": "CCG", "language": "en", "role": "reference",
        "processing": "incrementally maintained chart; application and harmonic composition", "semantics": "lambda terms",
        "reference": "c285928 CCG fragment, original lexicon, no type raising", "max_words": 12},
    "ccg-incremental-v1": {"family": "CCG", "language": "en", "role": "reference",
        "processing": "incremental chart; application, harmonic composition, NP type raising", "semantics": "lambda terms",
        "reference": "Declared experiment lexicon; combinator schemata after Steedman (2000), not full CCG", "max_words": 12},
    "ccg-application-v1": {"family": "CCG", "language": "en", "role": "ablation",
        "processing": "same chart and experiment lexicon, application only", "semantics": "lambda terms",
        "reference": "composition/type-raising ablation of ccg-incremental-v1", "max_words": 12},
}
MEMORIES = {"none-v1": "No adaptation", "count-v1": "Cumulative cue counts", "exponential-v1": "Exponential recency"}
MEASUREMENTS = {"lognormal-v1": "Lognormal response time", "shifted-lognormal-v1": "Lognormal + fixed 150 ms shift"}
REPRESENTATIONS = {"native": "Engine-declared structural cues", "lexical": "Observed lexical bigrams", "combined": "Lexical + native cues"}
FACTORIES = {}


def register_grammar(identifier, specification, factory):
    """Trusted Python extension point; web payloads cannot name import paths."""
    required = {"family", "language", "role", "processing", "semantics", "reference", "max_words"}
    if not isinstance(identifier, str) or not identifier or identifier in GRAMMARS:
        raise ValueError("A new unique grammar identifier is required")
    if not isinstance(specification, dict) or set(specification) != required or not callable(factory):
        raise ValueError("A grammar needs its complete contract and a callable factory")
    GRAMMARS[identifier] = dict(specification)
    FACTORIES[identifier] = factory


def validate(config):
    if not isinstance(config, Configuration):
        raise ValueError("Expected a configuration")
    if not isinstance(config.grammar, str) or config.grammar not in GRAMMARS:
        raise ValueError("Unknown grammar package")
    if not isinstance(config.representation, str) or config.representation not in REPRESENTATIONS:
        raise ValueError("Unknown representation interface")
    Memory(config.memory, config.decay)
    Measurement(config.measurement)
    return config


def from_dict(value):
    if not isinstance(value, dict) or set(value) - set(Configuration.__dataclass_fields__):
        raise ValueError("Invalid configuration fields; grammar and semantics are compatible packages")
    return validate(Configuration(**value))


def create_engine(identifier):
    validate(Configuration(grammar=identifier))
    if identifier in FACTORIES:
        return FACTORIES[identifier](identifier)
    if GRAMMARS[identifier]["family"] == "DS":
        from dylan.experiments.ds_engine import DSEngine
        return DSEngine(identifier)
    from dylan.experiments.ccg_engine import CCGEngine
    return CCGEngine(identifier)


def catalog():
    return {"schema": 1, "grammars": GRAMMARS, "memories": MEMORIES,
            "representations": REPRESENTATIONS, "measurements": MEASUREMENTS,
            "contract": "Shared observations and tasks; internal state and completion belong to each engine",
            "scope": "Versioned implementation fragments, not exhaustive implementations of framework traditions"}
