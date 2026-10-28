"""Explicit bounded f-structures and functional uncertainty.

Grammatical functions are primitive in this configuration. A separate MG
configuration may derive analogous relations; no equivalence is assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Predicate:
    name: str
    arguments: tuple[str, ...]


@dataclass
class FStructure:
    root: str
    predicates: dict[str, Predicate]
    functions: dict[str, dict[str, str]] = field(default_factory=dict)
    morphology: dict[str, dict[str, str]] = field(default_factory=dict)
    mappings: list[dict] = field(default_factory=list)

    def check(self, *, closed=False):
        issues, pending = [], []
        governed = {"SUBJ", "OBJ", "OBJ2", "COMP", "XCOMP", "OBL"}
        for node, pred in self.predicates.items():
            fields = self.functions.get(node, {})
            for arg in pred.arguments:
                if arg not in fields:
                    (issues if closed else pending).append({"node": node, "kind": "completeness", "function": arg})
            for function, target in fields.items():
                if target not in self.predicates:
                    issues.append({"node": node, "kind": "dangling_reference", "function": function})
                if function in governed and function not in pred.arguments:
                    issues.append({"node": node, "kind": "coherence", "function": function})
        if self.root not in self.predicates:
            issues.append({"kind": "missing_root"})
        return {"valid": not issues, "complete": not issues and not pending,
                "pending": pending, "issues": issues, "closed": closed}

    def uncertainty(self, repeated, terminal, *, max_depth=4):
        """Resolve (COMP|XCOMP)* OBJ under an explicit bound, retaining paths."""
        if max_depth < 0 or not repeated or not terminal:
            raise ValueError("A finite bound and nonempty path alphabet are required")
        frontier = [(self.root, ())]
        matches, truncated = [], False
        while frontier:
            node, path = frontier.pop()
            fields = self.functions.get(node, {})
            if terminal in fields:
                matches.append({"path": (*path, terminal), "node": fields[terminal]})
            for function in repeated:
                if function not in fields:
                    continue
                if len(path) >= max_depth:
                    truncated = True
                else:
                    frontier.append((fields[function], (*path, function)))
        return {"matches": matches, "bound": max_depth, "truncated": truncated}

    def link_topic(self, target, *, repeated=("COMP",), terminal="OBJ", max_depth=4):
        paths = self.uncertainty(repeated, terminal, max_depth=max_depth)
        licensed = [m for m in paths["matches"] if m["node"] == target]
        if not licensed:
            return {"linked": False, "reason": "bound_exhausted" if paths["truncated"] else "no_matching_function", **paths}
        existing = self.functions.setdefault(self.root, {}).get("TOPIC")
        if existing is not None and existing != target:
            return {"linked": False, "reason": "functional_uniqueness"}
        self.functions[self.root]["TOPIC"] = target
        return {"linked": True, "paths": licensed, "truncated": paths["truncated"]}

    def to_dict(self):
        return {"root": self.root, "predicates": {k: {"name": p.name, "arguments": p.arguments} for k, p in self.predicates.items()},
                "functions": self.functions, "morphology": self.morphology,
                "mappings": self.mappings}


def transitive(subject, verb, obj=None):
    predicates = {"f0": Predicate(verb, ("SUBJ", "OBJ")), "f1": Predicate(subject, ())}
    functions = {"f0": {"SUBJ": "f1"}}
    if obj is not None:
        predicates["f2"] = Predicate(obj, ())
        functions["f0"]["OBJ"] = "f2"
    return FStructure("f0", predicates, functions)
