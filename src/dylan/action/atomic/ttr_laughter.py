"""Local backward laughter: Maraev et al. (2026), §4.2, Fig. 7.

The beta resolves the immediately pointed, complete record. Forward/distant
resolution and grounding are separate work; laughable does not mean funny.
"""

import re

from dylan.action.atomic.effect import Effect
from dylan.action.atomic.go import Go
from dylan.action.atomic.make import Make
from dylan.action.atomic.put import Put
from dylan.action.atomic.semantic_effects import _sequence
from dylan.formula.ttr_field import TTRField
from dylan.formula.ttr_record_type import TTRRecordType
from dylan.tree.label.labels import FeatureLabel, FormulaLabel, Requirement, TypeLabel
from dylan.type.dstype import DSType

BETA_GRAMMAR = "2026-english-laughter-beta-ttr"


class TTRLaughter(Effect):
    def __str__(self):
        return "ttr-laughter-backward"

    def instantiate(self):
        return self

    def exec_tuple_context(self, tree, context):
        node = tree.pointed_node
        if (tree.semantic_profile or str(node.get_type()) not in {"e", "t"}
                or node.address.down_link() in tree
                or not all(n.is_complete() for a, n in tree.items()
                           if str(a).startswith(str(node.address)))):
            return None
        formula = node.get_formula()
        if not isinstance(formula, TTRRecordType):
            return None
        head = formula.head()
        if (head is None or head.manifest_type is None
                or str(head.ds_type) not in {"e", "es"}):
            return None
        # Keep the same referent/event, rather than freshening the antecedent.
        # Copy its record so all dependencies remain bound on the LINK too.
        linked = formula.clone()
        used = " ".join(str(n.get_formula()) for n in tree.values())
        index = 0
        while re.search(rf"\blaughter{index}\b", used):
            index += 1
        field = TTRField.parse(f"laughter{index}==laughable({head.manifest_type}):t")
        if field is None:
            raise ValueError("Could not build the laughter record field")
        linked.add(field)
        return _sequence(tree, context, [
            Put(Requirement(FeatureLabel("eval"))),
            Make.parse(r"make(\/L)"), Go.parse(r"go(\/L)"),
            Put(TypeLabel(DSType.parse(str(head.ds_type)))),
            Put(FeatureLabel("LAUGHTER-BACKWARD")),
            Put(FormulaLabel(linked)), Go.parse(r"go(/\L)"),
        ])
