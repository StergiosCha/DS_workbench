"""Small lambda calculus used by the experimental MG and CCG fragments."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    kind: str
    name: str = ""
    children: tuple["Term", ...] = ()

    def __str__(self):
        if self.kind in {"var", "const"}:
            return self.name
        if self.kind == "lam":
            return f"λ{self.name}.{self.children[0]}"
        return f"({self.children[0]} {self.children[1]})"


def var(name):
    return Term("var", name)


def const(name):
    return Term("const", name)


def lam(name, body):
    return Term("lam", name, (body,))


def app(function, argument):
    return Term("app", children=(function, argument))


def free(term):
    if term.kind == "var":
        return {term.name}
    if term.kind == "const":
        return set()
    if term.kind == "lam":
        return free(term.children[0]) - {term.name}
    return free(term.children[0]) | free(term.children[1])


def names(term):
    return ({term.name} if term.name else set()).union(*(names(c) for c in term.children))


def substitute(term, name, value):
    if term.kind == "var":
        return value if term.name == name else term
    if term.kind == "const":
        return term
    if term.kind == "lam":
        if term.name == name:
            return term
        binder, body = term.name, term.children[0]
        if binder in free(value):
            used = names(term) | names(value) | {name}
            fresh = binder + "_"
            while fresh in used:
                fresh += "_"
            body, binder = substitute(body, binder, var(fresh)), fresh
        return lam(binder, substitute(body, name, value))
    return app(substitute(term.children[0], name, value), substitute(term.children[1], name, value))


def normalize(term, fuel=1000):
    """Normal-order reduction, bounded even for malformed untyped terms."""
    def step(t):
        if t.kind == "app":
            f, a = t.children
            if f.kind == "lam":
                return substitute(f.children[0], f.name, a), True
            f2, changed = step(f)
            if changed:
                return app(f2, a), True
            a2, changed = step(a)
            return app(f, a2), changed
        if t.kind == "lam":
            body, changed = step(t.children[0])
            return lam(t.name, body), changed
        return t, False
    for _ in range(fuel):
        term, changed = step(term)
        if not changed:
            return term
    raise ValueError("Lambda reduction bound exceeded")
