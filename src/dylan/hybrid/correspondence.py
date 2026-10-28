"""Declared, partial DS-to-LFG argument projection for the maintained native fragment."""

from dylan.formula.mltt.semantics import SemanticFormula
from dylan.hybrid.lfg import FStructure, Predicate

FRAMES = {"walk": ("SUBJ",), "sleep": ("SUBJ",), "like": ("SUBJ", "OBJ"),
          "love": ("SUBJ", "OBJ"), "read": ("SUBJ", "OBJ"), "meet": ("SUBJ", "OBJ"),
          "see": ("SUBJ", "OBJ"), "give": ("SUBJ", "OBJ", "OBJ2")}


def constants(term):
    if term.kind == "name":
        yield term.name
    for argument in term.args:
        yield from constants(argument)


def project(parser, *, closed=False):
    tree = parser.get_best_tuple().tree
    by_address = {str(address): node for address, node in tree.items()}
    root = by_address["0"].get_formula()
    predicates = set()
    for node in by_address.values():
        formula = node.get_formula()
        if isinstance(formula, SemanticFormula):
            predicates.update(n for n in constants(formula.term) if n in FRAMES)
    if len(predicates) != 1:
        return {"status": "unsupported_projection", "reason": "requires one declared native predicate"}
    predicate = next(iter(predicates))
    arguments = FRAMES[predicate]
    if predicate == "give":
        from dynamicsyntax._parse import _active_path_edges
        frames = {getattr(action, "action_type", "") for edge in _active_path_edges(parser)
                  for action in edge.get_actions()} & {"ditransitive", "dative-to"}
        if len(frames) != 1:
            return {"status": "unsupported_projection", "reason": "give requires one declared active lexical frame"}
        arguments = ("SUBJ", "OBJ", "OBL") if "dative-to" in frames else ("SUBJ", "OBJ", "OBJ2")
    structure = FStructure("f0", {"f0": Predicate(predicate, arguments)}, {"f0": {}})
    # Native semantic argument order is declared explicitly. This is not a
    # general discovery of grammatical functions from arbitrary meaning terms.
    slots = {"SUBJ": "00", "OBJ": "010"} if len(arguments) <= 2 else {
        "SUBJ": "00", arguments[1]: "010", arguments[2]: "0110"}
    for index, role in enumerate(arguments, 1):
        address = slots[role]
        node = by_address.get(address)
        formula = node.get_formula() if node else None
        if not isinstance(formula, SemanticFormula):
            continue
        target = f"f{index}"
        structure.predicates[target] = Predicate(str(formula), ())
        structure.functions["f0"][role] = target
        structure.morphology[target] = {
            str(label).split("(", 1)[0]: str(label).split("(", 1)[1].rstrip(")")
            for label in node.labels if str(label).startswith(("Case(", "Gender(", "Number(", "Person("))}
        structure.mappings.append({"ds_address": address, "f_node": target, "function": role,
                                   "semantic_value": str(formula)})
    return {"status": "projected", "structure": structure.to_dict(), "checks": structure.check(closed=closed),
            "root_meaning": str(root) if root else None,
            "contract": "declared native argument-position projection; partial, not a framework-equivalence theorem"}
