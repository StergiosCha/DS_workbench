"""Nominal PP restriction via a LINK, before determiner composition.

The head and the PP complement remain separate individuals. The LINK denotes
a relation between them; its locally closed meaning refines the original CN.
"""

from dylan.action.atomic.delete import Delete
from dylan.action.atomic.effect import Effect
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.atomic.semantic_effects import _fresh_witness, _sequence
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
from dylan.formula.mltt.terms import Expr, app, arrow, name
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, TypeLabel


class NominalPP(Effect):
    def __init__(self, predicate=None):
        self.predicate = predicate

    def exec_tuple_context(self, tree, context):
        backend = tree.semantic_profile.get("backend")
        if backend not in {"mltt", "classical"}:
            return None
        return self._open(tree, context, backend) if self.predicate else self._close(tree, context, backend)

    def _open(self, tree, context, backend):
        host = tree.pointed_node
        base = host.get_formula()
        cn, entity, prop = ("CN", "object", "Prop") if backend == "mltt" else ("cn", "e", "t")
        parent = tree.get(host.address.up("0"))
        if (not isinstance(base, SemanticFormula)
                or host.get_type() != SemanticType(name(cn), backend)
                or not host.is_complete() or parent is None
                or parent.get_required_type() != SemanticType(name(entity), backend)
                or tree.semantic_profile.get("predicates", {}).get(self.predicate) != ["object", "object"]):
            return None
        anchor = host.address
        if backend == "mltt":
            variable, domain = name(_fresh_witness(tree, prefix="n")), base.term
        else:
            anchor = host.address.down0()
            head = tree.get(anchor)
            value = head.get_formula() if head else None
            if (base.term.kind != "cn" or not isinstance(value, SemanticFormula)
                    or value.term.kind != "name" or value.term != base.term.args[0]):
                return None
            variable, domain = value.term, name(entity)
        # Keep previous restrictions inspectable. Stacking on the same head is
        # outside this first fragment; nested PPs on different DPs are allowed.
        if anchor.down_link() in tree:
            return None
        relation = Expr("lam", "y", (name(entity), Expr("lam", "x", (
            name(entity), app(app(name(self.predicate), name("x")), name("y"))))))
        predicate_type = arrow(name(entity), name(prop))
        effects = [Put(Requirement(FeatureLabel("NOMINAL-PP")))]
        if backend == "classical":
            effects.append(Go.parse(r"go(\/0)"))
        effects += [
            Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
            Put(FeatureLabel("NOMINAL-PP")),
            Put(Requirement(FeatureLabel("NOMINAL-PP-CLOSED"))),
            Put(Requirement(TypeLabel(SemanticType(name(prop), backend)))),
            Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
            Put(TypeLabel(SemanticType(domain, backend))),
            Put(FormulaLabel(SemanticFormula(variable, backend, theory=tree.semantic_profile))),
            Go.parse(r"go(/\0)"), Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
            Put(Requirement(TypeLabel(SemanticType(predicate_type, backend)))),
            Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
            Put(TypeLabel(SemanticType(arrow(name(entity), predicate_type), backend))),
            Put(FormulaLabel(SemanticFormula(relation, backend, theory=tree.semantic_profile))),
            Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
            Put(Requirement(TypeLabel(SemanticType(name(entity), backend)))),
        ]
        return _sequence(tree, context, effects)

    def _close(self, tree, context, backend):
        clause = tree.pointed_node
        pending = Requirement(FeatureLabel("NOMINAL-PP-CLOSED"))
        formula = clause.get_formula()
        if (not str(clause.address).endswith("L")
                or not clause.contains(FeatureLabel("NOMINAL-PP")) or not clause.contains(pending)
                or clause.get_type() != SemanticType(name("Prop" if backend == "mltt" else "t"), backend)
                or not isinstance(formula, SemanticFormula)):
            return None
        for addr, node in tree.items():
            if str(addr).startswith(str(clause.address)) and any(
                isinstance(label, Requirement) and not (addr == clause.address and label == pending)
                for label in node.labels
            ):
                return None
        head = tree.get(clause.address.down0())
        copied = head.get_formula() if head else None
        anchor = clause.address.up("L")
        host = tree.get(anchor if backend == "mltt" else anchor.up("0"))
        base = host.get_formula() if host else None
        host_pending = Requirement(FeatureLabel("NOMINAL-PP"))
        if (not isinstance(base, SemanticFormula) or not isinstance(copied, SemanticFormula)
                or copied.term.kind != "name" or not host.contains(host_pending)):
            return None
        body = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow")).term
        if backend == "mltt":
            refined = Expr("sigma", copied.term.name, (base.term, body))
        else:
            if base.term.kind != "cn" or base.term.args[0] != copied.term:
                return None
            refined = Expr("cn", args=(copied.term, Expr("and", args=(base.term.args[1], body))))
        effects = [Delete(pending), Put(FeatureLabel("NOMINAL-PP-CLOSED")), Go.parse(r"go(/\L)")]
        if backend == "classical":
            effects.append(Go.parse(r"go(/\0)"))
        effects += [Delete(host.get_formula_label()),
                    Put(FormulaLabel(SemanticFormula(refined, backend, base.witnesses, tree.semantic_profile))),
                    Delete(host_pending)]
        return _sequence(tree, context, effects)

    def instantiate(self):
        return NominalPP(self.predicate)

    def __str__(self):
        return f"semantic-nominal-pp({self.predicate})" if self.predicate else "semantic-nominal-pp-close"
