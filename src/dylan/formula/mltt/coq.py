"""Export native constructive meanings with their declared nominal theory."""

from dylan.formula.mltt.terms import Expr, fresh_name, parse_expr


def coq_term(term: Expr, *, type_operators=frozenset()) -> str:
    if term.kind == "name":
        return {"top": "True", "CN": "Type", "Content": "Type", "unit": "I"}.get(
            term.name, term.name
        )
    args = [coq_term(arg, type_operators=type_operators) for arg in term.args]
    if term.kind == "sigma":
        return f"{{ {term.name} : {args[0]} & {args[1]} }}"
    if term.kind == "pi":
        return f"(forall {term.name} : {args[0]}, {args[1]})"
    if term.kind == "lam":
        return f"(fun {term.name} : {args[0]} => {args[1]})"
    if term.kind == "arrow":
        return f"({args[0]} -> {args[1]})"
    if term.kind == "app":
        return f"({args[0]} {args[1]})"
    if term.kind == "fst":
        return f"(projT1 {args[0]})"
    if term.kind == "neg":
        # A dependent witness type is refuted by a function to False. Coq
        # reserves ~ for Prop; Σ witness types inhabit Type.
        if _type_valued(term.args[0], type_operators):
            return f"({args[0]} -> False)"
        return f"(~ {args[0]})"
    if term.kind == "and":
        if any(_type_valued(a, type_operators) for a in term.args):
            return f"({args[0]} * {args[1]})%type"
        return f"({args[0]} /\\ {args[1]})"
    if term.kind == "predication":
        # Nominal predication asserts membership through the nominal inclusion.
        # It does not cast the subject into a subtype or assume an inhabitant.
        witness = fresh_name("member", term.free())
        projection, domain = witness, term.args[0]
        while domain.kind == "sigma":
            projection = f"(projT1 {projection})"
            domain = domain.args[0]
        return f"(exists {witness} : {args[0]}, ({projection} : object) = ({args[1]} : object))"
    raise ValueError(f"Cannot export {term.kind} to constructive Coq")


def _type_valued(term: Expr, type_operators=frozenset()) -> bool:
    return (term.kind == "sigma"
            or term.kind == "pi" and _type_valued(term.args[1], type_operators)
            or term.kind == "and" and any(_type_valued(a, type_operators) for a in term.args)
            or term.kind == "app" and term.args[0].kind == "name" and term.args[0].name in type_operators)


def export_coq(formula, *, minimal: bool = True) -> str:
    if formula.backend != "mltt":
        raise ValueError("Coq export is provided for constructive DS")
    theory = formula.theory
    needed = formula.term.free()
    constants = theory.get("constants", {})
    predicates = theory.get("predicates", {})
    modifiers = theory.get("modifiers", {})
    type_operators = frozenset(theory.get("content_modifiers", []))
    hierarchy = theory.get("subtyping", {})
    sorts = {"object"} | set(theory.get("sorts", [])) | set(hierarchy)
    sorts.update(parent for parents in hierarchy.values() for parent in parents)
    if not minimal:
        needed |= set(constants) | set(predicates) | set(modifiers) | sorts
    while True:
        before = set(needed)
        for symbol in list(needed):
            if symbol in constants:
                needed |= parse_expr(constants[symbol]).free()
            if symbol in predicates:
                for domain in predicates[symbol]:
                    needed |= parse_expr(domain).free()
        if needed == before:
            break
    frontier = list(needed & sorts)
    while frontier:
        child = frontier.pop()
        for parent in hierarchy.get(child, []):
            if parent not in needed:
                needed.add(parent)
                frontier.append(parent)
    lines = [
        "(* Native constructive DS: nominal inclusions and dependent meaning. *)",
        "Set Universe Polymorphism.",
    ]
    declared = (needed & sorts) - set(hierarchy)
    for sort in sorted(declared):
        lines.append(f"Parameter {sort} : Type.")
    pending = {child: parents for child, parents in hierarchy.items() if child in needed}
    while pending:
        ready = [
            (child, parents)
            for child, parents in pending.items()
            if len(parents) == 1 and parents[0] in declared
        ]
        if not ready:
            raise ValueError("Coq export needs an acyclic single-parent nominal hierarchy")
        for child, parents in ready:
            parent = parents[0]
            lines.append(
                f"Record {child} : Type := mk_{child} {{ as_{child}_{parent} :> {parent} }}."
            )
            declared.add(child)
            del pending[child]
    for symbol, domains in predicates.items():
        if symbol not in needed:
            continue
        rendered = ["Type" if domain in {"CN", "Content"} else domain for domain in domains]
        lines.append(f"Parameter {symbol} : {' -> '.join(rendered + ['Prop'])}.")
    for symbol in modifiers:
        if symbol not in needed:
            continue
        signature = "Type -> Type" if symbol in type_operators else "Prop -> Prop"
        lines.append(f"Parameter {symbol} : {signature}.")
    for symbol, typ in constants.items():
        if symbol in needed:
            lines.append(f"Parameter {symbol} : {coq_term(parse_expr(typ), type_operators=type_operators)}.")
    lines.append(f"Definition meaning : Type := {coq_term(formula.term, type_operators=type_operators)}.")
    lines.append("Check meaning.")
    return "\n".join(lines) + "\n"
