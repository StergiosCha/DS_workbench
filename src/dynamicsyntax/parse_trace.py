"""Action-level parse trace models for facade integrations (e.g. Manim export)."""

from __future__ import annotations

from dataclasses import dataclass

from dylan.action.execution_trace import EffectStep

from dylan.tree.tree import Tree


@dataclass(frozen=True)
class ParseActionStep:
    """One action-level transition in the active parse path."""

    word: str | None
    action_name: str
    before_tree: Tree
    after_tree: Tree
    edge_id: int | None = None
    operations: tuple[EffectStep, ...] = ()
    action_kind: str = "grouped"


def action_kind(action) -> str:
    """Classify the executed program, independently of its name or vocabulary."""
    from dylan.action.lexical_action import LexicalAction
    from dylan.action.computational_action import ComputationalAction

    if isinstance(action, LexicalAction):
        return "lexical"
    if isinstance(action, ComputationalAction):
        return "computational"
    return "action"
