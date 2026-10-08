"""Paragraph orchestration. Only completed DS trees enter subsequent context.

Sentence segmentation is deterministic and its exact source spans are returned.
Completion is an engine result, not a claim that the text is grammatical or true.
"""

from contextlib import contextmanager
from copy import deepcopy
from functools import lru_cache
import json
import re
import signal
import threading
import time

from dylan.action.meta.element import restore_meta_bindings, snapshot_meta_bindings
from dylan.nlp.types import utterance_from_text

ABBREVIATIONS = {
    "en": {"mr", "mrs", "ms", "dr", "prof", "rev", "st", "sr", "jr", "vs", "e.g", "i.e"},
    "el": {"κ", "κα", "δρ", "καθ", "π.χ", "δηλ", "αρ", "σελ", "βλ"},
}
CLOSERS = '\"\'”’»)]}'
PARAGRAPH_SECONDS = 23
SENTENCE_SECONDS = 3


@lru_cache(maxsize=1)
def configuration():
    from dylan.workbench_paths import data_path

    path = data_path("coverage/paragraph-baseline.json")
    try:
        baseline = json.loads(path.read_text())["summary"]
    except (OSError, ValueError, KeyError):
        baseline = None
    try:
        assisted = json.loads((path.parent / "open-text-results.json").read_text())["summary"]
    except (OSError, ValueError, KeyError):
        assisted = None
    return {"max_characters": 6000, "max_tokens": 400, "max_sentences": 24,
            "baseline": baseline,
            "assisted_probe": assisted,
            "baseline_note": "2026-10-01: six sampled English source paragraphs and six Greek passages (three consecutive test-set sentences each; original paragraph boundaries unavailable). Small engineering sample, not a representative accuracy estimate."}


def sentence_spans(text, language):
    """Preserve all non-whitespace text; Greek semicolon is a question boundary.

    Initials, common abbreviations and decimal points do not end sentences.
    Ambiguous abbreviations/quotations remain a documented segmentation limit.
    """
    terminal = ".?!;;" if language == "el" else ".?!"
    start, i = 0, 0
    spans = []

    def append(end):
        nonlocal start
        left, right = start, end
        while left < right and text[left].isspace():
            left += 1
        while right > left and text[right - 1].isspace():
            right -= 1
        if left < right:
            spans.append({"text": text[left:right], "start": left, "end": right})
        start = end

    while i < len(text):
        char = text[i]
        if char not in terminal:
            i += 1
            continue
        if char == ".":
            if i and i + 1 < len(text) and text[i - 1].isdigit() and text[i + 1].isdigit():
                i += 1
                continue
            match = re.search(r"([\w.]+)$", text[start:i], re.UNICODE)
            token = match.group(1) if match else ""
            if (token.lower() in ABBREVIATIONS[language]
                    or len(token) == 1 and token.isupper()
                    or re.fullmatch(r"(?:[A-Za-zΑ-ΩΆΈΉΊΌΎΏ]\.)+[A-Za-zΑ-ΩΆΈΉΊΌΎΏ]", token)):
                i += 1
                continue
        end = i + 1
        while end < len(text) and text[end] in terminal + CLOSERS:
            end += 1
        if end == len(text) or text[end].isspace():
            append(end)
        i = end
    append(len(text))
    return spans


def validate_paragraph(payload):
    if "sentence" in payload or "dialogue" in payload:
        raise ValueError("Send one input: paragraph, sentence or dialogue.")
    text = payload.get("paragraph")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter a paragraph to parse.")
    if len(text) > 6000:
        raise ValueError("Use a paragraph of at most 6000 characters.")
    grammar = payload.get("grammar", "")
    if not isinstance(grammar, str) or grammar not in {f"2026-{lang}-{b}" for lang in ("english", "smg") for b in ("classical", "mltt")}:
        raise ValueError("Paragraphs support the native English and Standard Modern Greek grammars.")
    spans = sentence_spans(text, "en" if "english" in grammar else "el")
    if len(spans) > 24:
        raise ValueError("Use at most 24 sentences in a paragraph.")
    if sum(len(utterance_from_text("Dylan", s["text"]).words) for s in spans) > 400:
        raise ValueError("Use a paragraph of at most 400 tokens.")
    return text, spans


class SentenceDeadline(Exception):
    pass


@contextmanager
def time_budget(seconds):
    # Hosted parsing runs in its own main-thread process. Preserve an enclosing
    # alarm; direct library callers on other threads retain their caller's limits.
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGALRM)
    timer = signal.getitimer(signal.ITIMER_REAL)
    started = time.monotonic()
    def expired(signum, frame):
        raise SentenceDeadline("The sentence exceeded its parsing time budget.")
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, min(seconds, timer[0]) if timer[0] else seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if timer[0]:
            signal.setitimer(signal.ITIMER_REAL, max(.001, timer[0] - (time.monotonic() - started)), timer[1])


def parse_paragraph(payload, on_event=None):
    from dynamicsyntax import icp
    from dylan.workbench_api import parse_request

    text, spans = validate_paragraph(payload)
    started = time.monotonic()
    options = {k: v for k, v in payload.items() if k not in {"paragraph", "stream"}}
    parser = icp(payload["grammar"], top_n=payload.get("top_n", 0), strict=payload.get("strict", False))
    rows, committed, gaps = [], [], []
    if on_event:
        on_event({"event": "paragraph_start", "paragraph": text, "sentences": spans})
    try:
        parser.init()
        assisted = payload.get("lexical_mode") == "assisted"
        if assisted:
            from dylan.assisted_parsing import Assistance
            all_tokens = [w.word for s in spans for w in utterance_from_text("Dylan", s["text"]).words]
            parser._assistance = Assistance(parser, payload["grammar"], all_tokens, live_sources=payload.get("live_greek_sources", False), source_corpus=payload.get("greek_source_corpus", "ud_ud_greek-gud"))
            if on_event:
                on_event({"event": "lexical", "message": "Preparing vocabulary for the whole paragraph…"})
            parser._assistance.seed()
        for index, span in enumerate(spans):
            tokens = [w.word for w in utterance_from_text("Dylan", span["text"]).words]
            row = {**span, "index": index, "tokens": tokens, "complete": False,
                   "context_sentences": list(committed), "context_gaps": list(gaps)}
            remaining = (50 if assisted else PARAGRAPH_SECONDS) - (time.monotonic() - started)
            if len(span["text"]) > 2000 or len(tokens) > 160:
                row.update(status="input_limit", failure={"kind": "input_limit", "message": "This sentence exceeds 2000 characters or 160 tokens."})
            elif remaining <= .05:
                row.update(status="not_attempted", failure={"kind": "paragraph_limit", "message": "The paragraph time budget was exhausted before this sentence."})
            else:
                # A failed hypothesis must not supply antecedents to later text.
                checkpoint = deepcopy(parser.context)
                lexical_checkpoint = {word: list(entries) for word, entries in parser.lexicon.items()}
                profile_checkpoint = deepcopy(parser.semantic_profile)
                entries_checkpoint = getattr(parser, "_paragraph_lexical_entries", [])
                assisted_entries_checkpoint = list(parser._assistance.entries) if assisted else None
                selector_checkpoint = getattr(parser, "lexical_selector", None)
                bindings = snapshot_meta_bindings()
                try:
                    with time_budget(min(remaining, 30 if assisted else SENTENCE_SECONDS)):
                        parser.semantic_profile = {**parser.semantic_profile, "sentence_namespace": f"s{index + 1}_"}
                        result = parse_request({**options, "sentence": span["text"]}, _parser=parser, _trace=False)
                    row.update(status="complete" if result["complete"] else "failed",
                               complete=result["complete"], failure=result["failure"],
                               result=result)
                    # Paragraph inspection keeps actual word boundaries. Replay
                    # duplicates are omitted so hundreds of tokens fit the host.
                    result["actions"] = []
                    result["operations"] = []
                    result["trace_note"] = "Recorded DS word states; paragraph inspection uses word steps. Each completed sentence includes its selected rule sequence and semantic export."
                    if not result["complete"] and not row["failure"]:
                        row["failure"] = {"kind": "incomplete_tree", "message": "The sentence leaves unsatisfied DS requirements."}
                    # Bound unusually large individual traces, keeping the final
                    # tree and stating exactly which earlier states were omitted.
                    if len(json.dumps(result, ensure_ascii=False).encode()) > 180_000:
                        result["words"] = [result["words"][0], result["words"][-1]]
                        result["trace_level"] = "endpoints"
                        result["trace_note"] += " Only the initial and final states fit this sentence's trace budget."
                    if result["complete"]:
                        committed.append(index)
                except SentenceDeadline as exc:
                    row.update(status="search_limit", failure={"kind": "search_limit", "message": str(exc)})
                except Exception as exc:
                    # Preserve the other sentences while exposing the engine error.
                    row.update(status="error", failure={"kind": "engine_error", "message": f"{type(exc).__name__}: {exc}"})
                if not row["complete"]:
                    parser.context = checkpoint
                    # An alarm can interrupt lexical installation as well as
                    # parsing. Roll back the whole sentence transaction, so no
                    # half-installed entry or unreported hypothesis survives.
                    parser.lexicon.clear()
                    parser.lexicon.update(lexical_checkpoint)
                    parser.lexicon.invalidate_vocab_cache()
                    parser.semantic_profile = profile_checkpoint
                    parser._paragraph_lexical_entries = entries_checkpoint
                    if assisted:
                        parser._assistance.entries = assisted_entries_checkpoint
                    parser.lexical_selector = selector_checkpoint
                    restore_meta_bindings(bindings)
            if not row["complete"]:
                gaps.append(index)
            rows.append(row)
            if on_event:
                on_event({"event": "paragraph_sentence", "sentence": {k: v for k, v in row.items() if k != "result"}})
    finally:
        parser.close()
    return {"kind": "paragraph", "paragraph": text, "grammar": payload["grammar"],
            "complete": len(committed) == len(spans), "ok": len(committed) == len(spans),
            "sentences": rows, "coverage": {"complete": len(committed), "total": len(spans),
                "failed": len(gaps), "all_complete": not gaps},
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "segmentation": "Deterministic source spans; common abbreviations and decimals preserved. Ambiguous quotations/abbreviations may need explicit sentence boundaries.",
            "context_note": "Completed sentences retain their DS context. Failed sentences are excluded and listed as context gaps; later analyses do not establish a complete interpretation of the paragraph. Pronoun resolution currently handles basic named antecedents, not general discourse inference.",
            "verification": "DS completion and semantic type checks, relative to this grammar and its lexical assumptions. No LLM tree or grammaticality judgment substitutes for a derivation."}
