"""Dialogue context with DAG state (partial Java `Context`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, TypeVar

from dylan.action.speech_act_inference_grammar import SpeechActInferenceGrammar
from dylan.dag.dag_edge import DAGEdge
from dylan.dag.dag_tuple import DAGTuple
from dylan.dag.word_level_context_dag import WordLevelContextDAG
from dylan.context.referent import Referent

T = TypeVar("T", bound=DAGTuple)
E = TypeVar("E", bound=DAGEdge)


class Context(Generic[T, E]):
    """Holds participants, floor state, and the word-level DAG (Eshghi et al. 2015)."""

    def __init__(
        self,
        dag: WordLevelContextDAG,
        sa_grammar: SpeechActInferenceGrammar | None = None,
        *participants: str,
    ) -> None:
        """Wire a fresh DAG, participants, and optional SA grammar."""
        self._dag: WordLevelContextDAG = dag
        dag.set_context(self)
        self.my_name = participants[0] if participants else "Dylan"
        self.who_has_floor: str | None = None
        self._participants: set[str] = set(participants) if participants else {self.my_name}
        self.sa_inf_grammar = sa_grammar or SpeechActInferenceGrammar(Path("."))
        self._dialogue_words: list[Any] = []
        self._grounded_content: list[DAGTuple] = []
        self._seed_referents: list[Referent] = []
        self.last_reference_failure: dict | None = None

    def seed_referents(self, profile: dict) -> None:
        """Seed declared constants; optional metadata supplies gender and number."""
        metadata = profile.get("referents", {})
        self._seed_referents = [r for r in self._seed_referents if r.source != "grammar"]
        for symbol, sort in profile.get("constants", {}).items():
            features = metadata.get(symbol, {})
            self._seed_referents.append(Referent(
                symbol, sort, features.get("person", {"speaker": 1, "hearer": 2}.get(symbol, 3)),
                features.get("gender"), features.get("number"), "grammar",
            ))
        self.last_reference_failure = None

    @property
    def referents(self) -> list[Referent]:
        """Newest active-path names first, then the explicit context and grammar seeds.

        Deriving names from the active path makes failed alternatives and repairs
        disappear automatically; speculative actions never mutate discourse state.
        """
        from dylan.action.lexical_action import LexicalAction
        from dylan.formula.mltt.semantics import SemanticFormula, SemanticType
        from dylan.tree.label.labels import UnaryPredicateLabel

        result, seen = [], set()
        current = self._dag.get_current_tuple()
        while current is not None:
            edge = self._dag.get_parent_edge(current)
            if edge is None:
                break
            if any(isinstance(a, LexicalAction) and a.action_type.startswith("proper")
                   for a in edge.get_actions()):
                for address, node in edge.dst.tree.items():
                    formula, typ = node.get_formula(), node.get_type()
                    previous = edge.src.tree.get(address)
                    if (isinstance(formula, SemanticFormula) and formula.term.kind == "name"
                            and isinstance(typ, SemanticType)
                            and (previous is None or previous.get_formula() != formula)):
                        symbol = formula.term.name
                        if symbol not in seen:
                            known = next((r for r in self._seed_referents if r.symbol == symbol), None)
                            features = {lab.predicate.lower(): lab.arg for lab in node.labels
                                        if isinstance(lab, UnaryPredicateLabel)}
                            gender = features.get("gender", known.gender if known else None)
                            gender = {"m": "masc", "f": "fem", "n": "neut"}.get(gender, gender)
                            result.append(Referent(
                                symbol, known.sort if known else str(typ.term),
                                int(features.get("person", known.person if known else 3)),
                                gender, features.get("number", known.number if known else None),
                            ))
                            seen.add(symbol)
            current = edge.src
        return result + [r for r in self._seed_referents if r.symbol not in seen]

    @referents.setter
    def referents(self, values: list[Referent]) -> None:
        self._seed_referents = list(values)

    def get_name(self) -> str:
        """Return the default agent name for this context."""
        return self.my_name

    def get_dag(self) -> WordLevelContextDAG:
        """Return the word-level context DAG."""
        return self._dag

    def set_dag(self, dag: WordLevelContextDAG) -> None:
        """Replace the active DAG and attach this context to it."""
        self._dag = dag
        dag.set_context(self)

    def get_participants(self) -> set[str]:
        """Return dialogue participant ids."""
        return set(self._participants)

    def get_current_addressee(self) -> str | None:
        """Addressee of the word currently being parsed (Java ``Context.getCurrentAddressee``)."""
        stack = self._dag.word_stack_ref()
        if not stack:
            return None
        return stack[-1].addressee

    def get_current_tuple(self) -> DAGTuple:
        """Return the tuple under the DAG cursor."""
        return self._dag.get_current_tuple()

    def floor_is_open(self) -> bool:
        """Return True when no participant holds the floor."""
        return self.who_has_floor is None

    def open_floor(self) -> None:
        """Mark the floor as unassigned."""
        self.who_has_floor = None

    def ground_to_root(self) -> None:
        """Ground dialogue state to root (Java ``Context.groundToRoot``)."""
        self._dag.ground_to_root()
        self._grounded_content.append(self._dag.get_current_tuple())

    def get_speech_act_grammar(self) -> SpeechActInferenceGrammar:
        """Return the loaded speech-act inference grammar (Java ``getSAGrammar``)."""
        return self.sa_inf_grammar

    def set_who_has_floor(self, speaker: str) -> None:
        """Assign the conversational floor to `speaker`."""
        self.who_has_floor = speaker

    def get_who_has_floor(self) -> str | None:
        """Return the participant currently holding the floor."""
        return self.who_has_floor

    def set_repair_processing(self, repairing: bool) -> None:
        """Enable or disable repair handling on the DAG."""
        self._dag.set_repair_processing(repairing)

    def repair_initiated(self) -> bool:
        """Return True when the top stack token is the repair-init marker."""
        return self._dag.repair_initiated()

    def append_word(self, w: Any) -> None:
        """Record a word in dialogue history (Java `Context.appendWord`)."""
        self._dialogue_words.append(w)

    def get_dialogue_history(self) -> list[Any]:
        """Return recorded dialogue words."""
        return list(self._dialogue_words)

    def get_grounded_content(self) -> list[DAGTuple]:
        """Return tuples grounded so far."""
        return list(self._grounded_content)

    def get_cautiously_optimistic_grounded_content(self) -> list[DAGTuple]:
        """Return grounded content using Java's cautious optimistic API name."""
        return self.get_grounded_content()

    def get_current_speaker(self) -> str | None:
        """Return speaker of the top word on the parser stack."""
        stack = self._dag.word_stack_ref()
        if not stack:
            return None
        return stack[-1].speaker

    def init(self) -> None:
        """Reset DAG and variable pools (simplified vs Java `Context.init`)."""
        self._dag = WordLevelContextDAG()
        self._dag.set_context(self)
        self._dialogue_words.clear()
        self._grounded_content.clear()
        self._seed_referents.clear()
        self.last_reference_failure = None
        self.who_has_floor = None

    def init_participants(self, participants: list[str]) -> None:
        """Reset participant set and rebuild an empty DAG."""
        self._participants = set(participants)
        self.my_name = participants[0] if participants else "Dylan"
        self.init()


Context.getName = Context.get_name  # type: ignore[attr-defined]
Context.getDAG = Context.get_dag  # type: ignore[attr-defined]
Context.getDag = Context.get_dag  # type: ignore[attr-defined]
Context.setDAG = Context.set_dag  # type: ignore[attr-defined]
Context.setDag = Context.set_dag  # type: ignore[attr-defined]
Context.getParticipants = Context.get_participants  # type: ignore[attr-defined]
Context.getCurrentAddressee = Context.get_current_addressee  # type: ignore[attr-defined]
Context.getCurrentTuple = Context.get_current_tuple  # type: ignore[attr-defined]
Context.floorIsOpen = Context.floor_is_open  # type: ignore[attr-defined]
Context.openFloor = Context.open_floor  # type: ignore[attr-defined]
Context.groundToRoot = Context.ground_to_root  # type: ignore[attr-defined]
Context.getSAGrammar = Context.get_speech_act_grammar  # type: ignore[attr-defined]
Context.setWhoHasFloor = Context.set_who_has_floor  # type: ignore[attr-defined]
Context.getWhoHasFloor = Context.get_who_has_floor  # type: ignore[attr-defined]
Context.setRepairProcessing = Context.set_repair_processing  # type: ignore[attr-defined]
Context.repairInitiated = Context.repair_initiated  # type: ignore[attr-defined]
Context.appendWord = Context.append_word  # type: ignore[attr-defined]
Context.getDialogueHistory = Context.get_dialogue_history  # type: ignore[attr-defined]
Context.getGroundedContent = Context.get_grounded_content  # type: ignore[attr-defined]
Context.getCautiouslyOptimisticGroundedContent = Context.get_cautiously_optimistic_grounded_content  # type: ignore[attr-defined]
Context.getCurrentSpeaker = Context.get_current_speaker  # type: ignore[attr-defined]
Context.initParticipants = Context.init_participants  # type: ignore[attr-defined]
