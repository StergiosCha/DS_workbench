"""Clause-local scope for individual-valued classical epsilon/tau terms.

For an open clause B(x), restricted universal closure uses
    H(x) = R(x) -> B(x);  H(tau x.H(x)).
Restricted existential closure uses
    H(x) = R(x) & B(x);   H(epsilon x.H(x)).
These are Hilbert choice identities, not generalized-quantifier lexical
entries. NPs still contribute type e. Inner choices are constructed before
outer choices, so narrow-scope epsilon terms contain the doctor parameter.

The choice_scope node records an already closed clause boundary. It is
transparent in mathematical output and prevents an embedded clause's choices
from being re-scoped by its parent. Bare epsilon-only clauses retain the
existing nominal-choice interpretation; this module resolves clauses with
tau choices and any accompanying indefinites.
"""

from dataclasses import dataclass

from dylan.formula.mltt.terms import Expr, fresh_name, name


@dataclass(frozen=True)
class Choice:
    variable: str
    kind: str
    domain: Expr
    restriction: Expr


def close_choices(term: Expr, scope: str = "narrow") -> Expr:
    if scope not in {"narrow", "wide"}:
        raise ValueError("Choice scope must be narrow or wide")
    # Do not collect a choice out of a lambda, nominal restrictor, or an
    # already closed content clause. Free parameters of those clauses remain
    # available to ordinary capture-avoiding substitution.
    opaque = {"lam", "pi", "sigma", "iota", "choice_scope"}
    used = set()

    def names(node):
        if node.name:
            used.add(node.name)
        for arg in node.args:
            names(arg)

    names(term)
    choices = []
    references = {}

    def abstract(node):
        if node.kind in opaque:
            return node
        if node.kind in {"eps", "tau"}:
            if node not in references:
                variable = fresh_name("c", used)
                used.add(variable)
                references[node] = name(variable)
                domain, restriction = node.args
                choices.append(Choice(variable, node.kind, domain,
                                      restriction.substitute(node.name, name(variable))))
            return references[node]
        return Expr(node.kind, node.name, tuple(abstract(arg) for arg in node.args))

    body = abstract(term)
    if not choices:
        return term
    if not any(choice.kind == "tau" for choice in choices):
        return Expr("choice_scope", args=(term,))
    # This explicit setting orders indefinites relative to universals. It
    # does not claim to enumerate all scope orders or discourse readings.
    outer = "tau" if scope == "narrow" else "eps"
    choices.sort(key=lambda choice: choice.kind != outer)
    for choice in reversed(choices):
        restriction = choice.restriction
        condition = Expr("implies" if choice.kind == "tau" else "and",
                         args=(restriction, body))
        selected = Expr(choice.kind, choice.variable, (choice.domain, condition))
        body = condition.substitute(choice.variable, selected)
        # Expanded choice formulas duplicate their restrictors. Keep the
        # operational bound explicit rather than exhausting a worker.
        if size(body, 20000) > 20000:
            raise TypeError("Classical choice-scope expansion limit exceeded")
    return Expr("choice_scope", args=(body,))


def size(term: Expr, limit: int) -> int:
    count = 0
    pending = [term]
    while pending and count <= limit:
        node = pending.pop()
        count += 1
        pending.extend(node.args)
    return count
