"""Search counters, independent of trace replay and linguistic judgments."""

from copy import deepcopy
from dataclasses import asdict, dataclass, field, fields


@dataclass
class ParseStats:
    """Allocations and search attempts since the sentence's initial axiom.

    Children are grouped by input-word attempt, including zero for failed words.
    Executions count attempted rules, including failed triggers, but exclude
    display replay. Traversals count successful forward search steps. ``pruned``
    stays zero until the engine actually prunes search alternatives.
    """

    children_built_per_word: list[int] = field(default_factory=list)
    tuples: int = 0
    edges: int = 0
    traversed: int = 0
    backtracks_called: int = 0
    backtracks_ok: int = 0
    computational_execs: int = 0
    lexical_execs: int = 0
    top_n_cuts: list[tuple[str, int]] = field(default_factory=list)
    cap_hits: list[str] = field(default_factory=list)
    pruned: int = 0

    def snapshot(self) -> "ParseStats":
        return deepcopy(self)

    def to_dict(self) -> dict:
        return asdict(self)

    def add(self, other: "ParseStats") -> None:
        """Accumulate independent sentence snapshots for a dialogue request."""
        for item in fields(self):
            left, right = getattr(self, item.name), getattr(other, item.name)
            if isinstance(left, list):
                left.extend(deepcopy(right))
            else:
                setattr(self, item.name, left + right)
