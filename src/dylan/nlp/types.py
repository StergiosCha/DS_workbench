"""Utterance and lightweight tokenisation (replaces Stanford `HasWord` usage)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
import unicodedata

from dylan.dag.uttered_word import UtteredWord

DEFAULT_SPEAKER = "Dylan"
RELEASE_TURN_TOKEN = "<rt>"
WAIT_TOKEN = "<wait>"
TERMINAL_PUNCTUATION = (".", "?", "!", ",", ";", ";")
CONTRACTIONS = {
    "i'm": ("i", "am"), "you're": ("you", "are"), "we're": ("we", "are"),
    "they're": ("they", "are"), "don't": ("do", "not"), "doesn't": ("does", "not"),
    "didn't": ("did", "not"), "isn't": ("is", "not"), "aren't": ("are", "not"),
    "wasn't": ("was", "not"), "weren't": ("were", "not"), "can't": ("can", "not"),
    "cannot": ("can", "not"), "couldn't": ("could", "not"), "shouldn't": ("should", "not"),
    "mustn't": ("must", "not"), "won't": ("will", "not"), "wouldn't": ("would", "not"),
    "haven't": ("have", "not"), "hasn't": ("has", "not"), "hadn't": ("had", "not"),
}


@dataclass
class Utterance:
    """Sequence of `UtteredWord` with a speaker id (Java `Utterance`, simplified)."""

    speaker: str
    words: list[UtteredWord] = field(default_factory=list)

    def __len__(self) -> int:
        """Return number of words."""
        return len(self.words)

    def speaker_id(self) -> str:
        """Return the utterance speaker id."""
        return self.speaker

    def add_word(self, word: str, addressee: str = "you") -> None:
        """Append a word to this utterance."""
        self.words.append(UtteredWord(word, self.speaker, addressee))

    def __iter__(self) -> Iterator[UtteredWord]:
        """Iterate over uttered words."""
        return iter(self.words)

    def __str__(self) -> str:
        """Return speaker-prefixed utterance text."""
        return f"{self.speaker}: " + " ".join(w.word or "" for w in self.words)


@dataclass
class Dialogue:
    """Sequence of utterances with participant metadata (Java ``Dialogue``)."""

    utterances: list[Utterance] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)

    def add_utterance(self, utterance: Utterance) -> None:
        """Append an utterance and register its speaker as a participant."""
        self.utterances.append(utterance)
        if utterance.speaker not in self.participants:
            self.participants.append(utterance.speaker)

    def get_participants(self) -> list[str]:
        """Return dialogue participants."""
        if self.participants:
            return list(self.participants)
        seen: list[str] = []
        for utt in self.utterances:
            if utt.speaker not in seen:
                seen.append(utt.speaker)
        return seen

    def __iter__(self) -> Iterator[Utterance]:
        """Iterate utterances in order."""
        return iter(self.utterances)

    @staticmethod
    def load_dialogues_from_file(path: str | Path) -> list["Dialogue"]:
        """Load simple speaker-prefixed dialogues from a text file."""
        dialogue = Dialogue()
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                if dialogue.utterances:
                    break
                continue
            if ":" in line:
                speaker, text = line.split(":", 1)
                dialogue.add_utterance(utterance_from_text(speaker.strip(), text.strip()))
            else:
                dialogue.add_utterance(utterance_from_text(DEFAULT_SPEAKER, line))
        return [dialogue] if dialogue.utterances else []


def _detach_terminal_punctuation(chunk: str) -> list[str]:
    """Split trailing terminal punctuation off *chunk* into separate tokens.

    ``"you."`` becomes ``["you", "."]`` and ``"you?!"`` becomes
    ``["you", "?", "!"]``; a bare punctuation token like ``"."`` and
    word-internal punctuation like ``"3.5"`` are left untouched.
    """
    trailing: list[str] = []
    while len(chunk) > 1 and chunk[-1] in TERMINAL_PUNCTUATION:
        trailing.append(chunk[-1])
        chunk = chunk[:-1]
    trailing.reverse()
    return [chunk, *trailing]


def whitespace_tokenize(text: str) -> list[str]:
    """Split on whitespace for tests and default parsing.

    Terminal punctuation (``.``, ``?``, ``!``, ``,``) attached to the end of a
    word is detached into its own token so lexical actions triggered by
    punctuation (e.g. the ``.`` assert action) see it as a word.
    """
    tokens: list[str] = []
    for chunk in unicodedata.normalize("NFC", text).strip().lower().split():
        for token in _detach_terminal_punctuation(chunk):
            tokens.extend(CONTRACTIONS.get(token.replace("’", "'"), (token,)))
    return tokens


def utterance_from_text(speaker: str, text: str) -> Utterance:
    """Build an `Utterance` from raw text using `whitespace_tokenize`."""
    return Utterance(
        speaker=speaker,
        words=[UtteredWord(w, speaker) for w in whitespace_tokenize(text)],
    )


Utterance.speakerId = Utterance.speaker_id  # type: ignore[attr-defined]
Utterance.addWord = Utterance.add_word  # type: ignore[attr-defined]
Dialogue.addUtterance = Dialogue.add_utterance  # type: ignore[attr-defined]
Dialogue.getParticipants = Dialogue.get_participants  # type: ignore[attr-defined]
Dialogue.loadDialoguesFromFile = Dialogue.load_dialogues_from_file  # type: ignore[attr-defined]
