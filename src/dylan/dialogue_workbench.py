"""Bounded transcript input and demonstration cases for the DS dialogue lab."""

from dylan.nlp.types import utterance_from_text
from dylan.dag.uttered_word import UtteredWord


def validate_dialogue(payload):
    turns = payload.get("dialogue")
    if "sentence" in payload:
        raise ValueError("Send either a sentence or a dialogue, not both.")
    if not isinstance(turns, list) or not 1 <= len(turns) <= 12:
        raise ValueError("Use between 1 and 12 dialogue turns.")
    clean = []
    for turn in turns:
        if not isinstance(turn, dict):
            raise ValueError("Each turn needs a speaker and text.")
        speaker, text = turn.get("speaker"), turn.get("text")
        if (
            not isinstance(speaker, str)
            or not speaker.strip()
            or len(speaker) > 32
            or any(c in speaker for c in "\r\n")
        ):
            raise ValueError("Use a speaker name of 1–32 characters on one line.")
        if not isinstance(text, str) or not text.strip() or len(text) > 500:
            raise ValueError("Each turn needs 1–500 characters of text.")
        boundary = turn.get("boundary", "continue")
        if boundary not in {"continue", "new_tree"}:
            raise ValueError("A turn must continue the tree or start a new tree.")
        clean.append({"speaker": speaker.strip(), "text": text.strip(), "boundary": boundary})
    if len({t["speaker"] for t in clean}) > 2:
        raise ValueError("This dialogue lab supports one or two speakers.")
    if sum(len(t["text"]) for t in clean) > 1200:
        raise ValueError("Use at most 1200 characters across the dialogue.")
    if sum(len(utterance_from_text(t["speaker"], t["text"]).words) for t in clean) > 80:
        raise ValueError("Use at most 80 tokens across the dialogue.")
    return clean


def transcript_words(turns):
    participants = list(dict.fromkeys(turn["speaker"] for turn in turns))
    words, metadata = [], []
    for turn_index, turn in enumerate(turns):
        for position, word in enumerate(utterance_from_text(turn["speaker"], turn["text"]).words):
            if len(participants) == 2:
                word = UtteredWord(
                    word.word, word.speaker, next(p for p in participants if p != word.speaker)
                )
            words.append(word)
            metadata.append(
                {
                    "speaker": word.speaker,
                    "addressee": word.addressee,
                    "turn_index": turn_index,
                    "turn_start": position == 0,
                    "boundary": turn["boundary"],
                }
            )
    return words, metadata


def configuration():
    return {
        "max_turns": 12,
        "max_tokens": 80,
        "max_characters": 1200,
        "coverage": "Shared tree growth across speakers; explicit local repair of the last lexical contribution; earlier trees retained for inspection. Native English supports do/does/did polar questions, local subject-binding reflexives and Yes/No answers to the immediately preceding complete question. Speaker and addressee are evaluated at each word. Question content and answer polarity are labelled separately. General ellipsis, clarification acts, grounding, tense semantics and full agreement are not implemented.",
        "examples": [
            {
                "id": "shared-question",
                "label": "Question & answer",
                "family": "english",
                "backends": ["classical", "mltt"],
                "turns": [
                    {"speaker": "A", "text": "Did you burn"},
                    {"speaker": "B", "text": "myself?"},
                    {"speaker": "A", "text": "No"},
                ],
            },
            {
                "id": "shared",
                "label": "Shared completion",
                "family": "english",
                "turns": [
                    {"speaker": "A", "text": "john likes"},
                    {"speaker": "B", "text": "mary."},
                ],
            },
            {
                "id": "self-repair",
                "label": "Self-repair",
                "family": "english",
                "turns": [{"speaker": "A", "text": "john likes mary sorry bill."}],
            },
            {
                "id": "other-repair",
                "label": "Correction by B",
                "family": "english",
                "turns": [
                    {"speaker": "A", "text": "john likes mary."},
                    {"speaker": "B", "text": "sorry bill."},
                ],
            },
            {
                "id": "new-tree",
                "label": "Two propositions",
                "family": "english",
                "turns": [
                    {"speaker": "A", "text": "john likes mary."},
                    {"speaker": "B", "text": "bill walks.", "boundary": "new_tree"},
                ],
            },
            {
                "id": "smg-shared",
                "label": "Shared Greek clause",
                "family": "smg",
                "turns": [{"speaker": "A", "text": "τον"}, {"speaker": "B", "text": "αγαπά."}],
            },
            {
                "id": "cypriot-shared",
                "label": "Shared Cypriot clause",
                "family": "cypriot",
                "turns": [{"speaker": "A", "text": "εν"}, {"speaker": "B", "text": "τον ιξέρω."}],
            },
            {
                "id": "pontic-shared",
                "label": "Shared Pontic clause",
                "family": "pontic",
                "turns": [{"speaker": "A", "text": "ci kser"}, {"speaker": "B", "text": "aton."}],
            },
        ],
    }
