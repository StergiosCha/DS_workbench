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
_failures: ContextVar[list | None] = ContextVar("ds_effect_failures", default=None)
_lexical_rule: ContextVar[dict | None] = ContextVar("ds_failure_rule", default=None)


@contextmanager
def capture_failures():
    """Bounded diagnostics of failed experimental effects, separate from replay."""
    failures = []
    token = _failures.set(failures)
    try:
        yield failures
    finally:
        _failures.reset(token)


@contextmanager
def failure_rule(action):
    if _failures.get() is None:
        yield
        return
    experimental = (action.action_type or "").startswith("experimental:")
    token = _lexical_rule.set(
        {"rule_id": action.metadata.get("rule_id", action.action_type), "surface": action.word}
        if experimental else None
    )
    try:
        yield
    finally:
        _lexical_rule.reset(token)


def _failure_state(effect, tree):
    if _failures.get() is None or _lexical_rule.get() is None:
        return None
    operation = str(effect)
    if operation == "abort" or type(effect).__name__ == "IfThenElse":
        return None
    node = tree.pointed_node
    expected = {
        "semantic-pp": "Requires an existing predicate of type A → Prop (Classical: A → t) AND its formula. A CN or an unfilled ?Ty predicate slot cannot host this operation.",
        "semantic-nominal-pp": "Requires a complete CN directly below an unfinished determiner phrase, no existing LINK on that head, and a predicate declared [object, object].",
        "go": "The requested destination must already exist. Moving the pointer does not construct a type or formula.",
    }.get(operation.split("(")[0], "The action could not execute at this position; inspect its conditions, types and destination.")
    return {**_lexical_rule.get(), "operation": operation, "pointer": str(tree.pointer),
            "actual_type": str(node.get_type()) if node.get_type() else None,
            "required_type": str(node.get_required_type()) if node.get_required_type() else None,
            "formula": str(node.get_formula()) if node.get_formula() else None,
            "message": expected}


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
    failure = _failure_state(effect, tree)
    if trace is None:
        result = call(tree, context)
        if result is None and failure is not None:
            failures = _failures.get()
            if len(failures) < 24 and failure not in failures:
                failures.append(failure)
        return result
    # Tree.clone intentionally shares labels. Historical operation snapshots
    # must also freeze formula/label metavariables before the next rule resets.
    before = deepcopy(tree)
    start = len(trace.steps)
    operation = str(effect)
    result = call(tree, context)
    if result is None:
        del trace.steps[start:]
        if failure is not None:
            failures = _failures.get()
            if len(failures) < 24 and failure not in failures:
                failures.append(failure)
    elif len(trace.steps) == start:
        trace.steps.append(EffectStep(operation, before, deepcopy(result), trace.conditions))
    return result
