"""Named-head supplements: LINK/copy/MERGE and propositional conjunction.

Cann, Kempson & Marten (2005), §3.1, especially (3.6), (3.9), (3.13).
The native constructive interpretation is an explicit workbench adaptation.
See docs/design/nonrestrictive-relatives.md for the deliberately bounded remit.
"""
from dylan.action.atomic.delete import Delete
from dylan.action.atomic.effect import Effect
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.atomic.semantic_effects import _sequence
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
from dylan.formula.mltt.terms import Expr, arrow, name
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, TypeLabel, label_factory_create
from dylan.tree.node_address import NodeAddress


def pending(feature):
    return Requirement(FeatureLabel(feature))


class NonrestrictiveEffect(Effect):
    def __init__(self, operation):
        self.operation = operation

    def instantiate(self):
        return NonrestrictiveEffect(self.operation)

    def __str__(self):
        return self.operation

    def exec_tuple_context(self, tree, context):
        backend = tree.semantic_profile.get("backend")
        if backend not in {"classical", "mltt"}:
            return None
        entity, prop = ("object", "Prop") if backend == "mltt" else ("e", "t")
        node = tree.pointed_node
        root = tree[NodeAddress("0")]
        formula, typ = node.get_formula(), node.get_type()
        if self.operation == "nonrestrictive-open":
            # Main-clause named subject/direct object only. No projection out
            # of attitudes, quantifier restriction, or inferred referent choice.
            if (str(node.address) not in {"00", "010"} or not node.is_complete()
                    or not isinstance(formula, SemanticFormula) or formula.witnesses
                    or formula.term.kind != "name" or not isinstance(typ, SemanticType)
                    or formula.term.name not in tree.semantic_profile.get("constants", {})
                    or node.address.down0() in tree or node.address.down1() in tree
                    or node.address.down_link() in tree
                    or root.contains(FeatureLabel("APPOS-SEALED"))
                    or root.contains(FeatureLabel("POLAR-QUESTION"))
                    or typ.term.kind != "name" or typ.term.name in {"Prop", "t", "CN", "cn", "Content"}):
                return None
            moves = [Go.parse(r"go(/\0)")]
            if str(node.address) == "010":
                moves.append(Go.parse(r"go(/\1)"))
            back = [Go.parse(r"go(\/0)")] if str(node.address) == "00" else [Go.parse(r"go(\/1)"), Go.parse(r"go(\/0)")]
            return _sequence(tree, context, moves + [Put(pending("APPOS-EVAL"))] + back + [
                Put(pending("APPOS-RETURN")), Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
                Put(FeatureLabel("REL")), Put(FeatureLabel("APPOS")),
                Put(pending("APPOS-PRONOUN")), Put(pending("APPOS-CLOSED")),
                Put(Requirement(TypeLabel(SemanticType(name(prop), backend)))),
            ])
        if self.operation == "nonrestrictive-pronoun":
            if not node.contains(pending("APPOS-PRONOUN")):
                return None
            head = tree[node.address.up("L")]
            return _sequence(tree, context, [
                Delete(pending("APPOS-PRONOUN")),
                Make.parse(r"make(\/*)"), Go.parse(r"go(\/*)"),
                Put(head.get_type_label()), Put(head.get_formula_label()),
                Put(label_factory_create("?Ex.Tn(x)")), Put(FeatureLabel("REL-GAP")),
                Put(label_factory_create("!")), Go.parse(r"go(/\*)"),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(Requirement(TypeLabel(SemanticType(arrow(name(entity), name(prop)), backend)))),
                Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                Put(Requirement(TypeLabel(SemanticType(name(entity), backend)))),
            ])
        if self.operation in {"nonrestrictive-close", "nonrestrictive-end"}:
            if (not node.contains(pending("APPOS-CLOSED"))
                    or not isinstance(formula, SemanticFormula)
                    or typ != SemanticType(name(prop), backend)):
                return None
            if self.operation == "nonrestrictive-end" and str(node.address) != "010L":
                return None
            for address, child in tree.items():
                if str(address).startswith(str(node.address)) and any(
                        isinstance(label, Requirement) and not (address == node.address and label == pending("APPOS-CLOSED"))
                        for label in child.labels):
                    return None
            sites = [node.address.down0(), node.address.down1().down0()]
            gaps = [tree[a] for a in sites if a in tree and tree[a].contains(FeatureLabel("REL-GAP"))]
            head = tree[node.address.up("L")]
            if len(gaps) != 1 or gaps[0].get_formula() != head.get_formula():
                return None
            closed = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow"))
            return _sequence(tree, context, [
                Delete(node.get_formula_label()), Put(FormulaLabel(closed)),
                Delete(pending("APPOS-CLOSED")), Put(FeatureLabel("APPOS-CLOSED")),
                Go.parse(r"go(/\L)"), Delete(pending("APPOS-RETURN")),
            ])
        if self.operation == "nonrestrictive-evaluate":
            if (str(node.address) != "0" or not node.contains(pending("APPOS-EVAL"))
                    or typ != SemanticType(name(prop), backend) or not isinstance(formula, SemanticFormula)):
                return None
            if any(isinstance(label, Requirement) and not (a == node.address and label == pending("APPOS-EVAL"))
                   for a, child in tree.items() for label in child.labels):
                return None
            supplements = [tree[NodeAddress(a)] for a in ("00L", "010L")
                           if NodeAddress(a) in tree and tree[NodeAddress(a)].contains(FeatureLabel("APPOS-CLOSED"))]
            if not supplements:
                return None
            # Each proposition closes its own witnesses. The copied head is
            # already identified and remains exactly the same term in both.
            meaning = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow")).term
            for supplement in supplements:
                meaning = Expr("and", args=(meaning, supplement.get_formula().term))
            return _sequence(tree, context, [
                Delete(node.get_formula_label()),
                Put(FormulaLabel(SemanticFormula(meaning, backend, (), tree.semantic_profile))),
                Delete(pending("APPOS-EVAL")), Put(FeatureLabel("APPOS-SEALED")),
            ])
        return None
