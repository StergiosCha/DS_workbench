"""DyLan Dynamic Syntax + TTR core (Python port of qmul.ds)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from dylan.formula.ttr_record_type import TTRRecordType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dylan.parser.interactive_context_parser import InteractiveContextParser

__all__ = ["TTRRecordType", "InteractiveContextParser", "__version__"]

try:
    __version__: str = version("dynamicsyntax")
except PackageNotFoundError:  # pragma: no cover - editable checkout without metadata
    __version__ = "0.0.0"


def __getattr__(name: str):
    # Keep the public conveniences without loading DS when a different engine
    # imports dylan.experiments. The exported classes themselves are unchanged.
    if name == "InteractiveContextParser":
        from dylan.parser.interactive_context_parser import InteractiveContextParser
        value = InteractiveContextParser
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
