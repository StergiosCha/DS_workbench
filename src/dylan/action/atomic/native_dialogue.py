"""Typed subject binding and immediate polar-question answer resolution.

These actions interpret a bounded native grammar fragment. They do not infer
speaker beliefs, agreement with the answer, or general elliptical material.
"""

from dylan.action.atomic.effect import Effect
from dylan.action.atomic.delete import Delete
from dylan.action.atomic.put import Put
from dylan.action.atomic.substitute import local_root
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType, coerce, is_gq
from dylan.formula.mltt.terms import Expr, app, arrow, name
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, TypeLabel


def participant_symbol(participant):
    return ("speaker" if participant == "Dylan" else "you" if participant == "you" else
            "speaker_" + "".join(c if c.isascii() and c.isalnum() else f"_x{ord(c):x}_"
                                 for c in participant))


def previous_question(context):
    """Only the immediately preceding tree on the selected DAG path qualifies."""
    from dylan.dag.groundable_edge import AxiomEdge

    dag = context.get_dag()
    current = dag.get_current_tuple()
    while (edge := dag.get_parent_edge(current)) is not None:
        if isinstance(edge, AxiomEdge):
            prior = edge.src.tree
            if prior.is_complete() and prior.get_root_node().contains(FeatureLabel("POLAR-QUESTION")):
                return prior
            return None
        current = edge.src
    return None


class NativeDialogueEffect(Effect):
    def __init__(self, operation, value):
        allowed = {"semantic-reflexive": {"myself", "yourself", "himself", "herself", "itself", "themselves"},
                   "semantic-answer": {"yes", "no"}}
        if value not in allowed.get(operation, ()):
            raise ValueError("Unsupported native dialogue action")
        self.operation, self.value = operation, value

    def __str__(self):
        return f"{self.operation}({self.value})"

    def instantiate(self):
        return self

    def exec_tuple_context(self, tree, context):
        if context is None or tree.semantic_profile.get("backend") not in {"classical", "mltt"}:
            return None
        if self.operation == "semantic-answer":
            return self.answer(tree, context)
        return self.reflexive(tree, context)

    def fail(self, context, message, kind="reflexive_binding"):
        context.last_reference_failure = {"kind": kind, "message": message}
        return None

    def reflexive(self, tree, context):
        from dylan.action.atomic.semantic_effects import _sequence

        root = local_root(tree)
        node = tree.pointed_node
        if node.address != root.down1().down0():
            return self.fail(context, "This reflexive requires the local clause's subject and final object slot.")
        subject, verb = tree.get(root.down0()), tree.get(root.down1().down1())
        if subject is None or verb is None:
            return None
        sf, st, vt = subject.get_formula(), subject.get_type(), verb.get_type()
        if not isinstance(sf, SemanticFormula) or not all(isinstance(t, SemanticType) for t in (st, vt)):
            return None
        backend = st.backend
        prop = name("Prop" if backend == "mltt" else "t")
        if (vt.term.kind != "arrow" or vt.term.args[1].kind != "arrow"
                or vt.term.args[1].args[1] != prop):
            return None
        speaker = context.get_current_speaker()
        addressee = context.get_current_addressee() or "you"
        if not speaker:
            return None
        participant = speaker if self.value == "myself" else addressee
        if self.value in {"myself", "yourself"}:
            if sf.term != name(participant_symbol(participant)):
                return self.fail(context, f"“{self.value}” must denote this word's {'speaker' if self.value == 'myself' else 'addressee'} and bind to the local subject.")
        elif sf.term in {name(participant_symbol(speaker)), name(participant_symbol(addressee))}:
            return self.fail(context, "A third-person reflexive cannot replace the current speaker/addressee reflexive here.")

        # Check attested features; unknown gender is not invented from a name.
        features = tree.semantic_profile.get("referents", {}).get(sf.term.name, {})
        gender = features.get("gender") or {"him": "masc", "her": "fem", "it": "neut"}.get(sf.term.name)
        expected = {"himself": "masc", "herself": "fem", "itself": "neut"}.get(self.value)
        labels = {str(label) for label in subject.labels}
        if self.value not in {"myself", "yourself"} and labels.intersection({"Person(1)", "Person(2)"}):
            return self.fail(context, "This third-person reflexive requires a third-person local subject.")
        number = "pl" if "Number(pl)" in labels else "sg" if "Number(sg)" in labels else features.get("number")
        if any(str(addr).startswith(str(subject.address)) and n.contains(FeatureLabel("DISTRIBUTIVE-PLURAL"))
               for addr, n in tree.items()):
            number = "pl"
        domain = st.term.args[0].args[0] if is_gq(st.term, prop.name) else st.term
        nominal = domain
        while nominal.kind == "sigma":
            nominal = nominal.args[0]
        gender = gender or {"man": "masc", "woman": "fem"}.get(nominal.name)
        if not gender and sf.term.kind in {"eps", "tau"}:
            # Classical choice terms retain their overt nominal restrictor.
            restrictor = sf.term.args[1]
            if restrictor.kind == "app" and restrictor.args[0].kind == "name":
                gender = {"man": "masc", "woman": "fem"}.get(restrictor.args[0].name)
        if expected and gender and expected != gender:
            return self.fail(context, "The reflexive's gender conflicts with the known local subject.")
        if number == "pl" and self.value != "themselves":
            return self.fail(context, "A singular reflexive cannot bind this plural subject in the current fragment.")

        try:
            obj = coerce(name("x"), domain, vt.term.args[0], tree.semantic_profile)
            subj = coerce(name("x"), domain, vt.term.args[1].args[0], tree.semantic_profile)
        except TypeError:
            return self.fail(context, "The local subject cannot satisfy both typed arguments of this verb.")
        term = Expr("lam", "R", (vt.term, Expr("lam", "x", (domain, app(app(name("R"), obj), subj)))))
        typ = SemanticType(arrow(vt.term, arrow(domain, prop)), backend)
        binding = {"node": str(node.address), "subject_node": str(subject.address), "word": self.value,
                   "speaker": speaker, "antecedent": str(sf), "subject_type": str(st),
                   "antecedent_label": participant if self.value in {"myself", "yourself"} else str(sf)}
        tree.semantic_profile = {**tree.semantic_profile, "reflexive_bindings": [
            *tree.semantic_profile.get("reflexive_bindings", []), binding]}
        return _sequence(tree, context, [Delete(node.get_type_requirement()), Put(FeatureLabel("REFLEXIVE")),
            Put(TypeLabel(typ)), Put(FormulaLabel(SemanticFormula(term, backend, (), tree.semantic_profile)))])

    def answer(self, tree, context):
        from dylan.action.atomic.semantic_effects import SemanticEffect, _sequence

        prior = previous_question(context)
        if prior is None:
            return self.fail(context, "Yes/No needs an immediately preceding complete polar question in this dialogue.", "missing_context")
        node = tree.pointed_node
        if node.address != tree.root_addr or node.get_formula() is not None:
            return None
        formula, typ = prior.get_root_node().get_formula(), prior.get_root_node().get_type()
        if (not isinstance(formula, SemanticFormula) or not isinstance(typ, SemanticType)
                or formula.backend != tree.semantic_profile.get("backend")):
            return None
        formula = formula.close_witnesses()
        profile = dict(tree.semantic_profile)
        for key in ("constants", "predicates", "subtyping", "modifiers", "context_assumptions"):
            profile[key] = {**profile.get(key, {}), **prior.semantic_profile.get(key, {})}
        profile["answer_context"] = {"polarity": self.value, "question_content": str(formula),
                                     "speaker": context.get_current_speaker()}
        tree.semantic_profile = profile
        effects = [Put(FeatureLabel("SHORT-ANSWER")), Put(TypeLabel(typ)),
                   Put(FormulaLabel(SemanticFormula(formula.term, formula.backend, (), profile)))]
        if self.value == "no":
            effects.append(SemanticEffect("semantic-negate"))
        return _sequence(tree, context, effects)
