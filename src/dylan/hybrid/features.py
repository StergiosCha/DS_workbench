"""Finite typed feature graphs with appropriateness and reentrant unification.

This is a constraint kernel, not a claim to implement the whole HPSG framework.
Partial descriptions may omit appropriate features; explicit paths must be typed.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field


class UnificationError(ValueError):
    pass


@dataclass
class TypeSystem:
    parents: dict[str, tuple[str, ...]]
    appropriateness: dict[str, dict[str, str]] = field(default_factory=dict)

    def ancestors(self, sort, seen=None):
        if sort not in self.parents:
            raise UnificationError(f"Unknown sort {sort}")
        seen = set() if seen is None else seen
        if sort in seen:
            raise UnificationError("Cyclic type hierarchy")
        result = {sort}
        for parent in self.parents[sort]:
            result.update(self.ancestors(parent, seen | {sort}))
        return result

    def subtype(self, specific, general):
        return general in self.ancestors(specific)

    def meet(self, first, second):
        common = [t for t in self.parents if self.subtype(t, first) and self.subtype(t, second)]
        most_general = [t for t in common if not any(t != u and self.subtype(t, u) for u in common)]
        if len(most_general) != 1:
            raise UnificationError(f"No unique type meet: {first}, {second}")
        return most_general[0]

    def appropriate(self, sort):
        result = {}
        for ancestor in sorted(self.ancestors(sort)):
            for feature, value_sort in self.appropriateness.get(ancestor, {}).items():
                result[feature] = self.meet(result[feature], value_sort) if feature in result else value_sort
        return result


@dataclass
class Node:
    sort: str
    features: dict[str, str] = field(default_factory=dict)
    atom: str | None = None


@dataclass
class FeatureGraph:
    root: str
    nodes: dict[str, Node]

    def at(self, path):
        current = self.root
        for feature in path:
            current = self.nodes[current].features[feature]
        return current

    def validate(self, types):
        if self.root not in self.nodes:
            raise UnificationError("Missing graph root")
        for key, node in self.nodes.items():
            allowed = types.appropriate(node.sort)
            for feature, target in node.features.items():
                if feature not in allowed:
                    raise UnificationError(f"Feature {feature} inappropriate for {node.sort}")
                if target not in self.nodes:
                    raise UnificationError(f"Dangling feature reference {key}.{feature}")
                if not types.subtype(self.nodes[target].sort, allowed[feature]):
                    raise UnificationError(f"Wrong value sort on {key}.{feature}")
        return self

    def canonical(self):
        labels, queue, result = {self.root: "n0"}, deque([self.root]), {}
        while queue:
            key = queue.popleft()
            node = self.nodes[key]
            edges = {}
            for feature, target in sorted(node.features.items()):
                if target not in labels:
                    labels[target] = f"n{len(labels)}"
                    queue.append(target)
                edges[feature] = labels[target]
            result[labels[key]] = {"type": node.sort, "features": edges, "atom": node.atom}
        return {"root": "n0", "nodes": result}

    @classmethod
    def description(cls, mapping):
        nodes = {}

        def add(value):
            key = f"n{len(nodes)}"
            nodes[key] = Node(value["type"], atom=value.get("atom"))
            nodes[key].features = {f: add(v) for f, v in value.get("features", {}).items()}
            return key

        root = add(mapping)
        return cls(root, nodes)


def unify(left: FeatureGraph, right: FeatureGraph, types: TypeSystem) -> FeatureGraph:
    """Nonmutating unification, preserving sharing and finite graph cycles."""
    left.validate(types)
    right.validate(types)
    nodes = {}
    for prefix, graph in (("L", left), ("R", right)):
        for key, node in graph.nodes.items():
            nodes[prefix + key] = Node(node.sort, {f: prefix + v for f, v in node.features.items()}, node.atom)
    parent = {key: key for key in nodes}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    pending = [("L" + left.root, "R" + right.root)]
    while pending:
        a, b = (find(key) for key in pending.pop())
        if a == b:
            continue
        x, y = nodes[a], nodes[b]
        sort = types.meet(x.sort, y.sort)
        if x.atom is not None and y.atom is not None and x.atom != y.atom:
            raise UnificationError(f"Conflicting atoms: {x.atom}, {y.atom}")
        parent[b] = a
        x.sort, x.atom = sort, x.atom if x.atom is not None else y.atom
        for feature, target in y.features.items():
            if feature in x.features:
                pending.append((x.features[feature], target))
            else:
                x.features[feature] = target
    # A newly refined parent sort can strengthen an existing value restriction.
    changed = True
    while changed:
        changed = False
        for key, node in nodes.items():
            if find(key) != key:
                continue
            allowed = types.appropriate(node.sort)
            for feature, target in node.features.items():
                if feature not in allowed:
                    raise UnificationError(f"Feature {feature} inappropriate for {node.sort}")
                value = nodes[find(target)]
                refined = types.meet(value.sort, allowed[feature])
                changed |= refined != value.sort
                value.sort = refined
    result = {key: Node(n.sort, {f: find(v) for f, v in n.features.items()}, n.atom)
              for key, n in nodes.items() if find(key) == key}
    return FeatureGraph(find("L" + left.root), result).validate(types)


def linguistic_types():
    parents = {"top": (), "sign": ("top",), "nominal": ("sign",), "clause": ("sign",),
               "agreement": ("top",), "gender": ("top",), "number": ("top",),
               "case": ("top",), "person": ("top",), "referent": ("top",), "symbol": ("top",)}
    for general, specifics in {"gender": ["masc", "fem", "neut"], "number": ["sg", "pl"],
                               "case": ["nom", "acc", "gen"], "person": ["1", "2", "3"]}.items():
        parents.update({s: (general,) for s in specifics})
    return TypeSystem(parents, {"sign": {"AGR": "agreement", "INDEX": "referent", "HEAD": "symbol"},
                               "agreement": {"GENDER": "gender", "NUMBER": "number", "PERSON": "person", "CASE": "case"}})


def nominal_description(*, gender=None, number=None, case=None, person=None, referent=None):
    values = {"GENDER": gender, "NUMBER": number, "CASE": case, "PERSON": person}
    features = {"AGR": {"type": "agreement", "features": {k: {"type": v} for k, v in values.items() if v}}}
    if referent is not None:
        features["INDEX"] = {"type": "referent", "atom": referent}
    return FeatureGraph.description({"type": "nominal", "features": features})


@dataclass
class Construction:
    name: str
    parents: tuple[str, ...]
    constraints: FeatureGraph
    meaning: str
    source: str


class ConstructionRegistry:
    """Monotonic multiple inheritance: incompatible parents raise, never silently override."""

    def __init__(self, types):
        self.types, self.entries = types, {}

    def add(self, construction):
        if construction.name in self.entries:
            raise ValueError("Construction already registered")
        self.entries[construction.name] = construction
        try:
            self.resolve(construction.name)
        except (ValueError, KeyError):
            del self.entries[construction.name]
            raise

    def resolve(self, name, path=()):
        if name in path:
            raise ValueError("Construction inheritance cycle")
        entry = self.entries[name]
        result = deepcopy(entry.constraints)
        result.validate(self.types)
        for parent in entry.parents:
            result = unify(result, self.resolve(parent, (*path, name)), self.types)
        return result

    def match(self, name, sign):
        return unify(self.resolve(name), sign, self.types)
