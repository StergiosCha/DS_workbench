"""Finite causal clauses with local content closure and explicit DS growth.

because(main, reason) is an opaque relation between clause contents, not and.
Postposed reasons grow a LINK; preposed reasons occupy a curried content slot.
"""
from dylan.action.atomic.effect import Effect
from dylan.action.atomic.delete import Delete
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.atomic.semantic_effects import _sequence
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
from dylan.formula.mltt.terms import Expr, app, arrow, fresh_name, name
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, TypeLabel
from dylan.tree.modality import Modality
from dylan.clause_inventory import RELATIONS


def _complete_below(tree, node):
    return all(n.is_complete() for a, n in tree.items() if str(a).startswith(str(node.address)))


def _content_clause(prop):
    return [Put(Requirement(TypeLabel(prop))), Put(FeatureLabel("CLAUSE")),
            Put(FeatureLabel("CAUSAL-CONTENT")), Put(Requirement(FeatureLabel("CLOSED")))]


def _seal_contents(tree, origin, root):
    """A captured content must not be overwritten by a later VP modifier.

    Seal embedded clauses too: otherwise a later adverb can revisit an earlier
    subordinate VP and recompute away the enclosing connective's captured main.
    Return to the original pointer before continuing ordinary DS growth.
    """
    effects = []
    for address, child in tree.items():
        if str(address).startswith(str(root.address)) and child.contains(FeatureLabel("CLAUSE")):
            effects += [Go(Modality.relating(origin.address, address)), Put(FeatureLabel("CAUSAL-SEALED")),
                        Go(Modality.relating(address, origin.address))]
    return effects


class CausalEffect(Effect):
    def __init__(self, operation, relation="because"):
        if relation not in RELATIONS:
            raise ValueError("Unknown finite-clause relation")
        self.operation = operation
        self.relation = relation

    def exec_tuple_context(self, tree, context):
        backend = tree.semantic_profile.get("backend")
        if backend not in {"mltt", "classical"} or tree.semantic_profile.get("predicates", {}).get(self.relation) != ["Content", "Content"]:
            return None
        prop = SemanticType(name("Prop" if backend == "mltt" else "t"), backend)
        content = name("Content" if backend == "mltt" else "t")
        node = tree.pointed_node
        if self.operation == "causal-post":
            # Supplemental assertion projection through a content-taking
            # connective is a separate semantic obligation, not conjunction
            # inside that connective's main argument.
            if any(child.contains(FeatureLabel("APPOS")) for child in tree.values()):
                return None
            typ, formula = node.get_type(), node.get_formula()
            if (not isinstance(formula, SemanticFormula) or not isinstance(typ, SemanticType)
                    or formula.backend != backend or typ.backend != backend
                    or typ.term not in {prop.term, content} or not _complete_below(tree, node)):
                return None
            if typ.term == name("Content") and not node.contains(FeatureLabel("CLAUSE")):
                return None
            main = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow")).term
            variable = fresh_name("reason", main.free())
            term = Expr("lam", variable, (content, app(app(name(self.relation), main), name(variable))))
            moves, anchor = [], node
            while anchor.address.down_link() in tree:
                anchor = tree[anchor.address.down_link()]
                moves.append(Go.parse(r"go(\/L)"))
            return _sequence(tree, context, [*_seal_contents(tree, node, node), Put(FeatureLabel("CAUSAL-HOST")), *moves,
                Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
                Put(FeatureLabel("CAUSAL-LINK")), Put(FeatureLabel("CAUSAL-UPDATE")), Put(Requirement(TypeLabel(prop))),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(TypeLabel(SemanticType(arrow(content, prop.term), backend))),
                Put(FormulaLabel(SemanticFormula(term, backend, (), tree.semantic_profile))),
                Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                *_content_clause(prop),
            ])
        if self.operation == "causal-front":
            if (node.get_required_type() != prop or node.get_formula() is not None
                    or node.address.down0() in tree or node.address.down1() in tree):
                return None
            return _sequence(tree, context, [
                Put(FeatureLabel("CAUSAL-FRONT")), Put(FeatureLabel("VERB")),
                Put(FeatureLabel("CLAUSE-REL-" + self.relation)),
                Put(Requirement(FeatureLabel("CAUSAL-BOUNDARY"))),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(Requirement(TypeLabel(SemanticType(arrow(content, prop.term), backend)))),
                Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                *_content_clause(prop),
            ])
        if self.operation == "causal-boundary":
            anchor = node
            while not anchor.contains(FeatureLabel("CAUSAL-FRONT")):
                parent = anchor.address.up()
                if parent not in tree:
                    return None
                anchor = tree[parent]
            pending = Requirement(FeatureLabel("CAUSAL-BOUNDARY"))
            reason, continuation = tree.get(anchor.address.down0()), tree.get(anchor.address.down1())
            if (not anchor.contains(pending) or reason is None or continuation is None
                    or not reason.contains(FeatureLabel("CLOSED")) or not _complete_below(tree, reason)
                    or reason.get_type() != SemanticType(content, backend)
                    or continuation.get_formula() is not None or continuation.address.down0() in tree
                    or continuation.address.down1() in tree):
                return None
            if tree.pointer not in {anchor.address, reason.address, continuation.address}:
                # Do not jump out of a completed but not yet propagated modifier
                # LINK. Ordinary DS ascent must update the reason's formula first.
                return None
            relations = [r for r in RELATIONS if anchor.contains(FeatureLabel("CLAUSE-REL-" + r))]
            if len(relations) != 1 or tree.semantic_profile.get("predicates", {}).get(relations[0]) != ["Content", "Content"]:
                return None
            term = Expr("lam", "main", (content, Expr("lam", "reason", (content,
                app(app(name(relations[0]), name("main")), name("reason"))))))
            return _sequence(tree, context, [
                *_seal_contents(tree, node, reason),
                Go(Modality.relating(tree.pointer, anchor.address)), Delete(pending),
                Go.parse(r"go(\/0)"), Put(FeatureLabel("CAUSAL-SEALED")), Go.parse(r"go(/\0)"),
                Go.parse(r"go(\/1)"),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(TypeLabel(SemanticType(arrow(content, arrow(content, prop.term)), backend))),
                Put(FormulaLabel(SemanticFormula(term, backend, (), tree.semantic_profile))),
                Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                *_content_clause(prop),
            ])
        if self.operation == "causal-link-close":
            if (not node.contains(FeatureLabel("CAUSAL-LINK"))
                    or not str(node.address).endswith("L") or not _complete_below(tree, node)):
                return None
            formula = node.get_formula()
            if not isinstance(formula, SemanticFormula) or formula.backend != backend or node.get_type() != prop:
                return None
            formula = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow"))
            effects = [Delete(FeatureLabel("CAUSAL-UPDATE"))]
            host = node
            while str(host.address).endswith("L"):
                host = tree[host.address.up()]
                effects.append(Go.parse(r"go(/\L)"))
                effects.extend(Delete(lab) for lab in host.labels if isinstance(lab, FormulaLabel))
                effects.append(Put(FormulaLabel(formula)))
                if host.get_type() is None:
                    effects += [Put(TypeLabel(prop)), Delete(Requirement(TypeLabel(prop)))]
            # An embedded host is still a locally closed Content. Recompute
            # enclosing applications after updating it; retain its DS subtree.
            parent_address = host.address.up()
            while parent_address in tree:
                parent = tree[parent_address]
                actual = parent.get_type()
                effects.append(Go.parse(r"go(/\)"))
                if isinstance(actual, SemanticType):
                    effects.extend(Delete(lab) for lab in parent.labels if isinstance(lab, (TypeLabel, FormulaLabel)))
                    if parent.contains(FeatureLabel("CLOSED")):
                        effects += [Delete(FeatureLabel("CLOSED")), Put(Requirement(FeatureLabel("CLOSED")))]
                        actual = prop
                    if parent.contains(FeatureLabel("NEG")) and not parent.contains(FeatureLabel("NEGATED")) and not parent.contains(FeatureLabel("CAUSAL-HOST")):
                        effects += [Delete(FeatureLabel("NEG")), Put(Requirement(FeatureLabel("NEG")))]
                    effects.append(Put(Requirement(TypeLabel(actual))))
                    if parent.contains(FeatureLabel("CAUSAL-LINK")):
                        effects.append(Put(FeatureLabel("CAUSAL-UPDATE")))
                if parent_address == tree.root_addr:
                    break
                parent_address = parent_address.up()
            if parent_address in tree:
                effects.append(Go(Modality.relating(parent_address, host.address)))
            return _sequence(tree, context, effects)
        return None

    def instantiate(self):
        return CausalEffect(self.operation, self.relation)

    def __str__(self):
        return self.operation if self.relation == "because" else f"{self.operation}({self.relation})"
