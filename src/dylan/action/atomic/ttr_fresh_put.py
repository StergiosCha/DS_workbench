"""``ttrput`` — add a freshened TTR formula as ``Fo`` (Java ``TTRFreshPut``)."""

from __future__ import annotations

import logging
import re
from typing import Any

from dylan.action.atomic.effect import Effect
from dylan.formula.formula import Formula
from dylan.formula.ttr_formula import TTRFormula
from dylan.tree.label.labels import FormulaLabel
from dylan.tree.tree import Tree

logger = logging.getLogger(__name__)

_PATTERN = re.compile(r"(?i)ttrput\((.+)\)")


class TTRFreshPut(Effect):
    """Put ``Fo(freshen(ttr))`` when no formula label exists (Java ``TTRFreshPut``)."""

    FUNCTOR = "ttrput"

    def __init__(self, ttr: TTRFormula) -> None:
        self.ttr = ttr

    @classmethod
    def parse(cls, string: str) -> TTRFreshPut | None:
        m = _PATTERN.fullmatch(string.strip())
        if not m:
            return None
        inner = m.group(1).strip()
        f = Formula.create(inner)
        if isinstance(f, TTRFormula):
            return cls(f)
        raise ValueError(f"ttrput requires a supported TTR formula: {inner}")

    def exec_tuple_context(self, tree: Tree, context: Any) -> Tree | None:
        """Freshen against the branch receiving the formula, then insert it.

        The dialogue context need not be a tree. More importantly, its current
        tuple may be the source of several speculative branches: allocating
        names there would mutate sibling searches and make replay unstable.
        The branch carries its own cloned variable pools.
        """
        node = tree.pointed_node
        if node.get_formula_label() is not None:
            logger.warning("ttrput: node already has Fo; leaving tree")
            return tree
        fresh = self.ttr.freshen_vars(tree)
        node.add_label(FormulaLabel(fresh.instantiate()))
        return tree

    def instantiate(self) -> Effect:
        return TTRFreshPut(self.ttr.clone())  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        """Java ``TTRFreshPut.equals``: mutual TTR subsumption (not string identity)."""
        if not isinstance(other, TTRFreshPut):
            return False
        if self.ttr is None:
            return other.ttr is None
        if other.ttr is None:
            return False
        return bool(self.ttr.subsumes(other.ttr) and other.ttr.subsumes(self.ttr))

    def __hash__(self) -> int:
        """Match Java ``Effect.hashCode`` (``toString``-based); equals may be coarser via subsumption."""
        return hash(str(self))

    def __str__(self) -> str:
        return f"{self.FUNCTOR}({self.ttr})"
