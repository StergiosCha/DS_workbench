"""``merge`` — merge a modality target into the pointed node (Java ``Merge``)."""

from __future__ import annotations

import logging
import re
from typing import Any

from dylan.action.atomic.effect import Effect
from dylan.formula.formula_metavariable import FormulaMetavariable
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType, subtype
from dylan.tree.label.labels import BottomLabel, FormulaLabel, Requirement, TypeLabel, UnaryPredicateLabel, label_factory_create
from dylan.tree.node import Node
from dylan.tree.node_address import NodeAddress
from dylan.tree.modality import Modality
from dylan.tree.tree import Tree

logger = logging.getLogger(__name__)

_PATTERN = re.compile(r"(?i)merge\((.+)\)")


def _feature_values(node, feature, theory):
    values = {str(label.arg) for label in node.labels
              if isinstance(label, UnaryPredicateLabel) and label.predicate.lower() == feature}
    formula = node.get_formula()
    metadata = {}
    if isinstance(formula, FormulaMetavariable):
        metadata = theory.get("reference_classes", {}).get(formula.restriction, {})
    elif isinstance(formula, SemanticFormula) and formula.term.kind == "name":
        metadata = theory.get("referents", {}).get(formula.term.name, {})
    if feature in metadata:
        values.add(str(metadata[feature]))
    if feature == "gender":
        values = {{"m": "masc", "f": "fem", "n": "neut"}.get(v, v) for v in values}
    return values


def _combined_node(node: Node, other: Node, theory: dict) -> Node | None:
    """Check a label union on a copy, retaining the most informative values."""
    old_type, new_type = node.get_type(), other.get_type()
    keep_type = old_type or new_type
    if old_type is not None and new_type is not None and old_type != new_type:
        if not (isinstance(old_type, SemanticType) and isinstance(new_type, SemanticType)
                and old_type.backend == new_type.backend == "mltt"):
            logger.debug("merge: incompatible types")
            return None
        if subtype(new_type.term, old_type.term, theory):
            keep_type = new_type
        elif not subtype(old_type.term, new_type.term, theory):
            logger.debug("merge: incompatible semantic types")
            return None
    if keep_type is not None:
        for candidate in (node, other):
            for label in candidate.labels:
                if not (isinstance(label, Requirement) and isinstance(label.inner, TypeLabel)):
                    continue
                required = label.inner.type
                accepts = (required.accepts_requirement(keep_type)
                           if isinstance(required, SemanticType) and isinstance(keep_type, SemanticType)
                           else required == keep_type)
                if not accepts:
                    logger.debug("merge: type does not satisfy the destination requirements")
                    return None
    for feature in ("case", "person", "number", "gender"):
        values = _feature_values(node, feature, theory) | _feature_values(other, feature, theory)
        if len(values) > 1:
            logger.debug("merge: incompatible %s decorations", feature)
            return None
    old, new = node.get_formula(), other.get_formula()
    old_meta, new_meta = isinstance(old, FormulaMetavariable), isinstance(new, FormulaMetavariable)
    if old is not None and new is not None:
        if old_meta and new_meta:
            if old.restriction and new.restriction and old.restriction != new.restriction:
                logger.debug("merge: incompatible clitic restrictions")
                return None
        elif not old_meta and not new_meta and not (old.subsumes(new) or new.subsumes(old)):
            logger.debug("merge: incompatible formulas")
            return None
    # Preserve a concrete target over a placeholder, or its established
    # restriction when both placeholders are compatible.
    keep = old if new is None or (new_meta and (not old_meta or old.restriction)) else new
    combined = Node(node.address, list(node.labels))
    combined.merge_from(other)
    if keep_type is not None:
        combined.add_label(TypeLabel(keep_type))
    if keep is not None:
        combined.add_label(FormulaLabel(keep))
    if combined.address.is_fixed():
        combined.remove_label(label_factory_create("?Ex.Tn(x)"))
    if keep is not None and not isinstance(keep, FormulaMetavariable):
        combined.remove_label(label_factory_create("?Ex.Fo(x)"))
    return combined


class Merge(Effect):
    """Splice a non-locally-fixed node into the current fixed node (Java ``Merge``)."""

    FUNCTOR = "merge"

    def __init__(self, modality: Modality) -> None:
        self.modality = modality

    @classmethod
    def parse(cls, string: str) -> Merge | None:
        m = _PATTERN.fullmatch(string.strip())
        if not m:
            return None
        return cls(Modality.parse(m.group(1).strip()))

    def exec_tuple_context(self, tree: Tree, context: Any) -> Tree | None:
        node = tree.pointed_node
        if not node.is_locally_fixed():
            logger.debug("merge: pointed node not locally fixed")
            return None
        mod_i = self.modality.instantiate()
        other = tree.get_node(mod_i)
        if other is None or other.is_locally_fixed():
            logger.debug("merge: other missing or fixed")
            return None
        if not other.address.subsumes(node.address):
            logger.debug("merge: destination does not refine the unfixed address")
            return None
        source_prefix, target_prefix = str(other.address), str(node.address)
        source_nodes = [(addr, child) for addr, child in tree.items()
                        if str(addr).startswith(source_prefix)]
        planned = {}
        for address, child in source_nodes:
            destination = NodeAddress(target_prefix + str(address)[len(source_prefix):])
            target = tree.get(destination) or Node(destination)
            combined = _combined_node(target, child, tree.semantic_profile)
            if combined is None:
                logger.debug("merge: incompatible descendant at %s", destination)
                return None
            planned[destination] = combined
        remaining = (set(tree) - {address for address, _ in source_nodes}) | set(planned)
        for address, combined in planned.items():
            if any(isinstance(label, BottomLabel) for label in combined.labels):
                prefix = str(address)
                if any(str(child).startswith(prefix) and len(str(child)) > len(prefix)
                       and str(child)[len(prefix)] not in "LB" for child in remaining):
                    logger.debug("merge: terminal restriction conflicts with descendants")
                    return None
        # Nothing is changed until every overlapping descendant is compatible.
        for address, _child in source_nodes:
            del tree[address]
        for address, combined in planned.items():
            if address in tree:
                tree[address].labels = combined.labels
            else:
                tree[address] = combined
        return tree

    def instantiate(self) -> Effect:
        return Merge(self.modality.instantiate())

    def __str__(self) -> str:
        return f"{self.FUNCTOR}({self.modality})"
