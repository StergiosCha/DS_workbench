"""010*-style node addresses (Java ``NodeAddress``)."""

from __future__ import annotations

import re
from dataclasses import dataclass

PATH_0 = "0"
PATH_1 = "1"
PATH_LINK = "L"
PATH_BACK_LINK = "B"  # Stored predecessor: a LINK from this node to its prefix.
PATH_UNFIXED = "*"
PATH_LOCAL_UNFIXED = "U"
PATH_LOCAL_UNFIXED_PLUS = "P"
PATH_CONTEXT = "C"
ROOT = "0"

_UNFIXED_CHARS = (PATH_UNFIXED, PATH_LOCAL_UNFIXED, PATH_LOCAL_UNFIXED_PLUS)


@dataclass(frozen=True, slots=True)
class NodeAddress:
    """String DS address (default root ``0``).

    Addresses are strings over ``{0,1,L,B,*,U,P,C}`` rooted at ``"0"``.
    ``B`` stores a backward LINK without renumbering the propositional root.
    Navigation uses ordinary inverse/forward LINK operators, not a B operator.
    Down-0 from ``"0"`` yields ``"00"``; down-1 yields ``"01"``, etc.
    """

    address: str = ROOT

    def is_root(self) -> bool:
        """Return true for the root address."""
        return self.address == ROOT

    def down(self, path: str) -> NodeAddress:
        """Go down by appending *path* (Java ``NodeAddress.down``)."""
        return NodeAddress(self.address + path)

    def down0(self) -> NodeAddress:
        """Return the 0-daughter address."""
        return self.down(PATH_0)

    def down1(self) -> NodeAddress:
        """Return the 1-daughter address."""
        return self.down(PATH_1)

    def down_link(self) -> NodeAddress:
        """Return the linked daughter address."""
        if self.address.endswith(PATH_BACK_LINK):
            return self.up(PATH_BACK_LINK)
        return self.down(PATH_LINK)

    def down_star(self) -> NodeAddress:
        """Return the unfixed daughter address."""
        return self.down(PATH_UNFIXED)

    def down_local_unfixed(self) -> NodeAddress:
        """Append local-unfixed step (Java ``NodeAddress.downLocalUnfixed``)."""
        return self.down(PATH_LOCAL_UNFIXED)

    def down_local_unfixed_plus(self) -> NodeAddress:
        """Append local-unfixed-plus step (thesis ``<up0><up1+>``; excludes the subject site)."""
        return self.down(PATH_LOCAL_UNFIXED_PLUS)

    def down_char(self, ch: str) -> NodeAddress:
        """Append a single path character ``0``, ``1``, ``L``, ``*``, ``U``, or ``P`` (Java ``down(String)``)."""
        return self.down(ch)

    def is_locally_fixed(self) -> bool:
        """False when the address ends in Kleene star or a local-unfixed marker (Java ``isLocallyFixed``)."""
        return not self.address.endswith(_UNFIXED_CHARS)

    def is_fixed(self) -> bool:
        """True when the address is not within an unfixed subtree (Java ``isFixed``)."""
        a = self.address
        return not any(ch in a for ch in _UNFIXED_CHARS)

    def up(self, path: str | None = None) -> NodeAddress | None:
        """Go up (Java ``NodeAddress.up``).

        Without *path*: strip last character (plain parent).
        With *path*: strip that suffix only if the address ends with it.
        Returns ``None`` if the operation is invalid.
        """
        if path is None:
            if len(self.address) < 2:
                return None
            return NodeAddress(self.address[:-1])
        if not self.address.endswith(path):
            return None
        i = self.address.rfind(path)
        if i < len(ROOT):
            return None
        return NodeAddress(self.address[:i])

    def modality_path_matches(self, other: NodeAddress, ops: list["BasicOperator"]) -> bool:
        """Whether *other* is reachable from ``self`` following *ops* (Java ``NodeAddress.to``).

        Literal steps only — fixed paths and the single-char unfixed edges
        ``*``/``U``/``P`` (which are plain address arithmetic).  Kleene-plus
        closure operators need the tree's address inventory and are handled by
        :meth:`Modality.relates` instead; here they never match.
        """
        if not ops:
            return self.address == other.address
        op, *rest = ops
        if op.is_plus():
            return False
        nxt = self.go_op(op)
        if nxt is None:
            return False
        return nxt.modality_path_matches(other, rest)

    def go_op(self, op: "BasicOperator") -> NodeAddress | None:
        """Navigate one ``BasicOperator`` step (Java ``NodeAddress.go(BasicOperator)``)."""
        if op.is_plus():
            return None  # A relation with many possible targets is not a navigation address.
        if op.is_link():
            if op.is_down():
                return self.up(PATH_BACK_LINK) if self.address.endswith(PATH_BACK_LINK) else self.down_link()
            return self.up(PATH_LINK) if self.address.endswith(PATH_LINK) else self.down(PATH_BACK_LINK)
        if op.is_down():
            if not op.path:
                raise RuntimeError("must specify down path")
            return self.down(op.path)
        if op.is_up():
            if not op.path:
                return self.up()
            return self.up(op.path)
        return None

    def go_modality(self, mod: "Modality") -> NodeAddress | None:
        """Navigate a full ``Modality`` path (Java ``NodeAddress.go(Modality)``)."""
        na: NodeAddress | None = self
        for op in mod.ops:
            if na is None:
                return None
            na = na.go_op(op)
        return na

    def __str__(self) -> str:
        """Return the address string."""
        return self.address

    def subsumes(self, other: NodeAddress) -> bool:
        """Match regular, locally unfixed, and locally unfixed-plus address patterns."""
        if self.is_fixed():
            return self.address == other.address
        pat = re.escape(self.address)
        pat = pat.replace(re.escape(PATH_UNFIXED), r"[01]*")
        pat = pat.replace(re.escape(PATH_LOCAL_UNFIXED), r"(?:1*0|U)")
        pat = pat.replace(re.escape(PATH_LOCAL_UNFIXED_PLUS), r"(?:1+0|P)")
        return bool(re.fullmatch(pat, other.address))


# Late imports to avoid circular dependency
from dylan.tree.basic_operator import BasicOperator  # noqa: E402
from dylan.tree.modality import Modality  # noqa: E402

__all__ = ["NodeAddress"]

NodeAddress.isRoot = NodeAddress.is_root  # type: ignore[attr-defined]
NodeAddress.downLink = NodeAddress.down_link  # type: ignore[attr-defined]
NodeAddress.downStar = NodeAddress.down_star  # type: ignore[attr-defined]
NodeAddress.downLocalUnfixed = NodeAddress.down_local_unfixed  # type: ignore[attr-defined]
NodeAddress.downChar = NodeAddress.down_char  # type: ignore[attr-defined]
NodeAddress.isLocallyFixed = NodeAddress.is_locally_fixed  # type: ignore[attr-defined]
NodeAddress.isFixed = NodeAddress.is_fixed  # type: ignore[attr-defined]
NodeAddress.goOp = NodeAddress.go_op  # type: ignore[attr-defined]
NodeAddress.goModality = NodeAddress.go_modality  # type: ignore[attr-defined]
