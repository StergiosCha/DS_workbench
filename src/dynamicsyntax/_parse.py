"""High-level :func:`parse` using bundled grammars and ``dylan`` parser core."""

from __future__ import annotations

from pathlib import Path
from typing import overload

from dylan.formula.formula import Formula
from dylan.dag.dag_tuple import DAGTuple
from dylan.dag.groundable_edge import GroundableEdge
from dylan.nlp.types import DEFAULT_SPEAKER, utterance_from_text
from dylan.parser.interactive_context_parser import (
    InteractiveContextParser,
    LogLevel,
    LogOutput,
)
from dylan.tree.tree import Tree

from dynamicsyntax._session import resolved_grammar_path
from dynamicsyntax.parse_trace import ParseActionStep, action_kind
from dynamicsyntax.parse_result import ParseResult


def _active_path_edges(parser: InteractiveContextParser) -> list[GroundableEdge]:
    """Return active DAG edges from root to the parser's current tuple."""
    dag = parser.get_state()
    cur = dag.get_current_tuple()
    edges: list[GroundableEdge] = []
    while True:
        edge = dag.get_parent_edge(cur)
        parent = dag.get_parent(cur)
        if edge is None or parent is None:
            break
        edges.append(edge)
        cur = parent
    edges.reverse()
    return edges


def _steps_from_edge(
    parser: InteractiveContextParser, edge: GroundableEdge, *, operations: bool = False
) -> list[ParseActionStep]:
    """Replay one active edge into action-level tree transitions."""
    stack = parser.get_state().word_stack_ref()
    saved = list(stack)
    if edge.word is not None:
        stack.append(edge.word)
    try:
        return _replay_steps_from_edge(parser, edge, operations=operations)
    finally:
        stack[:] = saved


def _replay_steps_from_edge(
    parser: InteractiveContextParser, edge: GroundableEdge, *, operations: bool = False
) -> list[ParseActionStep]:
    """Replay with the edge's original speaker/addressee, including after completion."""
    if not isinstance(edge.src, DAGTuple) or not isinstance(edge.dst, DAGTuple):
        return []
    word = edge.word.word if edge.word is not None else None
    actions = edge.get_actions()
    if not actions:
        return [
            ParseActionStep(
                word=word,
                action_name="(no action)",
                before_tree=edge.src.get_tree().clone(),
                after_tree=edge.dst.get_tree().clone(),
                edge_id=edge.edge_id,
            ),
        ]
    steps: list[ParseActionStep] = []
    cur = edge.src.get_tree().clone()
    for action in actions:
        before = cur.clone()
        from contextlib import nullcontext
        from dylan.action.execution_trace import capture_effects

        with capture_effects() if operations else nullcontext([]) as effects:
            after = parser.apply_actions(cur, [action])
        if after is None:
            return [
                ParseActionStep(
                    word=word,
                    action_name="; ".join(a.get_name() for a in actions),
                    before_tree=edge.src.get_tree().clone(),
                    after_tree=edge.dst.get_tree().clone(),
                    edge_id=edge.edge_id,
                ),
            ]
        steps.append(
            ParseActionStep(
                word=word,
                action_name=action.get_name(),
                before_tree=before,
                after_tree=after.clone(),
                edge_id=edge.edge_id,
                operations=tuple(effects),
                action_kind=action_kind(action),
            ),
        )
        cur = after
    return steps


def _complete_native_parse(parser: InteractiveContextParser) -> Tree:
    """Select the completion edge so result semantics and action playback agree."""
    completed = parser.complete()
    if parser.last_cap_hit is None:
        dag = parser.get_state()
        edge = dag.get_parent_edge(completed)
        assert edge is not None
        edge.traverse(dag)
        dag.stats.traversed += 1
        dag.update_last_n()
    return parser.get_best_tuple().get_tree()


def _run_parse_core(
    parser: InteractiveContextParser,
    stripped: str,
    *,
    speaker: str,
    trace: bool,
) -> ParseResult:
    """Run ``init`` / ``new_sentence`` / parse on *parser* and return a :class:`ParseResult`."""
    parser.init()
    parser.new_sentence()
    utt = utterance_from_text(speaker, stripped)
    if not trace:
        ok = parser.parse_utterance(utt)
        tree = parser.get_best_tuple().get_tree()
        if tree.semantic_profile and parser.last_cap_hit is None:
            tree = _complete_native_parse(parser)
            ok = ok and tree.is_complete()
        ok = ok and parser.last_cap_hit is None
        semantics: Formula | None = parser.get_final_semantics() if ok else None
        return ParseResult(
            ok=ok,
            semantics=semantics,
            tree=tree,
            sentence=stripped,
            parser=parser,
            cap_hit=parser.last_cap_hit,
            stats=parser.stats.snapshot(),
        )
    trace_list: list[Tree] = [parser.get_best_tuple().get_tree().clone()]
    labels: list[str] = []
    ok = True
    for uw in utt.words:
        labels.append(uw.word)
        if parser.parse_word(uw) is None:
            ok = False
        trace_list.append(parser.get_best_tuple().get_tree().clone())
        if parser.last_cap_hit is not None:
            break
    tree = parser.get_best_tuple().get_tree()
    if tree.semantic_profile and parser.last_cap_hit is None:
        tree = _complete_native_parse(parser)
        ok = ok and tree.is_complete()
    ok = ok and parser.last_cap_hit is None
    semantics = parser.get_final_semantics() if ok else None
    # Prefix snapshots record what was known at each word. The derivation must
    # instead follow the final active path after any later backtracking.
    action_steps = [step for edge in _active_path_edges(parser)
                    for step in _steps_from_edge(parser, edge)]
    return ParseResult(
        ok=ok,
        semantics=semantics,
        tree=tree,
        sentence=stripped,
        trace_trees=tuple(trace_list),
        trace_step_labels=tuple(labels),
        action_steps=tuple(action_steps),
        parser=parser,
        cap_hit=parser.last_cap_hit,
        stats=parser.stats.snapshot(),
    )


def _parse_one(
    parser: InteractiveContextParser,
    raw: str,
    *,
    speaker: str,
    trace: bool,
) -> ParseResult:
    """Strip *raw*, return a blank failure without parsing, or run the parse pipeline on *parser*."""
    stripped = raw.strip()
    if not stripped:
        return ParseResult(ok=False, semantics=None, tree=None, sentence="", parser=parser)
    return _run_parse_core(parser, stripped, speaker=speaker, trace=trace)


def _parse_at_path(
    grammar_path: Path,
    sentence: str,
    *,
    speaker: str,
    trace: bool,
    top_n: int = 3,
    strict: bool = False,
    log_level: LogLevel = "off",
    log_output: LogOutput = "terminal",
    log_dir: Path | None = None,
) -> ParseResult:
    """Run parse at *grammar_path* and build a :class:`ParseResult`."""
    parser = InteractiveContextParser(
        grammar_path,
        top_n=top_n,
        strict=strict,
        log_level=log_level,
        log_output=log_output,
        log_dir=log_dir,
    )
    return _parse_one(parser, sentence, speaker=speaker, trace=trace)


_GRAMMAR_REQUIRED_MSG = (
    "grammar is required for dynamicsyntax.parse(...); use parser.parse(...) after "
    "dynamicsyntax.icp().set_grammar(...), or pass grammar= to parse(...)"
)


@overload
def parse(
    sentence: str,
    grammar: str | Path,
    /,
    *,
    speaker: str = ...,
    trace: bool = ...,
    top_n: int = ...,
    strict: bool = ...,
    log_level: LogLevel = ...,
    log_output: LogOutput = ...,
    log_dir: Path | None = ...,
) -> ParseResult: ...


@overload
def parse(
    sentences: list[str],
    grammar: str | Path,
    /,
    *,
    speaker: str = ...,
    trace: bool = ...,
    top_n: int = ...,
    strict: bool = ...,
    log_level: LogLevel = ...,
    log_output: LogOutput = ...,
    log_dir: Path | None = ...,
) -> list[ParseResult]: ...


def parse(
    sentence_or_sentences: str | list[str],
    grammar: str | Path | None = None,
    /,
    *,
    speaker: str = DEFAULT_SPEAKER,
    trace: bool = False,
    top_n: int = 3,
    strict: bool = False,
    log_level: LogLevel = "off",
    log_output: LogOutput = "terminal",
    log_dir: Path | None = None,
) -> ParseResult | list[ParseResult]:
    """Parse one or many sentences and return :class:`~dynamicsyntax.parse_result.ParseResult` objects.

    :param sentence_or_sentences: A single whitespace-tokenised surface string, or a list of
        such strings (lowercased by the tokenizer). An empty list returns ``[]`` without using
        a grammar. Per-item blank or whitespace-only strings yield a failed result for that slot.
    :param grammar: Bundled id or alias (e.g. ``\"ttr\"``) or a grammar directory path. Required
        for non-empty input; for grammar-bound parsing on a long-lived object use
        :func:`dynamicsyntax.icp` and :meth:`~dylan.parser.interactive_context_parser.InteractiveContextParser.parse`.
    :param speaker: Dialogue participant id passed to the parser (default matches ``dylan``).
    :param trace: If ``True``, record one DS tree after ``new_sentence`` and after each word
        (for :meth:`~dynamicsyntax.parse_result.ParseResult.to_latex` ``incremental``).
    :param top_n: Maximum lexical entries per word (default 3); 0 keeps all entries.
    :param strict: Raise ``ValueError`` on lexicon or grammar validation problems (default False).
    :param log_level: Per-parser log verbosity passed to :class:`~dylan.parser.interactive_context_parser.InteractiveContextParser`.
    :param log_output: Where parser-bound logs go (terminal, file, or both).
    :param log_dir: Directory for parser log files when *log_output* includes file output.
    :returns: One :class:`~dynamicsyntax.parse_result.ParseResult`, or a list of them in input
        order; ``semantics`` is ``None`` on failure or blank input for that item.
        Each result may include ``parser`` (the
        :class:`~dylan.parser.interactive_context_parser.InteractiveContextParser` used), except when
        the facade returns early for whitespace-only single-string input without a parse.
    :raises ValueError: If *grammar* is omitted or ``None`` while any non-blank input would require parsing,
        or resource validation fails with *strict* enabled.
    :raises FileNotFoundError: If *grammar* is unknown or not a directory.

    Packaged grammars: ``dynamicsyntax/grammars/`` in the library, and the project
    :mod:`dynamicsyntax.resources` tree (the repository ``resources/`` directory at build time), read
    via :mod:`importlib.resources`. A single string with explicit
    *grammar* uses one fresh parser; a list with explicit *grammar* reuses one parser for all items.
    """
    if isinstance(sentence_or_sentences, list):
        sentences = sentence_or_sentences
        if not sentences:
            return []
        if grammar is None:
            if any(s.strip() for s in sentences):
                raise ValueError(_GRAMMAR_REQUIRED_MSG)
            return [
                ParseResult(ok=False, semantics=None, tree=None, sentence="", parser=None)
                for _ in sentences
            ]
        with resolved_grammar_path(grammar) as grammar_path:
            parser = InteractiveContextParser(
                grammar_path,
                top_n=top_n,
                strict=strict,
                log_level=log_level,
                log_output=log_output,
                log_dir=log_dir,
            )
            return [_parse_one(parser, s, speaker=speaker, trace=trace) for s in sentences]

    sentence = sentence_or_sentences
    stripped = sentence.strip()
    if not stripped:
        return ParseResult(ok=False, semantics=None, tree=None, sentence="", parser=None)

    if grammar is None:
        raise ValueError(_GRAMMAR_REQUIRED_MSG)

    with resolved_grammar_path(grammar) as grammar_path:
        return _parse_at_path(
            grammar_path,
            stripped,
            speaker=speaker,
            trace=trace,
            top_n=top_n,
            strict=strict,
            log_level=log_level,
            log_output=log_output,
            log_dir=log_dir,
        )
