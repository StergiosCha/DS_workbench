"""Typed discourse referents used by native SUBSTITUTION."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Referent:
    symbol: str
    sort: str = "object"
    person: int = 3
    gender: str | None = None
    number: str | None = None
    source: str = "context"
