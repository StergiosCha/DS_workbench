"""Restrictive relative LINK construction and nominal refinement."""

from dylan.action.atomic.delete import Delete
from dylan.action.atomic.effect import Effect
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.atomic.semantic_effects import _fresh_witness, _sequence
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
from dylan.formula.mltt.terms import Expr, arrow, name
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, TypeLabel, label_factory_create


class RelativeEffect(Effect):
    def __init__(self, operation):
        self.operation = operation

    def exec_tuple_context(self, tree, context):
        backend = tree.semantic_profile.get("backend")
        if backend not in {"mltt", "classical"}:
            return None
        if self.operation == "semantic-relative":
            return self._open(tree, context, backend)
        return self._restrict(tree, context, backend)

    def _open(self, tree, context, backend):
        host = tree.pointed_node
        base, typ = host.get_formula(), host.get_type()
        cn, entity, prop = ("CN", "object", "Prop") if backend == "mltt" else ("cn", "e", "t")
        if (not isinstance(base, SemanticFormula) or not isinstance(typ, SemanticType)
                or typ != SemanticType(name(cn), backend) or not host.is_complete()):
            return None
        # Refine the complete CN below a determiner, after any prenominal
        # adjective has composed. Internal adjective arguments are also CNs.
        parent = tree.get(host.address.up("0"))
        if parent is None or parent.get_required_type() != SemanticType(name(entity), backend):
            return None
        anchor = host.address
        if backend == "mltt":
            variable = name(_fresh_witness(tree, prefix="r"))
            domain = base.term
        else:
            # The classical LINK originates at the lower entity variable in the
            # five-node DP, not the upper epsilon/tau-bound entity.
            anchor = host.address.down0()
            head = tree.get(anchor)
            value = head.get_formula() if head else None
            if (base.term.kind != "cn" or not isinstance(value, SemanticFormula)
                    or value.term.kind != "name" or value.term != base.term.args[0]):
                return None
            variable, domain = value.term, name(entity)
        if anchor.down_link() in tree:
            return None
        effects = [Put(Requirement(FeatureLabel("RESTRICT")))]
        if backend == "classical":
            effects.append(Go.parse(r"go(\/0)"))
        effects.extend([
            Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
            Put(Requirement(TypeLabel(SemanticType(name(prop), backend)))),
            Put(FeatureLabel("REL")), Put(Requirement(FeatureLabel("REL-CLOSED"))),
            Make.parse(r"make(\/*)"), Go.parse(r"go(\/*)"),
            Put(TypeLabel(SemanticType(domain, backend))),
            Put(FormulaLabel(SemanticFormula(variable, backend, theory=tree.semantic_profile))),
            Put(label_factory_create("?Ex.Tn(x)")), Put(FeatureLabel("REL-GAP")),
            Put(label_factory_create("!")), Go.parse(r"go(/\*)"),
            Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
            Put(Requirement(TypeLabel(SemanticType(arrow(name(entity), name(prop)), backend)))),
            Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
            Put(Requirement(TypeLabel(SemanticType(name(entity), backend)))),
        ])
        return _sequence(tree, context, effects)

    def _restrict(self, tree, context, backend):
        clause = tree.pointed_node
        pending = Requirement(FeatureLabel("REL-CLOSED"))
        formula, typ = clause.get_formula(), clause.get_type()
        prop = "Prop" if backend == "mltt" else "t"
        if (not str(clause.address).endswith("L") or not clause.contains(FeatureLabel("REL"))
                or not clause.contains(pending) or not isinstance(formula, SemanticFormula)
                or typ != SemanticType(name(prop), backend)):
            return None
        for addr, node in tree.items():
            if str(addr).startswith(str(clause.address)) and any(
                isinstance(label, Requirement) and not (addr == clause.address and label == pending)
                for label in node.labels
            ):
                return None
        # This fragment permits a direct subject or direct object gap. Its
        # source marker must survive MERGE at exactly one of those sites.
        sites = (clause.address.down0(), clause.address.down1().down0())
        gaps = [tree[addr] for addr in sites if addr in tree and tree[addr].contains(FeatureLabel("REL-GAP"))]
        if len(gaps) != 1:
            return None
        copied = gaps[0].get_formula()
        if not isinstance(copied, SemanticFormula) or copied.term.kind != "name":
            return None
        anchor = clause.address.up("L")
        host_addr = anchor if backend == "mltt" else anchor.up("0")
        host = tree.get(host_addr)
        base = host.get_formula() if host else None
        host_pending = Requirement(FeatureLabel("RESTRICT"))
        if not isinstance(base, SemanticFormula) or not host.contains(host_pending):
            return None
        body = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow")).term
        if backend == "mltt":
            refined = Expr("sigma", copied.term.name, (base.term, body))
        else:
            if base.term.kind != "cn" or base.term.args[0] != copied.term:
                return None
            refined = Expr("cn", args=(copied.term, Expr("and", args=(base.term.args[1], body))))
        effects = [Delete(pending), Put(FeatureLabel("REL-CLOSED")), Go.parse(r"go(/\L)")]
        if backend == "classical":
            effects.append(Go.parse(r"go(/\0)"))
        effects.extend([
            Delete(host.get_formula_label()),
            Put(FormulaLabel(SemanticFormula(refined, backend, base.witnesses, tree.semantic_profile))),
            Delete(host_pending),
        ])
        return _sequence(tree, context, effects)

    def instantiate(self):
        return RelativeEffect(self.operation)

    def __str__(self):
        return self.operation
