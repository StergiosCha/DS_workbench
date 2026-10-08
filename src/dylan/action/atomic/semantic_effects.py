"""Typed elimination and thinning for native DS semantic decorations."""

from typing import Any

from dylan.action.atomic.effect import Effect
from dylan.action.atomic.delete import Delete
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.execution_trace import execute_effect
from dylan.formula.mltt.semantics import (
    SemanticFormula,
    SemanticType,
    Witness,
    apply_semantics,
    left_consumes_predicate,
    subtype,
)
from dylan.formula.mltt.terms import Expr, name, arrow, fresh_name, app
from dylan.tree.label.labels import (
    ExistentialLabelConjunction, FeatureLabel, FormulaLabel, ModalLabel,
    TypeLabel, Requirement, SharedFormulaLabel, label_factory_create,
)
from dylan.tree.tree import Tree


def _sequence(tree, context, effects):
    for effect in effects:
        tree = execute_effect(effect, tree, context, tuple_context=True)
        if tree is None:
            return None
    return tree


def _holds_without_binding(label, tree, context):
    from dylan.action.meta.element import snapshot_meta_bindings, restore_meta_bindings

    bindings = snapshot_meta_bindings()
    try:
        return label.check_with_tuple_as_context(tree, context)
    finally:
        restore_meta_bindings(bindings)


def _composition(tree: Tree):
    """Infer the typed application; leave all decorations unchanged."""
    node = tree.pointed_node
    left, right = tree.get(node.address.down0()), tree.get(node.address.down1())
    if left is None or right is None:
        return None
    f0, f1, t0, t1 = left.get_formula(), right.get_formula(), left.get_type(), right.get_type()
    if not (
        isinstance(f0, SemanticFormula)
        and isinstance(f1, SemanticFormula)
        and isinstance(t0, SemanticType)
        and isinstance(t1, SemanticType)
    ):
        return None
    # A generalized quantifier on daughter 0 consumes the predicate on 1.
    subject_gq = left_consumes_predicate(t0, t1, reflexive=left.contains(FeatureLabel("REFLEXIVE")))
    candidates = [(f0, t0, f1, t1)] if subject_gq else [(f1, t1, f0, t0)]
    try:
        return apply_semantics(*candidates[0], tree.semantic_profile)
    except TypeError:
        return None


def _fresh_witness(tree: Tree, *, prefix: str = "p") -> str:
    """Name a witness independently of later address refinement by MERGE."""
    # Keep established fixed-address names, but encode path operators such as *.
    base = prefix + "".join(c if c.isascii() and c.isalnum() else f"_{ord(c):x}_"
                         for c in str(tree.pointer))
    used = set()

    def collect(term):
        if term.name:
            used.add(term.name)
        for arg in term.args:
            collect(arg)

    for node in tree.values():
        formula, typ = node.get_formula(), node.get_type()
        if isinstance(formula, SemanticFormula):
            collect(formula.term)
            for witness in formula.witnesses:
                used.add(witness.variable)
                collect(witness.domain)
        if isinstance(typ, SemanticType):
            collect(typ.term)
    for category in ("constants", "predicates", "modifiers", "subtyping", "sorts"):
        used.update(tree.semantic_profile.get(category, ()))
    return fresh_name(base, used)


def eliminate(tree: Tree) -> Tree | None:
    node = tree.pointed_node
    combination = _composition(tree)
    if combination is None:
        return None
    result, result_type = combination
    required = node.get_required_type()
    if result.backend == "mltt" and result.term.kind == "definite":
        # A definite contributes a contextual assumption, never a globally
        # available choice function or a newly asserted existential.
        domain = result.term.args[0]
        namespace = tree.semantic_profile.get("sentence_namespace", "")
        variable = _fresh_witness(tree, prefix=f"definite_{namespace}")
        tree.semantic_profile = {
            **tree.semantic_profile,
            "constants": {**tree.semantic_profile.get("constants", {}), variable: domain.to_source()},
            "context_assumptions": {
                **tree.semantic_profile.get("context_assumptions", {}),
                variable: f"{variable}: a contextually identified referent of type {domain}; its identification is assumed.",
            },
        }
        result_type = SemanticType(domain)
        result = SemanticFormula(name(variable), "mltt", result.witnesses, tree.semantic_profile)
    if (
        result.backend == "mltt"
        and result.term.kind == "sigma"
        and isinstance(required, SemanticType)
        and required.term == name("object")
    ):
        # The determiner constructs a dependent pair type. The NP contributes
        # its witness; argument coercion projects the first component later.
        variable = _fresh_witness(tree)
        result_type = SemanticType(result.term)
        result = SemanticFormula(
            name(variable),
            "mltt",
            result.witnesses + (Witness(variable, result.term),),
            tree.semantic_profile,
        )
    node.add_label(TypeLabel(result_type))
    node.add_label(FormulaLabel(result))
    return tree


class SemanticEffect(Effect):
    def __init__(self, operation: str, args: tuple[str, ...] = ()) -> None:
        self.operation = operation
        self.args = args

    def exec_tuple_context(self, tree: Tree, context: Any) -> Tree | None:
        if not tree.semantic_profile:
            return None
        node = tree.pointed_node
        if self.operation == "semantic-vp-coordinate-types":
            arg, fun = tree.get(node.address.down0()), tree.get(node.address.down1())
            if arg is None or fun is None or not arg.is_complete():
                return None
            at, ft, formula = arg.get_type(), fun.get_type(), fun.get_formula()
            if not all(isinstance(t, SemanticType) for t in (at, ft)) or not isinstance(formula, SemanticFormula):
                return None
            old, new = ft.term.args[0], at.term
            if old.kind != "arrow" or new.kind != "arrow" or old.args[1] != new.args[1]:
                return None
            common = new if subtype(new.args[0], old.args[0], tree.semantic_profile) else old if subtype(old.args[0], new.args[0], tree.semantic_profile) else None
            if common is None:
                return None
            term = Expr("lam", "Q", (new, Expr("lam", "x", (common.args[0], formula.term.args[1].args[1]))))
            effects = [Delete(FeatureLabel("VP-COORD")), Go.parse(r"go(\/1)"), Delete(TypeLabel(ft)), Delete(FormulaLabel(formula)),
                       Put(TypeLabel(SemanticType(arrow(new, common), ft.backend))),
                       Put(FormulaLabel(SemanticFormula(term, ft.backend, formula.witnesses, tree.semantic_profile))), Go.parse(r"go(/\1)")]
            return _sequence(tree, context, effects)
        if self.operation == "semantic-coordinate":
            typ, formula = node.get_type(), node.get_formula()
            if (not isinstance(typ, SemanticType) or not isinstance(formula, SemanticFormula)
                    or typ.term != name("Prop" if typ.backend == "mltt" else "t")
                    or not tree.is_complete()):
                return None
            # Close witnesses within the first conjunct. They must not leak into
            # the second conjunct as globally chosen existential individuals.
            first = formula.close_witnesses().term
            function = SemanticFormula(Expr("lam", "q", (typ.term, Expr("and", args=(first, name("q"))))), typ.backend, (), tree.semantic_profile)
            moves, anchor = [], node
            while anchor.address.down_link() in tree:
                anchor = tree[anchor.address.down_link()]
                if not anchor.is_complete():
                    return None
                moves.append(Go.parse(r"go(\/L)"))
            return _sequence(tree, context, moves + [
                Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
                Put(FeatureLabel("COORDINATED")), Put(Requirement(TypeLabel(typ))),
                Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                Put(TypeLabel(SemanticType(arrow(typ.term, typ.term), typ.backend))),
                Put(FormulaLabel(function)), Go.parse(r"go(/\1)"),
                Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                Put(Requirement(TypeLabel(typ))),
            ])
        if self.operation == "semantic-coordinate-close":
            if not node.address.address.endswith("L") or not node.is_complete():
                return None
            formula = node.get_formula()
            if not isinstance(formula, SemanticFormula):
                return None
            formula = formula.close_witnesses()
            effects = [Delete(FeatureLabel("COORDINATED"))]
            while node.address.address.endswith("L"):
                node = tree[node.address.up()]
                effects.append(Go.parse(r"go(/\L)"))
                effects.extend(Delete(lab) for lab in node.labels if isinstance(lab, FormulaLabel))
                effects.append(Put(FormulaLabel(formula)))
            return _sequence(tree, context, effects)
        if self.operation in {"semantic-speaker", "semantic-pronoun"}:
            role, sort = self.args if self.args else ("speaker", "human")
            participant = context.get_current_speaker() if context is not None else None
            backend = tree.semantic_profile.get("backend")
            required = node.get_required_type()
            if (not participant or backend not in {"mltt", "classical"}
                    or not isinstance(required, SemanticType)
                    or required.term != name("object" if backend == "mltt" else "e")
                    or node.get_formula() is not None):
                return None
            # Preserve distinct speaker identities across turns. Encode punctuation
            # (including underscores) so participant names cannot collide or inject
            # formula text. The ordinary single-sentence context uses "speaker".
            if role == "hearer":
                participant = context.get_current_addressee() or "you"
            from dylan.action.atomic.native_dialogue import participant_symbol
            symbol = participant_symbol(participant)
            assumptions = dict(tree.semantic_profile.get("context_assumptions", {}))
            if role not in {"speaker", "hearer"}:
                from dylan.action.atomic.substitute import local_references
                gender = {"him": "masc", "her": "fem", "it": "neut"}.get(role)
                used = local_references(tree)
                candidates = [r for r in context.referents if r.source != "grammar"
                              and r.person == 3 and r.symbol not in used
                              and gender and r.gender == gender]
                symbol = candidates[0].symbol if candidates else role
                if not candidates:
                    assumptions[symbol] = f"{symbol}: a supplied discourse referent; its contextual identification is assumed."
                else:
                    assumption_id = f"pronoun_{tree.semantic_profile.get('sentence_namespace', '')}_{node.address}_{role}"
                    assumptions[assumption_id] = f"{role} interpreted as {symbol}: the most recent compatible named antecedent; this is a contextual resolution assumption."
            person = 1 if role in {"speaker", "we"} else 2 if role == "hearer" else 3
            tree.semantic_profile = {
                **tree.semantic_profile,
                "constants": {**tree.semantic_profile.get("constants", {}), symbol: sort},
                "context_assumptions": assumptions,
            }
            return _sequence(tree, context, [
                Put(TypeLabel(SemanticType(name(sort if backend == "mltt" else "e"), backend))),
                Put(FormulaLabel(SemanticFormula(name(symbol), backend, (), tree.semantic_profile))),
                Put(label_factory_create(f"Person({person})")),
                Put(label_factory_create(f"Number({'pl' if role in {'we', 'them'} else 'sg'})")),
            ])
        if self.operation in {"semantic-negate", "semantic-modal"}:
            formula, typ = node.get_formula(), node.get_type()
            if (
                not isinstance(formula, SemanticFormula)
                or not isinstance(typ, SemanticType)
                or typ.term != name("Prop" if typ.backend == "mltt" else "t")
            ):
                return None
            if tree.semantic_profile.get("scope", "narrow") == "narrow":
                formula = formula.close_witnesses()
            if self.operation == "semantic-modal" and (len(self.args) != 1 or self.args[0] not in tree.semantic_profile.get("modifiers", {})):
                return None
            negated = SemanticFormula(
                Expr("neg", args=(formula.term,)) if self.operation == "semantic-negate" else app(name(self.args[0]), formula.term), formula.backend,
                formula.witnesses, tree.semantic_profile,
            )
            return _sequence(tree, context, [
                Delete(node.get_formula_label()), Put(FormulaLabel(negated)),
            ])
        if self.operation == "semantic-close-complement":
            pending = Requirement(FeatureLabel("CLOSED"))
            formula, actual = node.get_formula(), node.get_type()
            if (
                not node.contains(FeatureLabel("CLAUSE"))
                or not node.contains(pending)
                or not isinstance(formula, SemanticFormula)
                or not isinstance(actual, SemanticType)
                or actual.term != name("Prop" if actual.backend == "mltt" else "t")
            ):
                return None
            # Every descendant must be complete; the boundary's own closure
            # requirement is the only one this operation is allowed to satisfy.
            for addr, descendant in tree.items():
                if not str(addr).startswith(str(node.address)):
                    continue
                if any(
                    isinstance(lab, Requirement) and not (addr == node.address and lab == pending)
                    for lab in descendant.labels
                ):
                    return None
            closed = formula.close_witnesses(tree.semantic_profile.get("scope", "narrow"))
            closed.theory = tree.semantic_profile
            content_type = (
                SemanticType(name("Content"), "mltt") if actual.backend == "mltt" else actual
            )
            return _sequence(
                tree,
                context,
                [
                    Delete(node.get_formula_label()),
                    Delete(node.get_type_label()),
                    Put(TypeLabel(content_type)),
                    Put(FormulaLabel(closed)),
                    Delete(pending),
                    Put(FeatureLabel("CLOSED")),
                ],
            )
        if self.operation == "semantic-thin":
            actual = node.get_type()
            if not isinstance(actual, SemanticType):
                return None
            for label in list(node.labels):
                if (isinstance(label, Requirement)
                        and isinstance(label.inner, ExistentialLabelConjunction)
                        and len(label.inner.parts) == 1
                        and isinstance(label.inner.parts[0], FormulaLabel)
                        and isinstance(node.get_formula(), SemanticFormula)
                        and _holds_without_binding(label.inner, tree, context)):
                    return execute_effect(Delete(label), tree, context, tuple_context=True)
                if (isinstance(label, Requirement) and isinstance(label.inner, (ModalLabel, SharedFormulaLabel))
                        and node.address.is_fixed()):
                    if _holds_without_binding(label.inner, tree, context):
                        return execute_effect(Delete(label), tree, context, tuple_context=True)
                if (
                    isinstance(label, Requirement)
                    and isinstance(label.inner, TypeLabel)
                    and isinstance(label.inner.type, SemanticType)
                    and label.inner.type.accepts_requirement(actual)
                ):
                    return execute_effect(Delete(label), tree, context, tuple_context=True)
            return None
        if self.operation == "semantic-project-parent-type":
            # An output filter can await the type of the very application whose
            # formula awaits this filter. Infer its type from the typed daughters;
            # an explicit formula requirement keeps the parent incomplete.
            if not node.address.is_fixed() or not any(
                isinstance(lab, Requirement) and isinstance(lab.inner, ModalLabel)
                for lab in node.labels
            ):
                return None
            parent_address = node.address.up()
            parent = tree.get(parent_address)
            if parent is None or parent.get_type() is not None:
                return None
            saved_pointer = tree.pointer
            try:
                tree.pointer = parent_address
                combination = _composition(tree)
            finally:
                tree.pointer = saved_pointer
            if combination is None:
                return None
            _, inferred_type = combination
            required = parent.get_required_type()
            if required is not None and not required.accepts_requirement(inferred_type):
                return None
            child_edge = str(node.address)[len(str(parent_address)):]
            return _sequence(tree, context, [
                Go.parse(r"go(/\)"), Put(TypeLabel(inferred_type)),
                Put(label_factory_create("?Ex.Fo(x)")), Go.parse(f"go(\\/{child_edge})"),
            ])
        if self.operation in {"semantic-adverb", "semantic-pp", "semantic-comparison", "semantic-vp-coordinate"}:
            # A postfix VP modifier is attached by LINK. Its domain is
            # instantiated from the actual predicate, not a nominal guess.
            vp = node
            if vp is None or not isinstance(vp.get_type(), SemanticType):
                return None
            parent = tree.get(vp.address.up())
            if parent and any(parent.contains(FeatureLabel(marker)) for marker in ("CAUSAL-HOST", "CAUSAL-SEALED", "APPOS-SEALED")):
                # This original VP no longer denotes the whole clause. A later
                # modifier must attach inside a content clause; rebuilding the
                # old VP would silently erase the completed causal LINK.
                return None
            typ, formula = vp.get_type(), vp.get_formula()
            proposition = name("Prop" if typ.backend == "mltt" else "t")
            if (typ.term.kind != "arrow" or typ.term.args[1] != proposition
                    or not isinstance(formula, SemanticFormula)):
                return None
            is_comparison = self.operation == "semantic-comparison"
            is_pp = self.operation in {"semantic-pp", "semantic-comparison"}
            is_coord = self.operation == "semantic-vp-coordinate"
            if not is_coord and len(self.args) != 1:
                return None
            domains = tree.semantic_profile.get("predicates", {}).get(self.args[0], []) if self.args else []
            if is_pp:
                if len(domains) != 2 or domains[1] != "Prop":
                    return None
                if is_comparison and domains[0] != "CN":
                    return None
                domain = name(("CN" if typ.backend == "mltt" else "cn") if is_comparison
                              else domains[0] if typ.backend == "mltt" else "e")
            elif not is_coord and self.args[0] not in tree.semantic_profile.get("modifiers", {}):
                return None
            # A sequence of modifiers extends the completed LINK chain. Existing
            # nodes retain the previous derivations; no subtree is overwritten.
            moves = []
            anchor = vp
            while anchor.address.down_link() in tree:
                anchor = tree[anchor.address.down_link()]
                if not anchor.is_complete() or anchor.get_type() != typ:
                    return None
                moves.append(Go.parse(r"go(\/L)"))
            if is_coord:
                body = Expr("and", args=(app(formula.term, name("x")), app(name("Q"), name("x"))))
                term = Expr("lam", "Q", (typ.term, Expr("lam", "x", (typ.term.args[0], body))))
                return _sequence(tree, context, moves + [
                    Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
                    Put(FeatureLabel("VP-COORD")),
                    Put(Requirement(TypeLabel(SemanticType(arrow(name("object" if typ.backend == "mltt" else "e"), proposition), typ.backend)))),
                    Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                    Put(TypeLabel(SemanticType(arrow(typ.term, typ.term), typ.backend))),
                    Put(FormulaLabel(SemanticFormula(term, typ.backend, formula.witnesses, tree.semantic_profile))),
                    Go.parse(r"go(/\1)"), Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                    Put(Requirement(TypeLabel(SemanticType(arrow(name("object" if typ.backend == "mltt" else "e"), proposition), typ.backend)))),
                ])
            body = app(name(self.args[0]), name("z")) if is_pp else name(self.args[0])
            body = app(body, app(name("P"), name("x")))
            term = Expr("lam", "P", (typ.term, Expr("lam", "x", (typ.term.args[0], body))))
            modifier_type = arrow(typ.term, typ.term)
            if is_pp:
                term = Expr("lam", "z", (domain, term))
            modifier = SemanticFormula(term, typ.backend, (), tree.semantic_profile)
            effects = moves + [
                    Make.parse(r"make(\/L)"),
                    Go.parse(r"go(\/L)"),
                    Put(Requirement(TypeLabel(typ))),
                    Make.parse(r"make(\/0)"),
                    Go.parse(r"go(\/0)"),
                    Put(TypeLabel(typ)),
                    Put(FormulaLabel(formula)),
                    Go.parse(r"go(/\0)"),
                    Make.parse(r"make(\/1)"),
                    Go.parse(r"go(\/1)"),
            ]
            if is_pp:
                # The PP complement is a real DP subtree, composed with the
                # lexical preposition before its result modifies the copied VP.
                effects += [
                    Put(FeatureLabel("PP")),
                    Put(Requirement(TypeLabel(SemanticType(modifier_type, typ.backend)))),
                    Make.parse(r"make(\/1)"), Go.parse(r"go(\/1)"),
                    Put(TypeLabel(SemanticType(arrow(domain, modifier_type), typ.backend))),
                    Put(FormulaLabel(modifier)), Go.parse(r"go(/\1)"),
                    Make.parse(r"make(\/0)"), Go.parse(r"go(\/0)"),
                    Put(Requirement(TypeLabel(SemanticType(domain if is_comparison else name("object" if typ.backend == "mltt" else "e"), typ.backend)))),
                ]
                if is_comparison:
                    effects.append(Put(FeatureLabel("COMPARISON")))
            else:
                effects += [
                    Put(TypeLabel(SemanticType(modifier_type, typ.backend))),
                    Put(FormulaLabel(modifier)),
                    Go.parse(r"go(/\1)"),
                ]
            return _sequence(tree, context, effects)
        if self.operation == "semantic-link":
            if not node.address.address.endswith("L") or not node.is_complete():
                return None
            vp = tree[node.address.up()]
            formula = node.get_formula()
            if not isinstance(formula, SemanticFormula):
                return None
            effects = [Go.parse(r"go(/\L)")]
            effects.extend(Delete(lab) for lab in vp.labels if isinstance(lab, FormulaLabel))
            effects.append(Put(FormulaLabel(formula)))
            if node.get_type() != vp.get_type():
                effects.extend(Delete(lab) for lab in vp.labels if isinstance(lab, TypeLabel))
                effects.append(Put(TypeLabel(node.get_type())))
            # A later modifier can be LINKed from an earlier completed modifier.
            # Propagate its value through that chain before recomputing the clause.
            while vp.address.address.endswith("L"):
                vp = tree[vp.address.up()]
                effects.append(Go.parse(r"go(/\L)"))
                effects.extend(Delete(lab) for lab in vp.labels if isinstance(lab, FormulaLabel))
                effects.append(Put(FormulaLabel(formula)))
            # Reopen compositional ancestors. For an embedded VP this includes
            # its Content boundary, whose witnesses must be closed again locally.
            clause_addr = vp.address.up("1")
            if clause_addr is None:
                return None
            parent_addr = vp.address.up()
            while parent_addr in tree:
                parent = tree[parent_addr]
                actual = parent.get_type()
                effects.append(Go.parse(r"go(/\)"))
                if isinstance(actual, SemanticType):
                    effects.extend(
                        Delete(lab) for lab in parent.labels
                        if isinstance(lab, (TypeLabel, FormulaLabel))
                    )
                    if parent.contains(FeatureLabel("CLOSED")):
                        effects.extend([
                            Delete(FeatureLabel("CLOSED")),
                            Put(Requirement(FeatureLabel("CLOSED"))),
                        ])
                        actual = SemanticType(
                            name("Prop" if actual.backend == "mltt" else "t"), actual.backend
                        )
                    if parent.contains(FeatureLabel("NEG")) and not parent.contains(FeatureLabel("CAUSAL-HOST")):
                        effects.extend([
                            Delete(FeatureLabel("NEG")),
                            Put(Requirement(FeatureLabel("NEG"))),
                        ])
                    effects.append(Put(Requirement(TypeLabel(actual))))
                    if parent.contains(FeatureLabel("CAUSAL-LINK")):
                        effects.append(Put(FeatureLabel("CAUSAL-UPDATE")))
                # A relative is a separate LINKed proposition. Updating its
                # predicate must not erase the nominal head across inverse LINK.
                if parent_addr == tree.root_addr or parent.contains(FeatureLabel("REL")):
                    break
                parent_addr = parent_addr.up()
            from dylan.tree.modality import Modality

            effects.append(Go(Modality.relating(parent_addr, clause_addr)))
            return _sequence(tree, context, effects)
        return None

    def instantiate(self) -> Effect:
        return SemanticEffect(self.operation, self.args)

    def __str__(self) -> str:
        return self.operation + ("(" + ",".join(self.args) + ")" if self.args else "")
