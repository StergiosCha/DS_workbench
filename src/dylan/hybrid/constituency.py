"""Explicit POS phrase grammar and bounded completed/unfinished tree fragments.

The grammar is a declared comparison hypothesis. Its constituents are not gold
annotations or the paper's Berkeley-parser judgments. Holes occur at the right
frontier only; supplied left contexts are processed as ordinary observed input.
"""

from dataclasses import dataclass
from functools import lru_cache


RULES = {
    "S": [("NP", "VP"), ("S", "SCOORD")],
    "SCOORD": [("CCONJ", "S")],
    "NP": [("PRON",), ("PROPN",), ("NBAR",), ("DET", "NBAR"), ("NP", "PP"), ("NP", "NPCOORD")],
    "NPCOORD": [("CCONJ", "NP")],
    "NBAR": [("NOUN",), ("ADJ", "NBAR"), ("NBAR", "PP")],
    "VP": [("VERB",), ("VERB", "NP"), ("VERB", "PP"), ("VERB", "CP"),
           ("AUX", "VP"), ("VP", "ADV"), ("VP", "PP"), ("VP", "VPCOORD")],
    "VPCOORD": [("CCONJ", "VP")],
    "PP": [("ADP", "NP")],
    "CP": [("SCONJ", "S")],
}


@dataclass(frozen=True)
class Tree:
    label: str
    start: int
    end: int
    children: tuple["Tree", ...] = ()
    hole: bool = False

    def signature(self, depth=3):
        if self.hole:
            return f"?{self.label}"
        if not self.children or depth == 0:
            return self.label
        return f"{self.label}({','.join(c.signature(depth - 1) for c in self.children)})"


@lru_cache(maxsize=4096)
def fragments(tags, context=(), *, partial=True, cap=24, depth=3):
    tokens = (*context, *tags)
    size, offset = len(tokens), len(context)
    if not size or size > 16:
        return {"features": (), "limited": False, "status": "unsupported_length"}
    chart, limited = {}, False

    def add(cell, tree):
        nonlocal limited
        trees = cell.setdefault(tree.label, {})
        key = tree.signature(depth=16)
        if key not in trees and len(trees) >= cap:
            limited = True
        else:
            trees[key] = tree

    for width in range(1, size + 1):
        for start in range(size - width + 1):
            end, cell = start + width, {}
            if width == 1:
                add(cell, Tree(tokens[start], start, end))
            for split in range(start + 1, end):
                for lhs, productions in RULES.items():
                    for rhs in productions:
                        if len(rhs) != 2:
                            continue
                        for a in chart[start, split].get(rhs[0], {}).values():
                            for b in chart[split, end].get(rhs[1], {}).values():
                                add(cell, Tree(lhs, start, end, (a, b)))
            # Unary closure; this grammar's unary relation is acyclic.
            changed = True
            while changed:
                before = sum(map(len, cell.values()))
                for lhs, productions in RULES.items():
                    for rhs in productions:
                        if len(rhs) == 1:
                            for child in list(cell.get(rhs[0], {}).values()):
                                add(cell, Tree(lhs, start, end, (child,)))
                changed = before != sum(map(len, cell.values()))
            chart[start, end] = cell
    features = set()
    # Completed fragments are local subtrees; right-frontier partial rules retain holes.
    for (start, end), cell in chart.items():
        if end <= offset:
            continue
        for label, trees in cell.items():
            if label not in RULES:
                continue
            for tree in trees.values():
                features.add(tree.signature(depth))
                if partial and end == size:
                    for lhs, productions in RULES.items():
                        for rhs in productions:
                            if len(rhs) == 2 and rhs[0] == label:
                                features.add(Tree(lhs, start, end, (tree, Tree(rhs[1], end, end, hole=True))).signature(depth))
        if partial and end == size:
            for lhs, productions in RULES.items():
                for rhs in productions:
                    if len(rhs) == 2 and rhs[0] in cell:
                        for tree in cell[rhs[0]].values():
                            features.add(Tree(lhs, start, end, (tree, Tree(rhs[1], end, end, hole=True))).signature(depth))
    if partial:
        @lru_cache(maxsize=None)
        def unfinished(label, start, remaining):
            nonlocal limited
            if start == size:
                return (Tree(label, size, size, hole=True),)
            if remaining == 0 or label not in RULES:
                return ()
            found = {}
            for rhs in RULES[label]:
                candidates = []
                if len(rhs) == 1:
                    candidates = [(child,) for child in unfinished(rhs[0], start, remaining - 1)]
                else:
                    for split in range(start + 1, size + 1):
                        for left in chart[start, split].get(rhs[0], {}).values():
                            candidates.extend((left, right) for right in unfinished(rhs[1], split, remaining - 1))
                for children in candidates:
                    tree = Tree(label, start, size, children)
                    signature = tree.signature(16)
                    if signature not in found and len(found) >= cap:
                        limited = True
                    else:
                        found[signature] = tree
            return tuple(found.values())
        for start in range(size):
            for label in RULES:
                for tree in unfinished(label, start, depth):
                    features.add(tree.signature(depth))
    return {"features": tuple(sorted(features)), "limited": limited,
            "status": "features_available" if features else "no_features_in_fragment",
            "interpretation": "bounded completed subtrees and right-frontier holes; no full-parse claim"}
