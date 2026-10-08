"""``put(label)`` effect — add a label at the pointed node (Java ``Put``)."""

from __future__ import annotations

import logging
import re

from dylan.action.atomic.effect import Effect
from dylan.formula.formula_metavariable import FormulaMetavariable
from typing import Any
from dylan.tree.label.labels import FormulaLabel, Label, UnaryPredicateLabel, label_factory_create
from dylan.tree.tree import Tree

logger = logging.getLogger(__name__)

_PUT_RE = re.compile(r"(?i)put\((.+)\)")


class Put(Effect):
    """Add a label to the pointed node."""

    FUNCTOR = "put"

    def __init__(self, label: Label) -> None:
        self.label = label

    @classmethod
    def parse(cls, string: str) -> Put | None:
        """Parse ``put(?ty(e))`` etc.; return ``None`` if no match."""
        m = _PUT_RE.fullmatch(string.strip())
        if not m:
            return None
        lab = label_factory_create(m.group(1).strip())
        return cls(lab)

    def exec_tuple_context(self, tree: Tree, context: Any) -> Tree | None:
        node = tree.pointed_node
        label = self.label.instantiate()
        if isinstance(label, UnaryPredicateLabel) and label.predicate.lower() == "case":
            if any(isinstance(old, UnaryPredicateLabel) and old.predicate.lower() == "case"
                   and old.arg != label.arg for old in node.labels):
                logger.debug("put: incompatible Case decorations at %s", node.address)
                return None
        if isinstance(label, FormulaLabel):
            old = node.get_formula()
            new = label.get_formula()
            if isinstance(old, FormulaMetavariable) and isinstance(new, FormulaMetavariable):
                if old.restriction and new.restriction and old.restriction != new.restriction:
                    logger.debug("put: incompatible clitic restrictions at %s", node.address)
                    return None
                if old.restriction:
                    return tree  # Keep the established restriction on a collapsed node.
        if node.contains(label):
            logger.debug("put: label %s already present at %s", label, node.address)
            return tree
        tree.put_label(label)
        return tree

    def instantiate(self) -> Effect:
        """Fresh effect with label metavariables resolved (Java ``Put.instantiate``)."""
        return Put(self.label.instantiate())

    def __str__(self) -> str:
        return f"put({self.label})"
