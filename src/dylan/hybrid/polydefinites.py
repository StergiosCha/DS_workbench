"""Opt-in Classical Greek polydefinite subject fragment.

Repeated D checks agreement and shared definiteness and opens a content
requirement. Postnominal D opens adjectival refinement of the existing CN;
the adjective refines that CN before the same determiner composes again.
No token is deleted and no second individual is introduced.

This is an experimental intersective-adjective analysis, not a complete theory
of Greek polydefinites. It excludes ellipsis, contrastive readings, indefinite
doubling and modification after the finite predicate has been introduced.
"""

from dylan.action.atomic.effect import Effect
from dylan.action.atomic.semantic_effects import SemanticEffect, eliminate
from dylan.action.lexical_action import LexicalAction
from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
from dylan.formula.mltt.terms import Expr, name, app, arrow
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, TypeLabel, label_factory_create

from dylan.hybrid.features import (
    Construction, ConstructionRegistry, UnificationError, linguistic_types, nominal_description, unify,
)


def constructions():
    registry = ConstructionRegistry(linguistic_types())
    registry.add(Construction("nominal", (), nominal_description(),
                              "one referential index", "hybrid subject fragment v1"))
    registry.add(Construction("singular-subject", ("nominal",), nominal_description(number="sg", case="nom", person="3"),
                              "subject DP", "hybrid subject fragment v1"))
    registry.add(Construction("polydefinite", ("singular-subject",), nominal_description(),
                              "shared iota restrictor refined by intersective modifiers",
                              "proposed fragment; motivated by Kolliakou 2004, not a reproduction"))
    return registry

ARTICLES = {"ο": ("nom", "m"), "η": ("nom", "f"), "το": ("nom", "neut")}
ADJECTIVES = {"μεγάλος": ("big", "nom", "m"), "μεγάλη": ("big", "nom", "f"),
              "μεγάλο": ("big", "nom", "neut"), "κόκκινος": ("red", "nom", "m"),
              "κόκκινη": ("red", "nom", "f"), "κόκκινο": ("red", "nom", "neut")}
CONTENT = Requirement(FeatureLabel("POLY-CONTENT"))
ADJECTIVE = Requirement(FeatureLabel("POLY-ADJECTIVE"))


def agrees(node, case, gender):
    # The same feature kernel used in the inspection trace licenses the native
    # lexical effect; agreement is not merely an annotation after parsing.
    values = {key: next((value for value in options if node.contains(label_factory_create(f"{key}({value})"))), None)
              for key, options in {"Case": ("nom", "acc", "gen"), "Gender": ("m", "f", "neut")}.items()}
    if any(value is None for value in values.values()):
        return False
    genders = {"m": "masc", "f": "fem", "neut": "neut"}
    try:
        unify(nominal_description(case=values["Case"], gender=genders[values["Gender"]]),
              nominal_description(case=case, gender=genders[gender]), linguistic_types())
        return True
    except UnificationError:
        return False


def delete(node, label):
    if label is not None and label in node.labels:
        node.labels.remove(label)


class PolyEffect(Effect):
    def __init__(self, operation, case, gender, predicate=None, original=None):
        self.operation, self.case, self.gender = operation, case, gender
        self.predicate, self.original = predicate, original

    def exec_tuple_context(self, tree, context):
        if tree.semantic_profile.get("backend") != "classical":
            return None
        node = tree.pointed_node
        if self.operation == "content":
            # The native program still checks its own case/gender/type trigger.
            pending = node.contains(CONTENT)
            if pending:
                delete(node, CONTENT)
            result = self.original.exec(tree, context)
            return result
        if self.operation == "adjective":
            if not node.contains(ADJECTIVE):
                return None
            dp = tree.get(node.address.up("0"))
            base = node.get_formula()
            if dp is None or not agrees(dp, self.case, self.gender) or not isinstance(base, SemanticFormula) or base.term.kind != "cn":
                return None
            variable, body = base.term.args
            refined = Expr("cn", args=(variable, Expr("and", args=(body, app(name(self.predicate), variable)))))
            delete(node, node.get_formula_label())
            node.add_label(FormulaLabel(SemanticFormula(refined, "classical", base.witnesses, tree.semantic_profile)))
            delete(node, ADJECTIVE)
            node.add_label(FeatureLabel("POLY-REFINED"))
            delete(dp, dp.get_formula_label())
            delete(dp, TypeLabel(SemanticType(name("e"), "classical")))
            dp.add_label(Requirement(TypeLabel(SemanticType(name("e"), "classical"))))
            tree.pointer = dp.address
            if eliminate(tree) is None:
                return None
            SemanticEffect("semantic-thin").exec(tree, context)
            tree.pointer = next(a for a in tree if str(a) == "0")
            return tree
        # A repeated article is licensed only within an existing definite DP.
        if node.contains(CONTENT) or node.contains(ADJECTIVE):
            return None
        if node.get_required_type() == SemanticType(name("cn"), "classical"):
            parent = tree.get(node.address.up("0"))
            if parent is None:
                return None
            functor = tree.get(parent.address.down1())
            if functor is None or functor.get_type() != SemanticType(arrow(name("cn"), name("cn")), "classical"):
                return None
            hosts = [n for a, n in tree.items() if str(node.address).startswith(str(a)) and n.contains(FeatureLabel("DEFINITE"))]
            if len(hosts) != 1 or not agrees(hosts[0], self.case, self.gender):
                return None
            node.add_label(CONTENT)
            node.add_label(FeatureLabel("POLY-ARTICLE"))
            hosts[0].add_label(FeatureLabel("POLYDEFINITE"))
            return tree
        root = next(n for a, n in tree.items() if str(a) == "0")
        if str(tree.pointer) != "0" or root.contains(FeatureLabel("VERB")):
            return None
        hosts = [n for n in tree.values() if n.contains(FeatureLabel("DEFINITE")) and agrees(n, self.case, self.gender)]
        if len(hosts) != 1:
            return None
        dp = hosts[0]
        cn = tree.get(dp.address.down0())
        base = cn.get_formula() if cn else None
        if not isinstance(base, SemanticFormula) or base.term.kind != "cn" or not cn.is_complete():
            return None
        cn.add_label(ADJECTIVE)
        cn.add_label(FeatureLabel("POLY-ARTICLE"))
        dp.add_label(FeatureLabel("POLYDEFINITE"))
        tree.pointer = cn.address
        return tree

    def instantiate(self):
        return PolyEffect(self.operation, self.case, self.gender, self.predicate,
                          self.original.instantiate() if self.original else None)

    def __str__(self):
        base = "\n".join(self.original._source_lines) if self.original else ""
        return f"polydefinite-{self.operation}(case={self.case},gender={self.gender},predicate={self.predicate})\n{base}"


class PolyAction(LexicalAction):
    def __init__(self, word, effect, *, adjust=False):
        super().__init__(word, ["IF ?Ty(classical:t)", "THEN abort", "ELSE abort"],
                         f"hybrid-poly-{effect.operation}", no_left_adjustment=not adjust)
        self.effects = [effect]
        self._source_lines = [str(effect)]
        self.metadata = {"source": "hybrid-polydefinite-v1", "analysis": "shared definite CN refinement"}

    def instantiate(self):
        return PolyAction(self.word, self.effects[0].instantiate(), adjust=not self.no_left_adjustment)


def install(parser):
    if parser.semantic_profile.get("backend") != "classical":
        raise ValueError("Polydefinite experiment currently targets Classical Greek")
    if getattr(parser, "_hybrid_polydefinites", False):
        return
    parser._hybrid_polydefinites = True
    parser.semantic_profile["predicates"].setdefault("red", ["object"])
    for word, actions in list(parser.lexicon.items()):
        parser.lexicon[word] = [PolyAction(word, PolyEffect("content", "", "", original=a),
                                          adjust=a.requires_left_adjustment())
                                if a.action_type in {"common-noun", "common-adjective"} else a for a in actions]
    for word, (case, gender) in ARTICLES.items():
        parser.lexicon.setdefault(word, []).insert(0, PolyAction(word, PolyEffect("article", case, gender)))
    for word, (predicate, case, gender) in ADJECTIVES.items():
        parser.lexicon.setdefault(word, []).insert(0, PolyAction(word, PolyEffect("adjective", case, gender, predicate)))
        if not any("content" == getattr(a.effects[0], "operation", None) for a in parser.lexicon[word] if a.effects):
            original = parser.lexicon.instantiate_template(word, "common-adjective", [predicate, case, gender])
            parser.lexicon[word].append(PolyAction(word, PolyEffect("content", "", "", original=original), adjust=True))


def agreement_trace(words):
    """Independent HPSG-inspired sign constraints, with one explicit shared index."""
    registry = constructions()
    graph = registry.match("polydefinite", nominal_description(referent="nominal-0"))
    trace = []
    morphology = {**{w: (c, g) for w, (c, g) in ARTICLES.items()},
                  **{w: (c, g) for w, (_, c, g) in ADJECTIVES.items()},
                  "άνθρωπος": ("nom", "m"), "γυναίκα": ("nom", "f"), "παιδί": ("nom", "neut")}
    for index, word in enumerate(words):
        if word not in morphology:
            if trace:
                break  # Agreement is scoped to this initial nominal, not later arguments.
            continue
        case, gender = morphology[word]
        value = {"m": "masc", "f": "fem", "neut": "neut"}[gender]
        graph = unify(graph, nominal_description(gender=value, case=case, referent="nominal-0"), linguistic_types())
        trace.append({"index": index, "word": word, "graph": graph.canonical(),
                      "construction": "polydefinite", "inherits": ["nominal", "singular-subject"],
                      "meaning_implementation": "PolyEffect; shared iota with intersective CN refinement"})
    return trace
