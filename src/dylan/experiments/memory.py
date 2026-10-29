"""Interchangeable sequence memories over opaque, namespaced cue identities."""

from dataclasses import dataclass, field
import math


@dataclass
class Memory:
    kind: str
    decay: float = .8
    time: int = 0
    values: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.kind, str) or self.kind not in {"none-v1", "count-v1", "exponential-v1"}:
            raise ValueError("Unknown memory component")
        if type(self.decay) not in {int, float} or not math.isfinite(self.decay) or not 0 < self.decay <= 1:
            raise ValueError("Memory decay must be finite and in (0, 1]")

    def strength(self, cue):
        if self.kind == "none-v1":
            return 0.
        value, last = self.values.get(tuple(cue), (0., self.time - 1))
        return value * (self.decay ** (self.time - last - 1) if self.kind == "exponential-v1" else 1.)

    def activation(self, cues):
        unique = set(map(tuple, cues))
        return sum(math.log1p(self.strength(cue)) for cue in unique) / len(unique) if unique else 0.

    def observe(self, cues):
        for cue in set(map(tuple, cues)):
            old = self.strength(cue)
            self.values[cue] = (old * self.decay + 1. if self.kind == "exponential-v1" else old + 1., self.time)
        self.time += 1

    def snapshot(self):
        return {"component": self.kind, "time": self.time, "decay": self.decay,
                "stored_cues": len(self.values)}
