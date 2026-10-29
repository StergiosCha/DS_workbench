"""Observed input and opaque engine results; no shared syntactic ontology."""

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Protocol


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Observation:
    text: str
    left_context: str = ""
    task: str = "fragment"

    def __post_init__(self):
        if not isinstance(self.task, str) or self.task not in {"fragment", "sentence"}:
            raise ValueError("Task must be fragment or sentence")
        if not isinstance(self.text, str) or not isinstance(self.left_context, str):
            raise ValueError("Observed text and context must be strings")
        if not self.text.strip() or len((self.left_context + " " + self.text).split()) > 40:
            raise ValueError("Provide 1–40 observed words including context")

    def to_dict(self):
        return asdict(self)


@dataclass
class Analysis:
    engine: str
    observation: Observation
    status: str
    supported: bool
    complete: bool
    cues: tuple[tuple[str, ...], ...] = ()
    meanings: tuple[str, ...] = ()
    states: list[dict] = field(default_factory=list)
    counters: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class GrammarEngine(Protocol):
    def analyse(self, observation: Observation, *, trace: bool = True) -> Analysis: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class Configuration:
    grammar: str = "ds-english-v1"
    memory: str = "exponential-v1"
    representation: str = "native"
    measurement: str = "lognormal-v1"
    decay: float = .8

    def to_dict(self):
        return asdict(self)

    @property
    def identity(self):
        return digest(self.to_dict())
