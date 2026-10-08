"""Native compositional semantics for the classical and constructive DS grammars."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dylan.formula.formula import Formula
from dylan.formula.mltt.terms import Expr, app, arrow, fresh_name, name, parse_expr
from dylan.type.dstype import DSType


@dataclass(frozen=True)
class SemanticType(DSType):
    term: Expr
    backend: str = "mltt"

    def __str__(self) -> str:
        return str(self.term)

    def clone(self) -> SemanticType:
        return self

    def get_final_type(self) -> SemanticType:
        term = self.term
        while term.kind in {"arrow", "pi"}:
            term = term.args[1]
        return SemanticType(term, self.backend)

    def accepts_requirement(self, candidate: SemanticType) -> bool:
        """DS slot satisfaction, distinct from function subtyping at application."""
        if self.backend != candidate.backend:
            return False
        required, actual = self.term, candidate.term
        if required == actual:
            return True
        if self.backend == "classical":
            return required == name("e") and is_gq(actual, "t")
        if self.backend != "mltt":
            return False
        if required == name("object"):
            return (
                actual.kind == "sigma"
                or actual.kind == "name"
                and actual.name not in {"CN", "Prop", "Content"}
                or is_gq(actual)
            )
        if required == arrow(name("object"), name("Prop")):
            return actual.kind == "arrow" and actual.args[1] == name("Prop")
        if required.kind == actual.kind == "arrow" and required.args[0] == name("object"):
            return SemanticType(required.args[1], self.backend).accepts_requirement(
                SemanticType(actual.args[1], self.backend)
            )
        if required.kind == "pi" and required.args[0] == name("CN"):
            return actual.kind == "arrow" and actual.args[1] == name("Prop")
        return False


def is_gq(term: Expr, proposition="Prop") -> bool:
    return (
        term.kind == "arrow"
        and term.args[0].kind == "arrow"
        and term.args[0].args[1] == name(proposition)
        and term.args[1] == name(proposition)
    )


def gq_consumes_predicate(left: SemanticType, right: SemanticType) -> bool:
    proposition = "Prop" if left.backend == "mltt" else "t"
    return left.backend == right.backend and is_gq(left.term, proposition) and right.term.kind == "arrow" and right.term.args[1] == name(proposition)


def left_consumes_predicate(left: SemanticType, right: SemanticType, *, reflexive=False) -> bool:
    """Quantifiers and explicitly marked reflexive combinators take the functor."""
    return gq_consumes_predicate(left, right) or (
        reflexive and left.backend == right.backend and left.term.kind == "arrow"
        and left.term.args[0] == right.term
    )


def subtype(actual: Expr, required: Expr, theory: dict[str, Any]) -> bool:
    if actual == required:
        return True
    if actual.kind == required.kind == "arrow":
        return subtype(required.args[0], actual.args[0], theory) and subtype(
            actual.args[1], required.args[1], theory
        )
    if actual.kind == "sigma":
        return subtype(actual.args[0], required, theory)
    if actual.kind != "name" or required.kind != "name":
        return False
    edges = theory.get("subtyping", {})
    frontier, seen = [actual.name], set()
    while frontier:
        item = frontier.pop()
        if item == required.name:
            return True
        if item in seen:
            continue
        seen.add(item)
        parents = edges.get(
            item, [] if item in {"object", "CN", "Prop", "Content", "e", "t"} else ["object"]
        )
        frontier.extend(parents)
    return False


def coerce(term: Expr, actual: Expr, required: Expr, theory: dict[str, Any]) -> Expr:
    if not subtype(actual, required, theory):
        raise TypeError(f"Cannot apply a predicate of {required} to {actual}")
    while actual.kind == "sigma" and actual != required:
        term = Expr("fst", args=(term,))
        actual = actual.args[0]
    if actual.kind == required.kind == "arrow" and actual != required:
        # A predicate of A consumes the first projection of an A-refinement.
        # Subtyping arrows alone does not insert that projection into its body.
        variable = fresh_name("x", term.free() | actual.free() | required.free())
        argument = coerce(name(variable), required.args[0], actual.args[0], theory)
        body = coerce(app(term, argument), actual.args[1], required.args[1], theory)
        return Expr("lam", variable, (required.args[0], body)).normalize()
    return term


@dataclass(frozen=True)
class Witness:
    variable: str
    domain: Expr


@dataclass
class SemanticFormula(Formula):
    term: Expr
    backend: str = "mltt"
    witnesses: tuple[Witness, ...] = ()
    theory: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        super().__init__()
        if self.backend == "mltt" and contains_choice(self.term):
            raise ValueError("ε/τ terms belong to classical DS, not constructive DS")

    def clone(self) -> SemanticFormula:
        return SemanticFormula(self.term, self.backend, self.witnesses, self.theory)

    def evaluate(self) -> SemanticFormula:
        return SemanticFormula(self.term.normalize(), self.backend, self.witnesses, self.theory)

    def substitute(self, var: Any, arg: Formula) -> Formula:
        if not isinstance(arg, SemanticFormula) or arg.backend != self.backend:
            raise TypeError("Cannot mix semantic backends")
        return SemanticFormula(
            self.term.substitute(str(var), arg.term), self.backend, self.witnesses, self.theory
        )

    def __str__(self) -> str:
        return str(self.term)

    def __hash__(self) -> int:
        return hash((self.term, self.backend, self.witnesses))

    def simplified(self) -> SemanticFormula:
        return SemanticFormula(self.term.simplify(), self.backend, (), self.theory)

    def close_witnesses(self, scope: str = "narrow") -> SemanticFormula:
        def wrap(body: Expr) -> Expr:
            for witness in reversed(self.witnesses):
                if witness.variable in body.free():
                    body = Expr("sigma", witness.variable, (witness.domain, body))
            return body

        def inside_universals(body: Expr) -> Expr:
            if body.kind == "pi":
                return Expr("pi", body.name, (body.args[0], inside_universals(body.args[1])))
            return wrap(body)

        term = inside_universals(self.term) if scope == "narrow" else wrap(self.term)
        return SemanticFormula(term, self.backend, (), self.theory)

    def to_coq(self, *, minimal: bool = True) -> str:
        from dylan.formula.mltt.coq import export_coq

        return export_coq(self, minimal=minimal)


def contains_choice(term: Expr) -> bool:
    return term.kind in {"eps", "tau", "iota", "choice_eps", "choice_tau", "choice_iota"} or any(
        contains_choice(arg) for arg in term.args
    )


def resolve_refinements(term: Expr, theory: dict[str, Any]) -> Expr:
    """Instantiate a CN refinement once its nominal domain is known.

    A preceding adjective or contextual restriction may already have built a
    Sigma type. Project its individual before applying an object predicate;
    treating that dependent pair itself as an object is ill-typed.
    """
    args = tuple(resolve_refinements(a, theory) for a in term.args)
    if term.kind == "refine":
        domain, predicate = args
        if domain.kind == "sigma" or domain.kind == "name" and domain.name in {"object", *theory.get("subtyping", {})}:
            variable = fresh_name("x", domain.free() | predicate.free())
            individual = coerce(name(variable), domain, name("object"), theory)
            return Expr("sigma", variable, (domain, app(predicate, individual)))
    return Expr(term.kind, term.name, args)


def apply_semantics(
    function: SemanticFormula,
    function_type: SemanticType,
    argument: SemanticFormula,
    argument_type: SemanticType,
    theory: dict[str, Any],
) -> tuple[SemanticFormula, SemanticType]:
    if len({function.backend, argument.backend, function_type.backend, argument_type.backend}) != 1:
        raise TypeError("Cannot combine different semantic backends")
    ft, at = function_type.term, argument_type.term
    if ft.kind not in {"arrow", "pi"}:
        raise TypeError(f"{ft} is not a function type")
    domain, result_type = ft.args
    witnesses = tuple(dict.fromkeys(function.witnesses + argument.witnesses))
    if (
        is_gq(at, "Prop" if function.backend == "mltt" else "t")
        and ft.kind == "arrow"
        and result_type.kind == "arrow"
    ):
        # Lift an argument quantifier while retaining every remaining argument
        # of a curried predicate, including both arguments of a give frame.
        restrictor = at.args[0].args[0]
        remaining, tail = [], result_type
        while tail.kind == "arrow":
            remaining.append(tail.args[0])
            tail = tail.args[1]
        if tail != name("Prop" if function.backend == "mltt" else "t"):
            raise TypeError("Argument quantification requires a predicate ending in Prop")
        used = function.term.free() | argument.term.free() | result_type.free() | restrictor.free()
        variables = []
        for _ in remaining:
            variable = fresh_name("x", used)
            used.add(variable)
            variables.append(variable)
        y = fresh_name("y", used)
        object_term = coerce(name(y), restrictor, domain, theory)
        body = app(function.term, object_term)
        for variable in variables:
            body = app(body, name(variable))
        continuation = Expr("lam", y, (restrictor, body))
        result = app(argument.term, continuation)
        for variable, typ in reversed(list(zip(variables, remaining))):
            result = Expr("lam", variable, (typ, result))
        result = resolve_refinements(result.normalize(), theory).normalize()
        return SemanticFormula(result, function.backend, witnesses, theory), SemanticType(
            result_type, function.backend
        )
    term = coerce(argument.term, at, domain, theory)
    if ft.kind == "pi":
        result_type = result_type.substitute(ft.name, argument.term)
    result = resolve_refinements(app(function.term, term).normalize(), theory).normalize()
    return SemanticFormula(result, function.backend, witnesses, theory), SemanticType(
        result_type, function.backend
    )


def parse_semantic_type(source: str) -> SemanticType:
    backend, body = source.split(":", 1)
    return SemanticType(parse_expr(body), backend)


def parse_semantic_formula(source: str) -> SemanticFormula:
    backend, body = source.split(":", 1)
    return SemanticFormula(parse_expr(body), backend)
