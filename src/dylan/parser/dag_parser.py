"""Shared parser infrastructure (Java `DAGParser`)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TextIO

from loguru import logger as loguru_logger

from dylan.action.action import Action
from dylan.action.grammar import Grammar
from dylan.action.lexicon import Lexicon, NotebookMultilineText
from dylan.action.speech_act_inference_grammar import SpeechActInferenceGrammar
from dylan.context.context import Context
from dylan.dag.dag_tuple import DAGTuple
from dylan.dag.groundable_edge import GroundableEdge
from dylan.dag.word_level_context_dag import WordLevelContextDAG
from dylan.formula.formula import Formula
from dylan.tree.tree import Tree
from dylan.parser.parse_stats import ParseStats

if TYPE_CHECKING:
    from dylan.dag.uttered_word import UtteredWord

logger = logging.getLogger(__name__)

_MAX_NONOPTIONAL_ADJUST_PASSES = 10_000
_MAX_COMPLETION_STEPS = 10_000


class DAGParser:
    """Loads grammars and coordinates `Context` + DAG state (partial port)."""

    def __init__(
        self,
        lexicon: Lexicon,
        grammar: Grammar,
        sa_grammar: SpeechActInferenceGrammar | None = None,
        *,
        max_nonoptional_adjust_passes: int = _MAX_NONOPTIONAL_ADJUST_PASSES,
        max_completion_steps: int = _MAX_COMPLETION_STEPS,
    ) -> None:
        self.max_nonoptional_adjust_passes = max_nonoptional_adjust_passes
        self.max_completion_steps = max_completion_steps
        self.last_cap_hit: str | None = None
        self._stats = ParseStats()
        self.lexicon = lexicon
        self.decision_client = None
        self.nonoptional_grammar = Grammar()
        self.optional_grammar = Grammar()
        self.completion_grammar = Grammar()
        self._separate_grammars(grammar)
        self.sa_grammar = sa_grammar or SpeechActInferenceGrammar(Path("."))
        self.context: Context[DAGTuple, GroundableEdge] | None = None
        self.ready = True

    @property
    def stats(self) -> ParseStats:
        return self.get_state().stats if self.context is not None else self._stats

    def _reset_stats(self) -> None:
        self._stats = ParseStats()
        if self.context is not None:
            self.get_state().stats = ParseStats(tuples=1)

    def _separate_grammars(self, grammar: Grammar) -> None:
        """Partition computational actions like Java `DAGParser.separateGrammars`."""
        self._declared_completion = any(a.completion for a in grammar.values())
        for a in grammar.values():
            nm = a.name.lower()
            legacy_completion = nm in {"completion", "merge"} or nm.startswith("anticipation")
            if a.completion or (not self._declared_completion and legacy_completion):
                self.completion_grammar[a.name] = a
            if a.is_always_good():
                self.nonoptional_grammar[a.name] = a
            else:
                self.optional_grammar[a.name] = a

    @classmethod
    def from_resource_dir(cls, resource_dir: str | Path, *, strict: bool = False) -> DAGParser:
        """Load lexicon + grammars from a directory (Java `DAGParser(String)`).

        With *strict*, grammar/lexicon load-time validation problems (duplicate
        computational rule names, lexicon rows naming missing templates, column
        arity mismatches) raise ``ValueError`` instead of a loguru warning.
        """
        p = Path(resource_dir)
        return cls(
            Lexicon(p, strict=strict), Grammar(p, strict=strict), SpeechActInferenceGrammar(p)
        )

    def get_vocab(
        self,
        groupby: Literal["category", "alpha"] = "category",
        *,
        stream: TextIO | None = None,
        backend: Literal["plain", "rich"] = "plain",
        max_cell_width: int | None = 120,
    ) -> NotebookMultilineText:
        """Show loaded lexical entries via :meth:`~dylan.action.lexicon.Lexicon.get_vocab`.

        Uses this parser's lexicon only; computational grammar rules live on ``Grammar``
        objects (`nonoptional_grammar`, etc.), not in this listing.
        """
        return self.lexicon.get_vocab(
            groupby,
            stream=stream,
            backend=backend,
            max_cell_width=max_cell_width,
        )

    def get_state(self) -> WordLevelContextDAG:
        """Return the active word-level DAG."""
        if self.context is None:
            raise RuntimeError("context not initialised")
        return self.context.get_dag()

    def get_context(self) -> Context[DAGTuple, GroundableEdge]:
        """Return the active parser context."""
        if self.context is None:
            raise RuntimeError("context not initialised")
        return self.context

    def apply_actions(self, t: Tree, actions: list[Action]) -> Tree | None:
        """Sequentially apply `actions` to a clone of `t` (Java `applyActions`)."""
        cur: Tree | None = t.clone()
        for a in actions:
            assert cur is not None
            cur = a.exec(cur, self.context)
            if cur is None:
                return None
        return cur

    def adjust_with_non_optional_grammar(
        self,
        init_pair: tuple[list[Action], Tree],
    ) -> tuple[list[Action], Tree]:
        """Apply ``*`` computational actions until fixpoint (Java ``adjustWithNonOptionalGrammar``)."""
        actions = list(init_pair[0])
        res = init_pair[1]
        if self.last_cap_hit is not None:
            return (actions, res)
        for _ in range(self.max_nonoptional_adjust_passes):
            progressed = False
            for ca in sorted(self.nonoptional_grammar.values(), key=lambda x: x.name):
                clone = res.clone()
                self.stats.computational_execs += 1
                nxt = ca.exec(clone, self.context)
                if nxt is not None:
                    actions.append(ca.instantiate())
                    res = nxt
                    progressed = True
                    break
            if not progressed:
                return (actions, res)
        self.last_cap_hit = "max_nonoptional_adjust_passes"
        self.stats.cap_hits.append(self.last_cap_hit)
        loguru_logger.debug(
            "cap hit: max_nonoptional_adjust_passes={}", self.max_nonoptional_adjust_passes
        )
        self._log_nonoptional_adjust_limit_exceeded()
        return (actions, res)

    def _log_nonoptional_adjust_limit_exceeded(self) -> None:
        """Emit error when the non-optional adjustment loop exceeds its pass bound."""
        logger.error(
            "adjust_with_non_optional_grammar exceeded %s passes — possible runaway rule loop",
            self.max_nonoptional_adjust_passes,
        )

    def complete_once(
        self, t: Tree, *, skip_actions: set[str] | None = None
    ) -> tuple[list[Action], Tree]:
        """Apply star grammar to fixpoint, then try one completion-grammar action (Java ``DAGParser.completeOnce``)."""
        init_actions, init_tree = self.adjust_with_non_optional_grammar(([], t.clone()))
        if init_actions or self.last_cap_hit is not None:
            return (init_actions, init_tree)
        for ca in sorted(self.completion_grammar.values(), key=lambda x: x.name):
            if skip_actions and ca.name in skip_actions:
                continue
            self.stats.computational_execs += 1
            completed = ca.exec(init_tree.clone(), self.context)
            if completed is not None:
                return (init_actions + [ca.instantiate()], completed)
        return (init_actions, init_tree)

    def complete_tree(self, res: Tree) -> tuple[list[Action], Tree]:
        """Search completion rules, returning only the successful action path.

        Keep the ordinary rule order, but revisit optional choices when a path
        stalls. For example, a subject's case requirement may need the other
        daughter completed first. Mandatory adjustments remain mandatory. If
        no path completes, retain the first stalled partial analysis.
        """
        cur_tree = res.clone()
        acc: list[Action] = []
        attempted: dict[tuple, set[str]] = {}
        choices: list[tuple[Tree, list[Action]]] = []
        partial: tuple[list[Action], Tree] | None = None
        steps = 0
        while True:
            if self.last_cap_hit is not None or cur_tree.is_complete():
                return (acc, cur_tree)
            if steps >= self.max_completion_steps:
                self.last_cap_hit = "max_completion_steps"
                self.stats.cap_hits.append(self.last_cap_hit)
                loguru_logger.debug("cap hit: max_completion_steps={}", self.max_completion_steps)
                return (acc, cur_tree)
            steps += 1
            # An anticipation/completion pair can revisit a completed LINK.
            # Try each completion rule once per unchanged state, then consider
            # its alternatives instead of traversing the same cycle forever.
            state = (
                str(cur_tree.pointer),
                tuple(
                    (str(addr), tuple(sorted(str(lab) for lab in node.labels)))
                    for addr, node in cur_tree.items()
                ),
            )
            tried = attempted.setdefault(state, set())
            cur_actions, next_tree = self.complete_once(cur_tree, skip_actions=tried)
            if not cur_actions:
                if partial is None:
                    partial = (acc, cur_tree)
                if not choices:
                    return partial
                cur_tree, acc = choices.pop()
                continue
            # Instantiated actions do not retain the always_good flag. Check
            # grammar membership instead, so mandatory rules cannot be skipped.
            if cur_actions[0].name not in self.nonoptional_grammar:
                tried.update(action.name for action in cur_actions)
                choices.append((cur_tree, acc))
            acc = acc + cur_actions
            cur_tree = next_tree

    def get_final_semantics(self) -> Formula:
        """Semantics at the current tuple after `evaluate` (Java `getFinalSemantics`)."""
        dag = self.get_state()
        sem = dag.get_current_tuple().get_semantics(self.context)
        ev = sem.evaluate()
        if not isinstance(ev, Formula):
            raise TypeError("expected Formula from evaluate()")
        return ev

    def init(self) -> None:
        """Reset parser context."""
        self.last_cap_hit = None
        if self.context is not None:
            self.context.init()
        self._reset_stats()

    def new_sentence(self) -> None:
        """Reset DAG to axiom (Java `newSentence`)."""
        self.last_cap_hit = None
        self.get_state().init()

    def complete(self, word: UtteredWord | None = None) -> DAGTuple:
        """Complete the current tree and attach a completion edge."""
        dag = self.get_state()
        actions, tree = self.complete_tree(dag.get_current_tuple().get_tree())
        if self.last_cap_hit is not None:
            return dag.get_current_tuple()
        tup = dag.get_new_tuple(tree)
        edge = dag.get_new_completion_edge(actions, word)
        edge.set_repairable(False)
        dag.add_child(tup, edge)
        return tup

    def get_state_with_n_best_tuples(self, n: int) -> list[DAGTuple]:
        """Return current tuple plus up to *n* further interpretations by stepping the parser."""
        if n < 0:
            raise ValueError("n must be non-negative")
        dag = self.get_state()
        dag.reset_to_first_tuple_after_last_word()
        result: list[DAGTuple] = [dag.get_current_tuple()]
        try:
            for _ in range(n):
                if not self.parse_goal(None):
                    break
                result.append(dag.get_current_tuple())
            return result
        finally:
            dag.reset_to_first_tuple_after_last_word()

    def get_n_best_final_semantics(self, n: int) -> list[Formula]:
        """Return final semantics from Java-style N-best tuple stepping."""
        out: list[Formula] = []
        for tup in self.get_state_with_n_best_tuples(n):
            sem = tup.get_semantics(self.context)
            ev = sem.evaluate()
            if isinstance(ev, Formula):
                out.append(ev)
        return out

    def parse(self, goal: Formula | None = None) -> bool:
        """Delegate to `parse(goal)` on concrete parser (Java `DAGParser.parse()`)."""
        return self.parse_goal(goal)

    def parse_goal(self, goal: Formula | None) -> bool:
        raise NotImplementedError

    def parse_word(self, word: UtteredWord) -> WordLevelContextDAG | None:
        raise NotImplementedError


DAGParser.separateGrammars = DAGParser._separate_grammars  # type: ignore[attr-defined]
DAGParser.fromResourceDir = DAGParser.from_resource_dir  # type: ignore[attr-defined]
DAGParser.getVocab = DAGParser.get_vocab  # type: ignore[attr-defined]
DAGParser.getState = DAGParser.get_state  # type: ignore[attr-defined]
DAGParser.getContext = DAGParser.get_context  # type: ignore[attr-defined]
DAGParser.applyActions = DAGParser.apply_actions  # type: ignore[attr-defined]
DAGParser.adjustWithNonOptionalGrammar = DAGParser.adjust_with_non_optional_grammar  # type: ignore[attr-defined]
DAGParser.completeOnce = DAGParser.complete_once  # type: ignore[attr-defined]
DAGParser.completeTree = DAGParser.complete_tree  # type: ignore[attr-defined]
DAGParser.getFinalSemantics = DAGParser.get_final_semantics  # type: ignore[attr-defined]
DAGParser.newSentence = DAGParser.new_sentence  # type: ignore[attr-defined]
DAGParser.getStateWithNBestTuples = DAGParser.get_state_with_n_best_tuples  # type: ignore[attr-defined]
DAGParser.getNBestFinalSemantics = DAGParser.get_n_best_final_semantics  # type: ignore[attr-defined]
