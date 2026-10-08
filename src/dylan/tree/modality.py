"""Tree modality — sequence of ``BasicOperator`` steps (Java ``Modality``)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

from dylan.tree.basic_operator import ARROW_DOWN, ARROW_UP, OP_PATTERN, BasicOperator

if TYPE_CHECKING:
    from dylan.tree.node_address import NodeAddress

FORALL_LEFT = "["
FORALL_RIGHT = "]"
EXIST_LEFT = "<"
EXIST_RIGHT = ">"

_MODALITY_RE = re.compile(
    r"("
    + re.escape(FORALL_LEFT) + "|" + re.escape(EXIST_LEFT)
    + r")?((?:" + OP_PATTERN.pattern + r")+)("
    + re.escape(FORALL_RIGHT) + "|" + re.escape(EXIST_RIGHT)
    + r")?",
)
_META_MODALITY_RE = re.compile(
    r"^(?:"
    + re.escape(FORALL_LEFT)
    + "|"
    + re.escape(EXIST_LEFT)
    + r")?([A-Z][A-Z0-9]*)(?:"
    + re.escape(FORALL_RIGHT)
    + "|"
    + re.escape(EXIST_RIGHT)
    + r")?$",
)


class Modality:
    """A sequence of basic operators, optionally wrapped in ``[]`` or ``<>``."""

    def __init__(self, ops: list[BasicOperator], *, required: bool = False) -> None:
        self.ops = ops
        self.required = required

    @classmethod
    def parse(cls, string: str) -> Modality:
        """Parse a modality string like ``\\/0``, ``/\\1``, ``<\\/0/\\1>``, or ``<Z>`` metavar."""
        s = string.strip()
        if s[:1] in ("[", "<"):
            closing = "]" if s[0] == "[" else ">"
            if not s.endswith(closing):
                raise ValueError(f"unmatched modality brackets: {string!r}")
        elif s.endswith(("]", ">")):
            raise ValueError(f"unmatched modality brackets: {string!r}")
        m = _MODALITY_RE.fullmatch(s)
        if m:
            required = m.group(1) == FORALL_LEFT if m.group(1) else False
            ops = BasicOperator.create_many(m.group(2))
            return cls(ops, required=required)
        mm = _META_MODALITY_RE.fullmatch(s)
        if mm:
            from dylan.action.meta.meta_modality import MetaModality

            return MetaModality.get(mm.group(1), required=s.startswith("["))
        if re.fullmatch(r"[A-Z][A-Z0-9]*", s):
            from dylan.action.meta.meta_modality import MetaModality

            return MetaModality.get(s)
        raise ValueError(f"unrecognised modality string: {string!r}")

    def instantiate(self) -> Modality:
        """Return a fresh copy (no meta-variables in this stub)."""
        return Modality(list(self.ops), required=self.required)

    def inverse(self) -> Modality:
        """Reverse operator sequence with each step inverted (Java ``Modality.inverse``)."""
        inv_ops = [op.inverse() for op in reversed(self.ops)]
        return Modality(inv_ops, required=self.required)

    def __str__(self) -> str:
        bracket_l = FORALL_LEFT if self.required else EXIST_LEFT
        bracket_r = FORALL_RIGHT if self.required else EXIST_RIGHT
        path = "".join(str(op) for op in self.ops)
        return f"{bracket_l}{path}{bracket_r}"

    def reachable(
        self, from_addr: "NodeAddress", addresses: Iterable["NodeAddress"]
    ) -> set["NodeAddress"]:
        """Evaluate the path over existing nodes; ``+`` takes one or more steps.

        Bare daughter relations include unfixed edges but exclude LINK/context
        edges. ``*``, ``U`` and ``P`` themselves denote literal unfixed edges.
        """
        inventory = set(addresses)
        current = {from_addr}
        for op in self.ops:
            targets = set()
            if op.is_plus() or not op.path:
                edges = op.path[:-1] if op.is_plus() else ""
                edges = edges or "01*UP"
                if not op.path and op.is_up():
                    edges += "LC"
                frontier = set(current)
                while frontier:
                    following = set()
                    for addr in frontier:
                        for edge in edges:
                            nxt = addr.go_op(BasicOperator(op.direction, edge))
                            if nxt in inventory and nxt not in targets:
                                following.add(nxt)
                    targets.update(following)
                    if not op.is_plus():
                        break
                    frontier = following
            else:
                targets = {
                    nxt for addr in current
                    if (nxt := addr.go_op(op)) is not None and nxt in inventory
                }
            current = targets
        return current & inventory

    def relates(
        self, from_addr: "NodeAddress", to_addr: "NodeAddress",
        addresses: Iterable["NodeAddress"] | None = None,
    ) -> bool:
        """Whether a path holds; closures require the tree's address inventory."""
        if addresses is None:
            return from_addr.modality_path_matches(to_addr, self.ops)
        return to_addr in self.reachable(from_addr, addresses)

    @classmethod
    def relating(cls, from_addr: "NodeAddress", to_addr: "NodeAddress") -> Modality:
        """Build a literal path between two addresses for a modality binding."""
        source, target = str(from_addr), str(to_addr)
        shared = 0
        for a, b in zip(source, target):
            if a != b:
                break
            shared += 1
        ops = [BasicOperator(ARROW_DOWN, "L") if c == "B" else BasicOperator(ARROW_UP, c)
               for c in reversed(source[shared:])]
        ops.extend(BasicOperator(ARROW_UP, "L") if c == "B" else BasicOperator(ARROW_DOWN, c)
                   for c in target[shared:])
        return cls(ops)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Modality):
            return NotImplemented
        return self.required == other.required and self.ops == other.ops
