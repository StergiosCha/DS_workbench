"""A finite Stabler-style Merge/Move fragment with explicit feature checking.

Lexical selectors take right complements; subsequent selectors take left
specifiers. Licensees remain as movers; final Move fronts the pronounced copy.
The shortest-move restriction forbids competing movers with one licensee.
This fragment does not assert universal phase or cartographic constraints.
"""

from dataclasses import dataclass
from itertools import combinations

from dylan.hybrid.terms import Term, app, const, lam, names, normalize, var


class DerivationError(ValueError):
    pass


@dataclass(frozen=True)
class Mover:
    words: tuple[str, ...]
    features: tuple[str, ...]
    variable: str
    meaning: Term


@dataclass(frozen=True)
class Expression:
    words: tuple[str, ...]
    features: tuple[str, ...]
    meaning: Term
    movers: tuple[Mover, ...] = ()
    lexical: bool = True
    leaves: frozenset[int] = frozenset()
    history: tuple[dict, ...] = ()

    def key(self):
        return (self.words, self.features, str(self.meaning), self.movers, self.lexical, self.leaves)

    def to_dict(self):
        return {"words": self.words, "features": self.features,
                "meaning": str(normalize(self.meaning)),
                "movers": [{"words": m.words, "features": m.features, "variable": m.variable} for m in self.movers],
                "history": self.history}


def well_formed_movers(movers):
    first = [m.features[0] for m in movers]
    if any(not f.startswith("-") for f in first) or len(first) != len(set(first)):
        raise DerivationError("Shortest Move: competing or malformed licensees")


def merge(selector, selected):
    if selector.leaves & selected.leaves:
        raise DerivationError("External Merge requires disjoint lexical occurrences")
    if not selector.features or not selected.features or selector.features[0] != "=" + selected.features[0]:
        raise DerivationError("Unmatched selector/category")
    remaining = selected.features[1:]
    movers = (*selector.movers, *selected.movers)
    argument = selected.meaning
    if remaining:
        if any(not f.startswith("-") for f in remaining):
            raise DerivationError("Selected chain must retain licensees only")
        variable = "x" + "_".join(str(i) for i in sorted(selected.leaves))
        occupied = names(selector.meaning) | names(selected.meaning) | {m.variable for m in movers}
        while variable in occupied:
            variable += "_"
        movers = (*movers, Mover(selected.words, remaining, variable, argument))
        argument, words = var(variable), selector.words
    else:
        words = selector.words + selected.words if selector.lexical else selected.words + selector.words
    well_formed_movers(movers)
    return Expression(words, selector.features[1:], normalize(app(selector.meaning, argument)), movers,
                      False, selector.leaves | selected.leaves,
                      (*selector.history, *selected.history,
                       {"operation": "Merge", "selector": selector.features[0],
                        "selected": selected.words, "lower_copy_pronounced": not bool(remaining)}))


def move(expression):
    if not expression.features or not expression.features[0].startswith("+"):
        raise DerivationError("Move requires an active licensor")
    feature = "-" + expression.features[0][1:]
    matches = [m for m in expression.movers if m.features[0] == feature]
    if len(matches) != 1:
        raise DerivationError("Move requires one matching licensee")
    mover = matches[0]
    movers = tuple(m for m in expression.movers if m is not mover)
    if len(mover.features) > 1:
        movers += (Mover(mover.words, mover.features[1:], mover.variable, mover.meaning),)
        words, meaning = expression.words, expression.meaning
    else:
        words = mover.words + expression.words
        meaning = app(mover.meaning, lam(mover.variable, expression.meaning))
    well_formed_movers(movers)
    return Expression(words, expression.features[1:], normalize(meaning), movers, False,
                      expression.leaves, (*expression.history,
                      {"operation": "Move", "licensor": expression.features[0],
                       "chain": mover.variable, "pronounced": len(mover.features) == 1}))


def item(word, features, meaning, identity):
    return Expression((word,) if word else (), tuple(features), meaning, leaves=frozenset([identity]),
                      history=({"operation": "Lexical", "word": word, "features": tuple(features), "occurrence": identity},))


def lexical_entries(word, identity):
    if word in {"john", "mary", "the-book"}:
        return [item(word, ["d"], const(word), identity)]
    if word in {"who", "what"}:
        return [item(word, ["d", "-wh"], const(word), identity)]
    if word in {"likes", "like", "read", "reads", "met"}:
        meaning = lam("o", lam("s", app(app(const(word), var("s")), var("o"))))
        return [item(word, ["=d", "=d", "v"], meaning, identity)]
    if word in {"walks", "sleeps"}:
        return [item(word, ["v0"], lam("s", app(const(word), var("s"))), identity)]
    if word == "did":
        return [item(word, ["=v", "+wh", "c"], lam("p", var("p")), identity)]
    return []


def parse(text, *, cap=10000):
    words = text.lower().split()
    if not 1 <= len(words) <= 8:
        raise ValueError("MG comparison fragment supports 1–8 overt tokens")
    entries = [lexical_entries(w, i) for i, w in enumerate(words)]
    unknown = [w for w, e in zip(words, entries) if not e]
    if unknown:
        return {"status": "unsupported_lexicon", "unknown": unknown, "analyses": []}
    # Optional null declarative C is a declared lexical item, not a hidden repair.
    epsilon_id = len(words)
    entries.append([item("", ["=v", "c"], lam("p", var("p")), epsilon_id),
                    item("", ["=v0", "=d", "c"], lam("p", var("p")), epsilon_id)])
    chart = {frozenset([i]): {e.key(): e for e in group} for i, group in enumerate(entries)}
    built, limited = sum(map(len, entries)), False

    def closure(expression):
        output = [expression]
        while expression.features and expression.features[0].startswith("+"):
            try:
                expression = move(expression)
            except DerivationError:
                break
            output.append(expression)
        return output

    for size in range(2, len(entries) + 1):
        for indices in combinations(range(len(entries)), size):
            cell, whole = {}, frozenset(indices)
            for left_size in range(1, size):
                for left_indices in combinations(indices, left_size):
                    left_set = frozenset(left_indices)
                    for left in chart.get(left_set, {}).values():
                        for right in chart.get(whole - left_set, {}).values():
                            try:
                                merged = merge(left, right)
                            except DerivationError:
                                continue
                            for result in closure(merged):
                                if result.key() not in cell:
                                    built += 1
                                    if built > cap:
                                        limited = True
                                        break
                                    cell[result.key()] = result
                            if limited:
                                break
                        if limited:
                            break
                    if limited:
                        break
                if limited:
                    break
            chart[whole] = cell
            if limited:
                break
        if limited:
            break
    finals = []
    for subset in [frozenset(range(len(words))), frozenset(range(len(entries)))]:
        for expression in chart.get(subset, {}).values():
            if expression.words == tuple(words) and expression.features == ("c",) and not expression.movers:
                finals.append(expression.to_dict())
    return {"status": "search_limit" if limited else "derived" if finals else "no_derivation_in_fragment",
            "analyses": finals, "expressions_built": built,
            "config": {"bound": cap, "shortest_move": True, "phases": "not assumed",
                       "interpretation": "final movement binds a lower-copy variable with the mover operator"}}
