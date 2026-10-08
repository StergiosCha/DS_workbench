"""Opt-in observation of executed effects, including nested rule/macro bodies.

The ordinary executor remains authoritative. This observer records its leaf
effects and discards failed branches; it never implements a second interpreter.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from dylan.tree.tree import Tree


@dataclass(frozen=True)
class EffectStep:
    operation: str
    before_tree: Tree
    after_tree: Tree
    conditions: tuple[dict[str, Any], ...] = ()


@dataclass
class EffectTrace:
    steps: list[EffectStep] = field(default_factory=list)
    conditions: tuple[dict[str, Any], ...] = ()


_active: ContextVar[EffectTrace | None] = ContextVar("ds_effect_trace", default=None)


@contextmanager
def capture_effects():
    trace = EffectTrace()
    token = _active.set(trace)
    try:
        yield trace.steps
    finally:
        _active.reset(token)


def tracing() -> bool:
    return _active.get() is not None


def trace_checkpoint() -> int:
    trace = _active.get()
    return len(trace.steps) if trace else 0


def discard_effects_since(checkpoint: int) -> None:
    trace = _active.get()
    if trace is not None:
        del trace.steps[checkpoint:]


@contextmanager
def trace_branch(checks: list[dict[str, Any]], branch: str):
    trace = _active.get()
    if trace is None:
        yield
        return
    previous = trace.conditions
    trace.conditions = previous + ({"branch": branch, "checks": checks},)
    try:
        yield
    finally:
        trace.conditions = previous


def execute_effect(effect, tree: Tree, context: Any, *, tuple_context: bool = False):
    """Execute normally; when observed, record leaves with frozen decorations."""
    call = effect.exec_tuple_context if tuple_context else effect.exec
    trace = _active.get()
    if trace is None:
        return call(tree, context)
    # Tree.clone intentionally shares labels. Historical operation snapshots
    # must also freeze formula/label metavariables before the next rule resets.
    before = deepcopy(tree)
    start = len(trace.steps)
    operation = str(effect)
    result = call(tree, context)
    if result is None:
        del trace.steps[start:]
    elif len(trace.steps) == start:
        trace.steps.append(EffectStep(operation, before, deepcopy(result), trace.conditions))
    return result
