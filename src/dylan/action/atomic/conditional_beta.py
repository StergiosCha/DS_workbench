"""Bounded Classical situation conditionals, after Gregoromichelaki (2011).

The lexical effect instantiates the tree in (8.73)–(8.76). Ordinary typed
application constructs the restrictor and tau term. LINK evaluation copies
that term, and ordinary clause elimination performs choice evaluation.
This beta provides the fixed situation-position route only.
"""

from dylan.action.atomic.effect import Effect
from dylan.action.atomic.delete import Delete
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.atomic.semantic_effects import _fresh_witness, _sequence
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
from dylan.formula.mltt.terms import Expr, arrow, name
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, SharedFormulaLabel, TypeLabel


BETA_GRAMMAR = "2026-english-conditionals-beta-classical"


def _type(term):
    return SemanticType(term, "classical")


class ConditionalBetaEffect(Effect):
    def __init__(self, operation):
        self.operation = operation

    def exec_tuple_context(self, tree, context):
        if (tree.semantic_profile.get("backend") != "classical"
                or tree.semantic_profile.get("conditional_beta") != "fixed-situation-v1"):
            return None
        node = tree.pointed_node
        es, cns, prop = name("es"), name("cns"), name("t")

        def formula(term):
            return SemanticFormula(term, "classical", (), tree.semantic_profile)

        if self.operation == "conditional-beta-open":
            # One conditional, attached to the matrix situation. The antecedent
            # has a fixed free situation variable, so cannot start another if.
            if (node.address != tree.root_addr.down0()
                    or node.get_required_type() != _type(es)
                    or node.get_formula() is not None
                    or node.address.down_link() in tree):
                return None
            situation = _fresh_witness(tree, prefix="s")
            # cn(s, P(s)) is the inherited variable/restrictor pair. Its type in
            # this sorted grammar is cns, and the binder explicitly returns es.
            restrictor = Expr("lam", "R", (prop, Expr("cn", args=(name(situation), name("R")))))
            binder = Expr("lam", "P", (cns, Expr("tau", "u", (es,
                Expr("predication", args=(name("P"), name("u")))))))
            return _sequence(tree, context, [
                Put(Requirement(FeatureLabel("SITUATION-SHARED"))),
                Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
                Put(FeatureLabel("CONDITIONAL-RESTRICTOR")), Put(Requirement(TypeLabel(_type(es)))),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(TypeLabel(_type(arrow(cns, es)))), Put(FormulaLabel(formula(binder))),
                Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                Put(Requirement(TypeLabel(_type(cns)))),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(TypeLabel(_type(arrow(prop, cns)))), Put(FormulaLabel(formula(restrictor))),
                Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                Put(Requirement(TypeLabel(_type(prop)))),
                Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                Put(TypeLabel(_type(es))), Put(FormulaLabel(formula(name(situation)))),
                Go.parse(r"go(/\0)"),
            ])

        if self.operation == "conditional-beta-link":
            if (not node.contains(FeatureLabel("CONDITIONAL-RESTRICTOR"))
                    or node.address != tree.root_addr.down0().down_link()
                    or any(not child.is_complete() for address, child in tree.items()
                           if str(address).startswith(str(node.address)))):
                return None
            term = node.get_formula()
            host = tree[node.address.up()]
            pending = Requirement(FeatureLabel("SITUATION-SHARED"))
            if (node.get_type() != _type(es) or not isinstance(term, SemanticFormula)
                    or term.term.kind != "tau" or term.term.args[0] != es
                    or not host.contains(pending) or host.get_formula() is not None):
                return None
            # The same term is retained on both sides of LINK. A concrete
            # SharedFo requirement is then discharged by ordinary thinning.
            return _sequence(tree, context, [
                Go.parse(r"go(/\L)"), Put(TypeLabel(_type(es))),
                Put(FormulaLabel(term.clone())), Delete(pending),
                Put(Requirement(SharedFormulaLabel(term.clone()))),
            ])
        return None

    def instantiate(self):
        return ConditionalBetaEffect(self.operation)

    def __str__(self):
        return self.operation
