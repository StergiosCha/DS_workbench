"""DAG-based parsers (`DAGParser`, `InteractiveContextParser`)."""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dylan.parser.interactive_context_parser import InteractiveContextParser
    from dylan.parser.language_derivation import (
        DEFAULT_LANGUAGE_OUTPUT_DIR,
        LanguageDerivation,
        LanguageDerivationRecord,
    )

__all__ = [
    "DEFAULT_LANGUAGE_OUTPUT_DIR",
    "InteractiveContextParser",
    "LanguageDerivation",
    "LanguageDerivationRecord",
]


def __getattr__(name: str):
    # Importing the lightweight parse_stats submodule must not eagerly import
    # the parser back through the DAG/context modules that are loading it.
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = "interactive_context_parser" if name == "InteractiveContextParser" else "language_derivation"
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
