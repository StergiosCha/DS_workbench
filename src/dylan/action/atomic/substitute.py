"""Resolve a restricted formula placeholder against typed discourse referents."""

from dylan.action.atomic.effect import Effect
from dylan.action.atomic.delete import Delete
from dylan.action.atomic.put import Put
from dylan.action.execution_trace import execute_effect
from dylan.formula.formula_metavariable import FormulaMetavariable
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType, subtype
from dylan.formula.mltt.terms import name, parse_expr
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, TypeLabel, UnaryPredicateLabel, label_factory_create


def local_root(tree):
    address = tree.pointer
    while address != tree.root_addr:
        node = tree.get(address)
        if str(address).endswith(("L", "B")) or (node and node.contains(FeatureLabel("CLAUSE"))):
            break
        address = address.up()
    return address


def local_references(tree):
    root = local_root(tree)
    values = set()
    for address, node in tree.items():
        if address == tree.pointer or not str(address).startswith(str(root)):
            continue
        suffix = str(address)[len(str(root)):]
        if any(edge in suffix for edge in "LB"):
            continue
        ancestor = address
        inside_clause = False
        while ancestor != root:
            parent = tree.get(ancestor)
            if parent and parent.contains(FeatureLabel("CLAUSE")):
                inside_clause = True
                break
            ancestor = ancestor.up()
        formula = node.get_formula()
        if not inside_clause and isinstance(formula, SemanticFormula) and formula.term.kind == "name":
            values.add(formula.term.name)
    return values


class Substitute(Effect):
    @staticmethod
    def candidates(tree, context):
        node = tree.pointed_node
        formula = node.get_formula()
        if not isinstance(formula, FormulaMetavariable) or context is None:
            return []
        restriction = formula.restriction
        reference_class = tree.semantic_profile.get("reference_classes", {}).get(restriction)
        restricted_person = (reference_class or {}).get("person", {"Sp'": 1, "Hr'": 2}.get(restriction))
        features = {label.predicate.lower(): label.arg for label in node.labels
                    if isinstance(label, UnaryPredicateLabel)}
        person_feature = features.get("person")
        if person_feature is not None and person_feature not in {"1", "2", "3"}:
            return []
        labelled_person = int(person_feature) if person_feature else None
        if restricted_person and labelled_person and restricted_person != labelled_person:
            return []
        person = restricted_person or labelled_person or 3
        for key in ("gender", "number"):
            expected = (reference_class or {}).get(key)
            if expected and features.get(key, expected) != expected:
                return []
            if expected:
                features[key] = expected
        used = local_references(tree)
        required = node.get_type() or node.get_required_type()
        result = []
        for referent in context.referents:
            if referent.symbol in used or referent.person != person:
                continue
            if reference_class is None and restriction not in {None, "x", "Sp'", "Hr'"} and referent.symbol != restriction:
                continue
            if any(features.get(k) and value and features[k] != value
                   for k, value in (("gender", referent.gender), ("number", referent.number))):
                continue
            if isinstance(required, SemanticType) and required.backend == "mltt":
                if not subtype(parse_expr(referent.sort), required.term, tree.semantic_profile):
                    continue
            result.append(referent)
        default = (reference_class or {}).get("default") or ("speaker" if person == 1 else "hearer" if person == 2 else (
            "pro" if node.address == local_root(tree).down0() else
            "theme" if features.get("gender") == "neut" else
            "her" if features.get("gender") == "fem" else
            "them" if features.get("number") == "pl" else "him"
        ))
        # Explicit discourse reference precedes a role-based grammar fallback.
        return sorted(result, key=lambda r: (r.source == "grammar", r.symbol != default if r.source == "grammar" else False))

    def exec_tuple_context(self, tree, context):
        node = tree.pointed_node
        formula = node.get_formula()
        if not isinstance(formula, FormulaMetavariable) or not node.address.is_fixed():
            return None
        candidates = self.candidates(tree, context)
        if not candidates:
            if context is not None:
                context.last_reference_failure = {
                    "kind": "missing_context", "node": str(tree.pointer),
                    "message": f"No compatible non-local referent for {formula}.",
                }
            return None
        referent = candidates[0]
        backend = tree.semantic_profile.get("backend")
        if backend not in {"mltt", "classical"}:
            return None
        tree.semantic_profile = {
            **tree.semantic_profile,
            "constants": {**tree.semantic_profile.get("constants", {}), referent.symbol: referent.sort},
        }
        resolved = SemanticFormula(name(referent.symbol), backend, theory=tree.semantic_profile)
        effects = [Delete(node.get_formula_label()), Put(FormulaLabel(resolved)),
                   Delete(label_factory_create("?Ex.Fo(x)"))]
        if node.get_type_label() is not None:
            effects.append(Delete(node.get_type_label()))
        typ = SemanticType(parse_expr(referent.sort) if backend == "mltt" else name("e"), backend)
        effects.append(Put(TypeLabel(typ)))
        for effect in effects:
            tree = execute_effect(effect, tree, context, tuple_context=True)
            if tree is None:
                return None
        return tree

    def instantiate(self):
        return Substitute()

    def __str__(self):
        return "substitute"
