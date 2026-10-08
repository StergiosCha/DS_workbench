"""Immutable, capture-avoiding lambda, Π, Σ, projection and choice calculus.

The classical backend uses epsilon/tau nodes; the constructive backend never
constructs those nodes. Both share substitution and beta normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Expr:
    kind: str
    name: str = ""
    args: tuple[Expr, ...] = ()

    def free(self) -> set[str]:
        if self.kind == "name":
            return {self.name}
        if self.kind in {"lam", "pi", "sigma", "eps", "tau", "iota", "forall"}:
            return self.args[0].free() | (self.args[1].free() - {self.name})
        return set().union(*(arg.free() for arg in self.args))

    def substitute(self, variable: str, replacement: Expr) -> Expr:
        if self.kind == "name":
            return replacement if self.name == variable else self
        if self.kind in {"lam", "pi", "sigma", "eps", "tau", "iota", "forall"}:
            domain, body = self.args
            domain = domain.substitute(variable, replacement)
            if self.name == variable:
                return Expr(self.kind, self.name, (domain, body))
            binder = self.name
            if binder in replacement.free() and variable in body.free():
                fresh = fresh_name(binder, body.free() | replacement.free() | {variable})
                body = body.substitute(binder, name(fresh))
                binder = fresh
            return Expr(self.kind, binder, (domain, body.substitute(variable, replacement)))
        return Expr(
            self.kind, self.name, tuple(a.substitute(variable, replacement) for a in self.args)
        )

    def normalize(self, fuel: int = 200) -> Expr:
        if fuel <= 0:
            raise ValueError("Term normalization limit exceeded")
        args = tuple(arg.normalize(fuel - 1) for arg in self.args)
        if self.kind == "app" and args[0].kind == "lam":
            functor = args[0]
            return functor.args[1].substitute(functor.name, args[1]).normalize(fuel - 1)
        if self.kind == "fst" and args[0].kind == "pair":
            return args[0].args[0]
        if self.kind == "cn_body" and args[0].kind == "cn":
            return args[0].args[1]
        if self.kind == "cn_var" and args[0].kind == "cn":
            return args[0].args[0]
        if self.kind == "predication" and args[0].kind == "cn":
            head, restriction = args[0].args
            if head.kind != "name":
                raise TypeError("A classical predicative restrictor needs a variable head")
            return restriction.substitute(head.name, args[1]).normalize(fuel - 1)
        if self.kind in {"choice_eps", "choice_tau", "choice_iota"} and args[0].kind == "cn":
            head, restriction = args[0].args
            if head.kind != "name":
                raise TypeError("A classical cn restrictor needs a variable head")
            return Expr(
                {"choice_eps": "eps", "choice_tau": "tau", "choice_iota": "iota"}[self.kind], head.name, (name("e"), restriction)
            )
        return Expr(self.kind, self.name, args)

    def simplify(self) -> Expr:
        term = self.normalize()
        if term.kind in {"sigma", "pi"}:
            domain, body = term.args
            if domain.kind == "sigma" and domain.args[1] == name("top"):
                binder = fresh_name("x", body.free() | domain.free())
                body = body.substitute(term.name, Expr("pair", args=(name(binder), name("unit"))))
                return Expr(term.kind, binder, (domain.args[0], body)).simplify()
        return Expr(term.kind, term.name, tuple(arg.simplify() for arg in term.args))

    def to_tex(self) -> str:
        """Render mathematical notation, escaping lexical identifiers."""
        def identifier(value):
            return r"\mathit{" + value.replace("_", r"\_") + "}"

        if self.kind == "name":
            return {"top": r"\top", "unit": r"\star"}.get(self.name, identifier(self.name))
        args = [arg.to_tex() for arg in self.args]
        if self.kind in {"lam", "pi", "sigma", "eps", "tau", "iota", "forall"}:
            symbol = {"forall": r"\forall", "lam": r"\lambda", "pi": r"\Pi", "sigma": r"\Sigma",
                      "eps": r"\varepsilon", "tau": r"\tau", "iota": r"\iota"}[self.kind]
            return rf"{symbol} {identifier(self.name)} : \left({args[0]}\right).\; {args[1]}"
        if self.kind == "arrow":
            return rf"\left({args[0]} \to {args[1]}\right)"
        if self.kind == "app":
            return rf"\left({args[0]}\right)\left({args[1]}\right)"
        if self.kind == "fst":
            return rf"\pi_1\left({args[0]}\right)"
        if self.kind == "pair":
            return rf"\langle {args[0]}, {args[1]} \rangle"
        if self.kind == "cn":
            return rf"\left({args[0]}, {args[1]}\right)"
        if self.kind == "cn_body":
            return rf"\mathrm{{body}}\left({args[0]}\right)"
        if self.kind == "cn_var":
            return rf"\mathrm{{head}}\left({args[0]}\right)"
        if self.kind == "predication":
            return rf"{args[1]} \in \left({args[0]}\right)"
        if self.kind == "refine":
            return rf"\mathrm{{refine}}\left({args[0]}, {args[1]}\right)"
        if self.kind in {"choice_eps", "choice_tau", "choice_iota", "definite"}:
            symbol = {"choice_eps": r"\varepsilon", "choice_tau": r"\tau", "choice_iota": r"\iota", "definite": r"\mathrm{def}"}[self.kind]
            return rf"{symbol}\left({args[0]}\right)"
        if self.kind == "neg":
            return rf"\neg\left({args[0]}\right)"
        if self.kind == "implies":
            return rf"\left({args[0]} \Rightarrow {args[1]}\right)"
        if self.kind == "and":
            return rf"\left({args[0]} \land {args[1]}\right)"
        raise ValueError(f"Unknown term kind: {self.kind}")

    def __str__(self) -> str:
        if self.kind == "name":
            return "⊤" if self.name == "top" else self.name
        if self.kind == "arrow":
            left, right = self.args
            a = f"({left})" if left.kind in {"arrow", "pi", "sigma"} else str(left)
            return f"{a} → {right}"
        if self.kind in {"lam", "pi", "sigma", "eps", "tau", "iota", "forall"}:
            symbol = {"forall": "∀", "lam": "λ", "pi": "Π", "sigma": "Σ", "eps": "ε", "tau": "τ", "iota": "ι"}[self.kind]
            domain, body = self.args
            domain_text = f"({domain})" if domain.kind in {"sigma", "pi", "arrow"} else str(domain)
            return f"{symbol} {self.name}:{domain_text}. {body}"
        if self.kind == "app":
            fn, arg = self.args
            if fn.kind == "app":
                return str(fn)[:-1] + f", {arg})"
            return f"{f'({fn})' if fn.kind == 'lam' else fn}({arg})"
        if self.kind == "fst":
            return f"π₁({self.args[0]})"
        if self.kind == "pair":
            return f"⟨{self.args[0]}, {self.args[1]}⟩"
        if self.kind == "cn":
            return f"({self.args[0]}, {self.args[1]})"
        if self.kind == "cn_body":
            return f"body({self.args[0]})"
        if self.kind == "cn_var":
            return f"head({self.args[0]})"
        if self.kind == "predication":
            return f"({self.args[1]} ∈ {self.args[0]})"
        if self.kind == "refine":
            return f"refine({self.args[0]}, {self.args[1]})"
        if self.kind in {"choice_eps", "choice_tau", "choice_iota", "definite"}:
            return f"{ {'choice_eps': 'ε', 'choice_tau': 'τ', 'choice_iota': 'ι', 'definite': 'def'}[self.kind]}({self.args[0]})"
        if self.kind == "neg":
            return f"¬({self.args[0]})"
        if self.kind == "implies":
            return f"({self.args[0]} ⇒ {self.args[1]})"
        if self.kind == "and":
            return f"({self.args[0]} ∧ {self.args[1]})"
        raise ValueError(f"Unknown term kind: {self.kind}")

    def to_source(self) -> str:
        """Round-trippable constructor syntax for generated nominal declarations."""
        if self.kind == "name":
            return self.name
        args = [arg.to_source() for arg in self.args]
        if self.kind in {"lam", "pi", "sigma", "eps", "tau", "iota", "forall"}:
            args.insert(0, self.name)
        return f"{self.kind}({','.join(args)})"


def name(value: str) -> Expr:
    return Expr("name", value)


def arrow(domain: Expr, codomain: Expr) -> Expr:
    return Expr("arrow", args=(domain, codomain))


def app(function: Expr, argument: Expr) -> Expr:
    return Expr("app", args=(function, argument))


def fresh_name(base: str, used: set[str]) -> str:
    if base not in used:
        return base
    i = 1
    while f"{base}{i}" in used:
        i += 1
    return f"{base}{i}"


def parse_expr(source: str) -> Expr:
    """Parse explicit constructor syntax, e.g. ``lam(x,human,walk(x))``."""
    tokens = re.findall(r"[A-Za-z_][A-Za-z_0-9']*|[(),]", source)
    if "".join(tokens) != re.sub(r"\s+", "", source):
        raise ValueError(f"Invalid semantic expression: {source!r}")
    index = 0

    def parse() -> Expr:
        nonlocal index
        if index >= len(tokens) or tokens[index] in {"(", ")", ","}:
            raise ValueError("Expected a semantic term")
        symbol = tokens[index]
        index += 1
        if index == len(tokens) or tokens[index] != "(":
            return name(symbol)
        index += 1
        args = [parse()]
        while index < len(tokens) and tokens[index] == ",":
            index += 1
            args.append(parse())
        if index >= len(tokens) or tokens[index] != ")":
            raise ValueError("Unclosed semantic expression")
        index += 1
        if symbol in {"lam", "pi", "sigma", "eps", "tau", "iota", "forall"}:
            if len(args) != 3 or args[0].kind != "name":
                raise ValueError(f"{symbol} needs a binder, domain, and body")
            return Expr(symbol, args[0].name, tuple(args[1:]))
        arities = {
            "arrow": 2,
            "app": 2,
            "fst": 1,
            "pair": 2,
            "and": 2,
            "implies": 2,
            "neg": 1,
            "cn": 2,
            "cn_body": 1,
            "cn_var": 1,
            "predication": 2,
            "refine": 2,
            "choice_eps": 1,
            "choice_tau": 1,
            "choice_iota": 1,
            "definite": 1,
        }
        if symbol in arities:
            if len(args) != arities[symbol]:
                raise ValueError(f"Wrong arity for {symbol}")
            return Expr(symbol, args=tuple(args))
        term = name(symbol)
        for arg in args:
            term = app(term, arg)
        return term

    result = parse()
    if index != len(tokens):
        raise ValueError("Unexpected text after semantic expression")
    return result
