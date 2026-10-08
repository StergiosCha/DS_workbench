"""DS tree labels (partial ``qmul.ds.tree.label``).

Recognised label types are parsed into proper subclasses; everything
else falls through to :class:`GenericLabel` so the grammar can load
without crashing.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from dylan.action.meta.element import MetaElement, restore_meta_bindings, snapshot_meta_bindings
from dylan.formula.atomic_formula import AtomicFormula
from dylan.formula.formula import Formula
from dylan.formula.opaque_formula import OpaqueFormula
from dylan.tree.basic_operator import OP_PATTERN
from dylan.tree.modality import Modality
from dylan.tree.node_address import NodeAddress
from dylan.type.dstype import DSType

logger = logging.getLogger(__name__)

_UNARY_PRED_RE = re.compile(r"(?i)^(Tense|Class|Person|Case|Number|Gender|Aspect|Accept|Mood)\((.+)\)\s*$")
_WARNED_GENERIC_LABELS: set[str] = set()
_METALABEL_PATTERN = re.compile(r"^(?:[V-Z][0-9]*|META)$")
# Note: do not use a repeated *capturing* group for operators — in Python only the
# last repetition is stored; Java's regex differs.  We slice by the closing bracket.


def java_string_hashcode(s: str) -> int:
    """32-bit Java ``String.hashCode`` (signed)."""
    h = 0
    for ch in s:
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return h


def _java_int_sub(a: int, b: int) -> int:
    """32-bit signed Java integer subtraction."""
    r = (a - b) & 0xFFFFFFFF
    if r >= 0x80000000:
        r -= 0x100000000
    return r


def _java_int_add(a: int, b: int) -> int:
    """32-bit signed Java integer addition."""
    r = (a + b) & 0xFFFFFFFF
    if r >= 0x80000000:
        r -= 0x100000000
    return r


# ── abstract base ────────────────────────────────────────────────────


class Label(ABC):
    """Node label in a DS tree."""

    def reset_metas(self) -> None:
        """Reset any bound meta-variables (no-op in base)."""
        return

    def instantiate(self) -> Label:
        """Fresh copy with metavariables resolved (Java ``Label.instantiate``)."""
        return self

    def java_hash_code(self) -> int:
        """Java ``Label.hashCode`` default: hash of ``toString`` (subclasses override)."""
        return java_string_hashcode(str(self))

    def compare_to(self, other: "Label") -> int:
        """Java ``Label.compareTo`` (TreeSet order on ``Node``): equals → 0 else hashCode delta."""
        if self == other or other == self:
            return 0
        return _java_int_sub(self.java_hash_code(), other.java_hash_code())

    def __lt__(self, other: object) -> bool:
        """Order labels like Java ``TreeSet<Label>``."""
        if not isinstance(other, Label):
            return NotImplemented
        return self.compare_to(other) < 0

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError

    def check(self, node: Any) -> bool:
        """Return ``True`` if *node* carries this label (Java ``Node.hasLabel`` / symmetric ``equals``)."""
        for lab in node.labels:
            if self == lab or lab == self:
                return True
        return False

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """Check against the pointed node (default; subclasses may use *context*)."""
        return self.check(tree.pointed_node)


# ── concrete label types ─────────────────────────────────────────────


class TypeLabel(Label):
    """Type label ``Ty(e)`` etc."""

    FUNCTOR = "Ty"

    def __init__(self, t: DSType) -> None:
        super().__init__()
        self.type = t

    def instantiate(self) -> Label:
        return TypeLabel(self.type.instantiate())

    def java_hash_code(self) -> int:
        """Java ``TypeLabel.hashCode``: ``31 * 1 + type.hashCode()``."""
        type_h = 0 if self.type is None else self.type.java_hash_code()
        return _java_int_add(31, type_h)

    def __hash__(self) -> int:
        return hash(self.type)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TypeLabel) and self.type == other.type

    def __str__(self) -> str:
        return f"{self.FUNCTOR}({self.type})"


TypeLabel.t = TypeLabel(DSType.t)  # type: ignore[attr-defined]
TypeLabel.e = TypeLabel(DSType.e)  # type: ignore[attr-defined]
TypeLabel.cn = TypeLabel(DSType.cn)  # type: ignore[attr-defined]


class ArbitraryTypeLabel(Label):
    """``Ty(x)`` queries any type without binding a rule metavariable."""

    def __hash__(self) -> int:
        return hash(ArbitraryTypeLabel)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ArbitraryTypeLabel)

    def check(self, node: Any) -> bool:
        return any(isinstance(lab, (TypeLabel, ArbitraryTypeLabel)) for lab in node.labels)

    def __str__(self) -> str:
        return "Ty(x)"


class TnLabel(Label):
    """``Tn(x)`` tests fixedness; ``Tn(a)`` binds an address; ``Tn(0)`` tests it."""

    def __init__(self, address: str) -> None:
        self.address = address
        self._meta = (
            MetaElement.get(address, NodeAddress)
            if address != "x" and not re.fullmatch(r"[01LB*UPC]+", address) else None
        )

    def __hash__(self) -> int:
        return hash((TnLabel, self.address))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TnLabel) and self.address == other.address

    def check(self, node: Any) -> bool:
        if self.address == "x":
            return node.address.is_fixed()
        if self._meta is not None:
            return bool(self._meta == node.address)
        return str(node.address) == self.address

    def instantiate(self) -> Label:
        value = self._meta.get_value() if self._meta is not None else None
        return TnLabel(str(value)) if value is not None else self

    def __str__(self) -> str:
        return f"Tn({self.address})"


class Requirement(Label):
    """Requirement ``?X``."""

    PREFIX = "?"

    def __init__(self, inner: Label) -> None:
        super().__init__()
        self.inner = inner

    def __hash__(self) -> int:
        return hash(self.inner)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Requirement) and self.inner == other.inner

    def __str__(self) -> str:
        return f"{self.PREFIX}{self.inner}"

    def instantiate(self) -> Label:
        """Copy with inner label metavariables resolved (Java ``Requirement.instantiate``)."""
        return Requirement(self.inner.instantiate())

    def check(self, node: Any) -> bool:
        """True when the node carries this requirement (Java ``Node.hasLabel`` / ``equals``)."""
        if isinstance(self.inner, ArbitraryLabel) and self.inner.name == "x":
            return any(isinstance(lab, Requirement) for lab in node.labels)
        if isinstance(self.inner, ArbitraryTypeLabel):
            return any(
                isinstance(lab, Requirement)
                and isinstance(lab.inner, (TypeLabel, ArbitraryTypeLabel))
                for lab in node.labels
            )
        for lab in node.labels:
            if self == lab or lab == self:
                return True
        return False

    def subsumes(self, other: Label) -> bool:
        """Requirement subsumption via the inner label (Java ``Requirement.subsumes``)."""
        if self == other:
            return True
        if isinstance(self.inner, ModalLabel):
            return True
        if hasattr(self.inner, "subsumes"):
            return self.inner.subsumes(other)
        return False


class UnaryPredicateLabel(Label):
    """Unary DS predicates ``person(s3)``, ``class(obj)``, etc. (Java ``UnaryPredicateLabel``)."""

    def __init__(self, predicate: str, arg: str) -> None:
        super().__init__()
        self.predicate = predicate
        self.arg = arg

    @classmethod
    def parse(cls, s: str) -> UnaryPredicateLabel | None:
        """Parse *s* or return ``None`` if it is not a unary predicate."""
        m = _UNARY_PRED_RE.match(s.strip())
        if not m:
            return None
        raw = m.group(1)
        pred = raw[0].upper() + raw[1:].lower()
        return cls(pred, m.group(2).strip())

    def __hash__(self) -> int:
        return hash((self.predicate.lower(), self.arg))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, UnaryPredicateLabel)
            and self.predicate.lower() == other.predicate.lower()
            and self.arg == other.arg
        )

    def __str__(self) -> str:
        return f"{self.predicate}({self.arg})"


class FeatureLabel(Label):
    """Feature such as ``+Q``, ``+eval``, ``+BE`` (Java ``FeatureLabel``)."""

    PREFIX = "+"

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __hash__(self) -> int:
        return hash(("+", self.name))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FeatureLabel) and self.name == other.name

    def check(self, node: Any) -> bool:
        for lab in node.labels:
            if isinstance(lab, FeatureLabel) and lab.name == self.name:
                return True
        return False

    def __str__(self) -> str:
        return f"{self.PREFIX}{self.name}"


class SpeechActLabel(Label):
    """Speech-act annotation on a node (Java ``SpeechActLabel``; minimal stub)."""

    def __init__(self, name: str = "sa") -> None:
        super().__init__()
        self.name = name

    def __hash__(self) -> int:
        return hash(("SpeechAct", self.name))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SpeechActLabel) and self.name == other.name

    def __str__(self) -> str:
        return f"SA({self.name})"


class AssertionLabel(Label):
    """Assertion marker removed by ``unassert`` (Java ``AssertionLabel``; minimal stub)."""

    def __hash__(self) -> int:
        return hash("Assert")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AssertionLabel)

    def __str__(self) -> str:
        return "Assert"


class ScopeStatement(Label):
    """Scope dependency statement ``sat_scope_dep`` (Java ``ScopeStatement``; minimal stub)."""

    def __init__(self, wide: Formula, narrow: Formula) -> None:
        super().__init__()
        self.wide = wide
        self.narrow = narrow

    def get_widest(self) -> Formula:
        return self.wide

    def get_narrowest(self) -> Formula:
        return self.narrow

    def instantiate(self) -> Label:
        return ScopeStatement(self.wide.instantiate(), self.narrow.instantiate())

    def __hash__(self) -> int:
        return hash((ScopeStatement, self.wide, self.narrow))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ScopeStatement)
            and self.wide == other.wide
            and self.narrow == other.narrow
        )

    def __str__(self) -> str:
        return f"Scope({self.wide},{self.narrow})"


class BottomLabel(Label):
    """Bottom / done marker ``!`` (Java ``BottomLabel``)."""

    def __hash__(self) -> int:
        return hash("!")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, BottomLabel)

    def __str__(self) -> str:
        return "!"


class FormulaLabel(Label):
    """Formula label ``Fo(…)`` wrapping a :class:`Formula` (Java ``FormulaLabel``)."""

    FUNCTOR = "Fo"

    def __init__(self, formula: Formula) -> None:
        super().__init__()
        self._formula = formula

    def get_formula(self) -> Formula:
        """Return the semantic formula (Java ``FormulaLabel.getFormula``)."""
        return self._formula

    def instantiate(self) -> Label:
        return FormulaLabel(self._formula.instantiate().evaluate())

    def java_hash_code(self) -> int:
        """Java ``FormulaLabel.hashCode``: ``31 * 1 + formula.hashCode()``."""
        form_h = 0 if self._formula is None else self._formula.java_hash_code()
        return _java_int_add(31, form_h)

    def __hash__(self) -> int:
        return hash((FormulaLabel, self._formula))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FormulaLabel) and self._formula == other._formula

    def __str__(self) -> str:
        return f"{self.FUNCTOR}({self._formula})"


def _formula_for_fo_inner(inner: str, *, in_ex_conj: bool = False) -> Formula:
    """Parse *inner* or wrap as :class:`OpaqueFormula` (lexicon / IF ``Fo`` specs)."""
    s = inner.strip()
    parsed = Formula.create(s, in_ex_conj)
    if parsed is not None:
        return parsed
    return OpaqueFormula(s)


class SharedFormulaLabel(Label):
    """Topic copy condition: a fixed occurrence in this clause or a forward LINK.

    This names the D-path condition in thesis (2.94). Backward LINKs and
    context edges are excluded, so the topic cannot satisfy its own condition.
    Only concrete native formulas count; checking never binds a placeholder.
    """

    def __init__(self, formula: Formula) -> None:
        self.formula = formula

    def instantiate(self) -> Label:
        return SharedFormulaLabel(self.formula.instantiate().evaluate())

    def __hash__(self) -> int:
        return hash((SharedFormulaLabel, self.formula))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SharedFormulaLabel) and self.formula == other.formula

    def __str__(self) -> str:
        return f"SharedFo({self.formula})"

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        from dylan.formula.mltt.semantics import SemanticFormula

        prefix = str(tree.pointer)
        for address, node in tree.items():
            suffix = str(address)[len(prefix):]
            if not str(address).startswith(prefix) or not suffix or set(suffix) - set("01L"):
                continue
            formula = node.get_formula()
            if isinstance(formula, SemanticFormula) and formula == self.formula:
                return True
        return False


class ArbitraryLabel(Label):
    """Placeholder ``x`` inside ``Ex.x`` (Java ``ArbitraryLabel``)."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ArbitraryLabel) and self.name == other.name

    def check(self, node: Any) -> bool:
        """Approximate existential witness: any label on the node (metas omitted)."""
        return len(node.labels) > 0

    def __str__(self) -> str:
        return self.name


class ExistentialLabelConjunction(Label):
    """Existential bundle ``Ex.fo(x)`` (simplified Java ``ExistentialLabelConjunction``)."""

    FUNCTOR = "Ex."

    def __init__(self, parts: list[Label]) -> None:
        super().__init__()
        self.parts = parts

    def __hash__(self) -> int:
        return hash((self.FUNCTOR, tuple(self.parts)))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ExistentialLabelConjunction) and self.parts == other.parts

    def check(self, node: Any) -> bool:
        return all(p.check(node) for p in self.parts)

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        return all(p.check_with_tuple_as_context(tree, context) for p in self.parts)

    def __str__(self) -> str:
        if len(self.parts) == 1:
            return f"{self.FUNCTOR}{self.parts[0]}"
        return self.FUNCTOR + "(" + " & ".join(str(p) for p in self.parts) + ")"


class AddresseeLabel(Label):
    """``Addressee(X)`` — uses dialogue context (Java ``AddresseeLabel``)."""

    FUNCTOR = "Addressee"

    def __init__(self, formula: Formula) -> None:
        super().__init__()
        self._formula = formula

    @classmethod
    def parse(cls, s: str) -> AddresseeLabel | None:
        """Parse ``Addressee(...)`` with ``Formula.create(..., True)`` like Java ``LabelFactory``."""
        low = s.strip().lower()
        if not low.startswith(cls.FUNCTOR.lower() + "("):
            return None
        i = s.index("(")
        inner = s[i + 1 : s.rindex(")")].strip()
        f = Formula.create(inner, True)
        if f is None:
            return None
        return cls(f)

    def instantiate(self) -> Label:
        """Resolve metavariables inside the inner formula (Java ``AddresseeLabel.instantiate``)."""
        ev = self._formula.instantiate().evaluate()
        return AddresseeLabel(ev.clone())

    def __hash__(self) -> int:
        return hash((self.FUNCTOR, self._formula))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AddresseeLabel) and self._formula == other._formula

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """True when the rule metavariable unifies with the current addressee (Java ``check``)."""
        addressee = _dialogue_addressee(context)
        if addressee is None:
            return False
        return self._formula == AtomicFormula(addressee)

    def __str__(self) -> str:
        return f"{self.FUNCTOR}({self._formula})"


class SpeakerLabel(Label):
    """``Speaker(X)`` — uses dialogue context (Java ``SpeakerLabel``)."""

    FUNCTOR = "Speaker"

    def __init__(self, formula: Formula) -> None:
        super().__init__()
        self._formula = formula

    @classmethod
    def parse(cls, s: str) -> SpeakerLabel | None:
        """Parse ``Speaker(...)`` with ``Formula.create(..., True)`` like Java ``LabelFactory``."""
        low = s.strip().lower()
        if not low.startswith(cls.FUNCTOR.lower() + "("):
            return None
        i = s.index("(")
        inner = s[i + 1 : s.rindex(")")].strip()
        f = Formula.create(inner, True)
        if f is None:
            return None
        return cls(f)

    def instantiate(self) -> Label:
        """Resolve metavariables inside the inner formula (Java ``SpeakerLabel.instantiate``)."""
        ev = self._formula.instantiate().evaluate()
        return SpeakerLabel(ev.clone())

    def __hash__(self) -> int:
        return hash((self.FUNCTOR, self._formula))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SpeakerLabel) and self._formula == other._formula

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """True when the rule metavariable unifies with the current speaker (Java ``check``)."""
        speaker = _dialogue_speaker(context)
        if speaker is None:
            return False
        return self._formula == AtomicFormula(speaker)

    def __str__(self) -> str:
        return f"{self.FUNCTOR}({self._formula})"


class CompleteLabel(Label):
    """``complete`` — holds when the whole tree is complete (Java ``CompleteLabel``)."""

    FUNCTOR = "complete"

    def __hash__(self) -> int:
        return hash(self.FUNCTOR)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompleteLabel)

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """True when the tree pointer is at root and no node carries a requirement."""
        del context
        return bool(tree.is_complete())

    def __str__(self) -> str:
        return self.FUNCTOR


class MetaLabel(Label):
    """Label-position metavariable ``V``–``Z`` / ``META`` (Java ``MetaLabel`` / ``LabelFactory`` pattern)."""

    def __init__(self, meta: MetaElement[Label]) -> None:
        super().__init__()
        self._meta = meta

    @classmethod
    def get(cls, name: str) -> MetaLabel:
        """Return the shared :class:`MetaLabel` for *name* (pooled :class:`MetaElement`)."""
        return cls(MetaElement.get(name, Label))

    def instantiate(self) -> Label:
        """Resolve to the bound label when set (Java ``MetaLabel.instantiate``)."""
        v = self._meta.get_value()
        if v is None:
            return self
        return v.instantiate()

    def check(self, node: Any) -> bool:
        """Delegate to the bound label when set; else scan the node (thinning ``?X`` / ``X``)."""
        v = self._meta.get_value()
        if v is None:
            return super().check(node)
        if v.check(node):
            return True
        return super().check(node)

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """Use :meth:`check` on the pointed node (bound-meta thinning needs requirement-inner match)."""
        del context
        return self.check(tree.pointed_node)

    def __eq__(self, other: object) -> bool:
        """Match Java ``MetaLabel.equals`` (binding via :class:`MetaElement`)."""
        if self is other:
            return True
        if other is None:
            return False
        if isinstance(other, MetaLabel):
            return bool(self._meta == other._meta.get_value())
        return bool(self._meta == other)

    def __hash__(self) -> int:
        return hash((MetaLabel, self._meta.name))

    def __str__(self) -> str:
        """Java ``MetaLabel.toString`` → ``MetaElement.toString`` (``X`` or ``X=value``)."""
        return str(self._meta)


class ModalLabel(Label):
    """Modal path + inner label(s), e.g. ``<\\/1\\/0>person(s3)`` (Java ``ModalLabel``)."""

    def __init__(self, modality: Modality, inners: list[Label]) -> None:
        super().__init__()
        self.modality = modality
        self.inners = inners

    def __hash__(self) -> int:
        return hash((tuple(self.modality.ops), tuple(self.inners)))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ModalLabel)
            and self.modality.ops == other.modality.ops
            and self.modality.required == other.modality.required
            and self.inners == other.inners
        )

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """Diamonds require a witness; boxes hold at every target (including none)."""
        from dylan.action.meta.meta_modality import MetaModality

        save = tree.pointer
        initial = snapshot_meta_bindings()
        modality = self.modality.instantiate()
        meta = modality.get_meta() if isinstance(modality, MetaModality) else None
        if meta is not None and modality.required:
            raise ValueError("A box modality metavariable must be bound before checking")
        targets = tree.keys() if meta is not None else modality.reachable(save, tree.keys())
        success = False
        try:
            for addr in tree.keys():
                if addr not in targets:
                    continue
                candidate = snapshot_meta_bindings()
                if meta is not None and not (meta == Modality.relating(save, addr)):
                    restore_meta_bindings(candidate)
                    continue
                tree.pointer = addr
                holds = all(lab.check_with_tuple_as_context(tree, context) for lab in self.inners)
                if modality.required and not holds:
                    return False
                if not modality.required and holds:
                    success = True
                    return True
                if not holds:
                    restore_meta_bindings(candidate)
            success = modality.required
            return success
        finally:
            tree.pointer = save
            if not success:
                restore_meta_bindings(initial)

    def instantiate(self) -> Label:
        return ModalLabel(self.modality.instantiate(), [lab.instantiate() for lab in self.inners])

    def __str__(self) -> str:
        body = (
            str(self.inners[0])
            if len(self.inners) == 1
            else "(" + " & ".join(str(x) for x in self.inners) + ")"
        )
        return str(self.modality) + body


class NegatedLabel(Label):
    """Negation ``\u00acX`` — satisfied when the inner label is NOT present."""

    PREFIX = "\u00ac"

    def __init__(self, inner: Label) -> None:
        super().__init__()
        self.inner = inner

    def instantiate(self) -> Label:
        """Copy with inner metavariables resolved (Java ``NegatedLabel.instantiate``)."""
        return NegatedLabel(self.inner.instantiate())

    def __hash__(self) -> int:
        return hash(("NOT", self.inner))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NegatedLabel) and self.inner == other.inner

    def check(self, node: Any) -> bool:
        saved = snapshot_meta_bindings()
        try:
            return not self.inner.check(node)
        finally:
            restore_meta_bindings(saved)

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        """Negate modal / contextual checks (Java ``NegatedLabel.checkWithTupleAsContext``)."""
        saved = snapshot_meta_bindings()
        try:
            return not self.inner.check_with_tuple_as_context(tree, context)
        finally:
            restore_meta_bindings(saved)

    def __str__(self) -> str:
        return f"{self.PREFIX}{self.inner}"


class DisjunctionLabel(Label):
    """Inclusive trigger disjunction with isolated failed alternatives."""

    separator = " || "

    def __init__(self, parts: list[Label]) -> None:
        self.parts = parts

    def __hash__(self) -> int:
        return hash((type(self), tuple(self.parts)))

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other) and self.parts == other.parts

    def _check(self, check: Any) -> bool:
        for part in self.parts:
            saved = snapshot_meta_bindings()
            if check(part):
                return True
            restore_meta_bindings(saved)
        return False

    def check(self, node: Any) -> bool:
        return self._check(lambda part: part.check(node))

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        return self._check(lambda part: part.check_with_tuple_as_context(tree, context))

    def instantiate(self) -> Label:
        return type(self)([part.instantiate() for part in self.parts])

    def __str__(self) -> str:
        return "(" + self.separator.join(str(part) for part in self.parts) + ")"


class ConjunctionLabel(DisjunctionLabel):
    """Grouped trigger conjunction, e.g. the GSG imperative condition."""

    separator = " & "

    def _check(self, check: Any) -> bool:
        saved = snapshot_meta_bindings()
        if all(check(part) for part in self.parts):
            return True
        restore_meta_bindings(saved)
        return False


# Every label spec that fell through to GenericLabel, recorded at parse time so grammar lint can
# list vocabulary gaps (e.g. ``UnsupportedFeature(x)``) even before a trigger is evaluated.
generic_label_seen: set[str] = set()


class SubsumesLabel(Label):
    """The unfixed node reached by a bound modality subsumes the pointer address."""

    def __init__(self, modality: Modality) -> None:
        self.modality = modality

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        from dylan.action.meta.meta_modality import MetaModality

        modality = self.modality.instantiate()
        if isinstance(modality, MetaModality):
            return False  # Witness enumeration belongs to the preceding modal trigger.
        return any(
            address.subsumes(tree.pointer)
            for address in modality.reachable(tree.pointer, tree.keys())
        )

    def instantiate(self) -> Label:
        return SubsumesLabel(self.modality.instantiate())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SubsumesLabel) and self.modality == other.modality

    def __hash__(self) -> int:
        return hash((SubsumesLabel, self.modality))

    def __str__(self) -> str:
        return f"subsumes({self.modality})"


class GenericLabel(Label):
    """Fallback for unrecognised label specs — always fails ``check()``."""

    def __init__(self, spec: str) -> None:
        super().__init__()
        self.spec = spec
        generic_label_seen.add(spec)

    def __hash__(self) -> int:
        return hash(self.spec)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GenericLabel) and self.spec == other.spec

    def check(self, node: Any) -> bool:
        if self.spec not in _WARNED_GENERIC_LABELS:
            _WARNED_GENERIC_LABELS.add(self.spec)
            logger.warning("Unsupported trigger label %r; evaluating as False", self.spec)
        return False

    def check_with_tuple_as_context(self, tree: Any, context: Any) -> bool:
        return self.check(tree.pointed_node)

    def __str__(self) -> str:
        return self.spec


# ── factory ──────────────────────────────────────────────────────────

_NEG = "\u00ac"
def _split_trigger_group(s: str, separator: str) -> list[str]:
    """Split only at top level; formulas/types may contain their own groups."""
    depth = 0
    start = 0
    parts = []
    for i, ch in enumerate(s):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == separator and depth == 0:
            if s[start:i].strip():
                parts.append(s[start:i].strip())
            start = i + 1
    if s[start:].strip():
        parts.append(s[start:].strip())
    return parts


def _dialogue_addressee(context: Any) -> str | None:
    """Return addressee string from a :class:`~dylan.context.context.Context`, if any."""
    if context is None:
        return None
    fn = getattr(context, "get_current_addressee", None)
    if callable(fn):
        return fn()
    return None


def _dialogue_speaker(context: Any) -> str | None:
    """Return speaker string from a :class:`~dylan.context.context.Context`, if any."""
    if context is None:
        return None
    fn = getattr(context, "get_current_speaker", None)
    if callable(fn):
        return fn()
    return None


def _parse_modal_inner(rest: str, *, in_existential: bool = False) -> list[Label]:
    """Parse label group after a modality (possibly ``(a & b)``)."""
    rest = rest.strip()
    return [label_factory_create(rest, in_existential=in_existential)]


def _try_parse_modal_label(s: str, *, in_existential: bool = False) -> ModalLabel | None:
    """If *s* begins with a modality, return :class:`ModalLabel`; else ``None``."""
    s = s.strip()
    if s.startswith("<") and ">" in s:
        r = s.index(">")
        mod_str = s[: r + 1]
        rest = s[r + 1 :].strip()
        try:
            modality = Modality.parse(mod_str)
        except ValueError:
            return None
        if not rest:
            return None
        return ModalLabel(modality, _parse_modal_inner(rest, in_existential=in_existential))
    if s.startswith("[") and "]" in s:
        r = s.index("]")
        mod_str = s[: r + 1]
        rest = s[r + 1 :].strip()
        try:
            modality = Modality.parse(mod_str)
        except ValueError:
            return None
        if not rest:
            return None
        return ModalLabel(modality, _parse_modal_inner(rest, in_existential=in_existential))
    ops = list(OP_PATTERN.finditer(s))
    if not ops or ops[0].start() != 0:
        return None
    end = 0
    for om in ops:
        if om.start() != end:
            break
        end = om.end()
    mod_str = s[:end].strip()
    rest = s[end:].strip()
    if not rest:
        return None
    try:
        modality = Modality.parse(mod_str)
    except ValueError:
        return None
    return ModalLabel(modality, _parse_modal_inner(rest, in_existential=in_existential))


def label_factory_create(
    string: str,
    ite: Any = None,
    *,
    in_existential: bool = False,
) -> Label:  # noqa: ARG001
    """Parse label specs used in IF clauses (partial Java ``LabelFactory.create``)."""
    s = string.strip()

    if s.startswith("(") and s.endswith(")"):
        depth = 0
        for i, ch in enumerate(s):
            depth += (ch == "(") - (ch == ")")
            if depth == 0:
                if i == len(s) - 1:
                    return label_factory_create(s[1:-1], ite, in_existential=in_existential)
                break
    for separator, cls in (("|", DisjunctionLabel), ("&", ConjunctionLabel)):
        parts = _split_trigger_group(s, separator)
        if len(parts) > 1:
            return cls([label_factory_create(p, ite, in_existential=in_existential) for p in parts])

    if s.startswith(_NEG):
        inner_s = s[len(_NEG) :].strip()
        inner = label_factory_create(inner_s, ite, in_existential=in_existential)
        return NegatedLabel(inner)

    if s.startswith(Requirement.PREFIX):
        inner_s = s[len(Requirement.PREFIX) :].strip()
        if inner_s == "x":
            inner: Label = ArbitraryLabel("x")
        elif inner_s == "X" or _METALABEL_PATTERN.fullmatch(inner_s):
            inner = MetaLabel.get(inner_s)
        else:
            inner = label_factory_create(inner_s, ite, in_existential=in_existential)
        return Requirement(inner)

    low = s.lower()
    if re.fullmatch(r"(?i:ty)\(\s*x\s*\)", s):
        return ArbitraryTypeLabel()
    subsumes = re.fullmatch(r"(?i:subsumes)\((.+)\)", s)
    if subsumes:
        return SubsumesLabel(Modality.parse(subsumes.group(1)))
    tn = re.fullmatch(r"(?i)tn\(([^()]+)\)", s)
    if tn:
        return TnLabel(tn.group(1).strip())
    if s.startswith("[+") and s.endswith("]"):
        return FeatureLabel(s[2:-1].strip())
    if low.startswith(AddresseeLabel.FUNCTOR.lower() + "("):
        ad = AddresseeLabel.parse(s)
        if ad is not None:
            return ad

    if low.startswith(SpeakerLabel.FUNCTOR.lower() + "("):
        sp = SpeakerLabel.parse(s)
        if sp is not None:
            return sp

    if low == CompleteLabel.FUNCTOR:
        return CompleteLabel()

    up = UnaryPredicateLabel.parse(s)
    if up is not None:
        return up

    if low.startswith(FeatureLabel.PREFIX.lower()) and len(s) > 1:
        return FeatureLabel(s[1:].strip())

    if s == "!":
        return BottomLabel()

    if low.startswith("ex."):
        tail = s[3:].strip()
        if tail == "x":
            return ExistentialLabelConjunction([ArbitraryLabel("x")])
        return ExistentialLabelConjunction([label_factory_create(tail, ite, in_existential=True)])

    if low.startswith("sharedfo(") and s.endswith(")"):
        return SharedFormulaLabel(_formula_for_fo_inner(s[s.index("(") + 1:-1]))

    if low.startswith("fo("):
        inner = s[s.index("(") + 1 : s.rindex(")")]
        return FormulaLabel(_formula_for_fo_inner(inner, in_ex_conj=in_existential))

    if low.startswith(FormulaLabel.FUNCTOR.lower() + "("):
        inner = s[s.index("(") + 1 : s.rindex(")")]
        return FormulaLabel(_formula_for_fo_inner(inner, in_ex_conj=in_existential))

    if low.startswith(TypeLabel.FUNCTOR.lower() + "("):
        return _parse_ty(s)

    modal = _try_parse_modal_label(s, in_existential=in_existential)
    if modal is not None:
        return modal

    if _METALABEL_PATTERN.fullmatch(s):
        return MetaLabel.get(s)

    if len(s) == 1 and s.isupper():
        return MetaLabel.get(s)

    return GenericLabel(s)


def _parse_ty(s: str) -> TypeLabel:
    """Parse ``Ty(...)`` into a :class:`TypeLabel`."""
    low = s.strip().lower()
    if not low.startswith(TypeLabel.FUNCTOR.lower()):
        return GenericLabel(s)  # type: ignore[return-value]
    try:
        inner = s[s.index("(") + 1 : s.rindex(")")]
        dt = DSType.parse(inner)
        if dt is None:
            return GenericLabel(s)  # type: ignore[return-value]
        return TypeLabel(dt)
    except (ValueError, IndexError):
        return GenericLabel(s)  # type: ignore[return-value]
