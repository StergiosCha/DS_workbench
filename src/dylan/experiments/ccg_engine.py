"""Independent incremental CCG chart; it imports no DS parser or tree classes."""

from pathlib import Path

from dylan.experiments.contracts import Analysis, digest
from dylan.hybrid import ccg
from dylan.hybrid.terms import app, const, lam, var


def study_lexicon():
    """Explicit hand-declared lexical fragment; no experimental labels are inputs."""
    vocabulary = ccg.lexicon()
    for word in ("bill", "george"):
        vocabulary[word] = [ccg.Sign(ccg.cat("NP"), const(word), (word,))]
    for word in ("dog", "doctor", "patient", "stone", "library", "park", "peacock", "stage"):
        vocabulary[word] = [ccg.Sign(ccg.cat("N"), const(word), (word,))]
    for word, predicate in {"reads": "read", "knows": "know", "examines": "examine", "examined": "examine",
                            "burns": "burn", "likes": "like"}.items():
        meaning = lam("o", lam("s", app(app(const(predicate), var("s")), var("o"))))
        vocabulary[word] = [ccg.Sign(ccg.cat("(S\\NP)/NP"), meaning, (word,))]
    for word, predicate in {"walks": "walk", "shouts": "shout", "arrives": "arrive"}.items():
        vocabulary[word] = [ccg.Sign(ccg.cat("S\\NP"), lam("s", app(const(predicate), var("s"))), (word,))]
    for word in ("black", "wild"):
        vocabulary[word] = [ccg.Sign(ccg.cat("N/N"), lam("p", app(const(word), var("p"))), (word,))]
    return vocabulary


class Chart:
    def __init__(self, *, composition=True, type_raising=True, cap=256):
        self.composition, self.type_raising, self.cap = composition, type_raising, cap
        self.cells, self.words, self.limited = {}, [], False
        self.combinations = 0

    def append(self, word, entries):
        start = len(self.words)
        self.words.append(word)
        lexical = list(entries)
        if self.type_raising:
            lexical += [ccg.raise_np(sign) for sign in entries if sign.category == ccg.cat("NP")]
        if len(lexical) > self.cap:
            self.limited = True
        self.cells[start, start + 1] = lexical[:self.cap]
        end = start + 1
        # Only cells with the newly observed right boundary are constructed.
        # Existing prefix cells are retained, never recomputed from future words.
        for left_boundary in range(start - 1, -1, -1):
            answers = {}
            for split in range(left_boundary + 1, end):
                for left in self.cells[left_boundary, split]:
                    for right in self.cells[split, end]:
                        self.combinations += 1
                        for sign in ccg.combine(left, right, composition=self.composition):
                            key = (str(sign.category), str(sign.meaning))
                            if key not in answers and len(answers) >= self.cap:
                                self.limited = True
                            else:
                                answers[key] = sign
            self.cells[left_boundary, end] = list(answers.values())

    @property
    def analyses(self):
        return self.cells.get((0, len(self.words)), [])

    def state(self):
        return {"observed": list(self.words), "categories": sorted({str(a.category) for a in self.analyses}),
                "complete": any(a.category == ccg.cat("S") for a in self.analyses),
                "chart_cells": {f"{i}:{j}": sorted({str(a.category) for a in values}) for (i, j), values in self.cells.items()},
                "limited": self.limited}


def structural_cues(analyses):
    cues = set()

    def visit(sign):
        if sign.children:
            cues.add(("ccg-rule", sign.rule, str(sign.category), *(str(c.category) for c in sign.children)))
        for child in sign.children:
            visit(child)
    for analysis in analyses:
        visit(analysis)
    return tuple(sorted(cues))


class CCGEngine:
    def __init__(self, identifier):
        self.identifier = identifier
        self.vocabulary = ccg.lexicon() if identifier == "ccg-original-v1" else study_lexicon()
        self.composition = identifier != "ccg-application-v1"
        self.type_raising = identifier == "ccg-incremental-v1"

    def analyse(self, observation, *, trace=True):
        context = observation.left_context.lower().split()
        words = context + observation.text.lower().split()
        provenance = {"lexicon_sha256": digest({word: [entry.to_dict() for entry in entries]
                                               for word, entries in self.vocabulary.items()}),
                      "implementation_sha256": digest([Path(__file__).read_text(), Path(ccg.__file__).read_text()]),
                      "composition": self.composition, "type_raising": self.type_raising,
                      "cue_contract": "Union of rule/result/child-category tuples in retained full-span analyses",
                      "fragment_contract": "A category derived over the full supplied context and fragment; no DS completion predicate",
                      "tokenization": "lowercase whitespace tokens", "cell_cap": 256}
        if len(words) > 12:
            return Analysis(self.identifier, observation, "unsupported_length", False, False, provenance=provenance)
        chart = Chart(composition=self.composition, type_raising=self.type_raising)
        frames, unknown = [], None
        for index, word in enumerate(words):
            if word not in self.vocabulary:
                unknown = {"word": word, "index": index}
                break
            before = chart.state() if trace else None
            chart.append(word, self.vocabulary[word])
            if trace:
                frames.append({"index": index, "context": index < len(context), "word": word,
                               "before": before, "after": chart.state()})
        complete = any(sign.category == ccg.cat("S") for sign in chart.analyses)
        supported = bool(chart.analyses) and (observation.task == "fragment" or complete)
        status = "complete" if complete else "recognized_fragment" if supported else "no_derivation"
        if chart.limited:
            status, supported = "search_limit", False
        if unknown:
            status, supported = "unsupported_lexicon", False
            provenance["failure"] = unknown
        provenance["analyses"] = [a.to_dict() for a in chart.analyses] if trace else []
        return Analysis(self.identifier, observation, status, supported, complete and supported,
                        structural_cues(chart.analyses) if supported else (),
                        tuple(sorted({str(a.meaning) for a in chart.analyses})) if supported else (), frames,
                        {"combination_attempts": chart.combinations, "chart_cells": len(chart.cells),
                         "retained_analyses": len(chart.analyses), "counter_unit": "CCG sign-pair combinations"}, provenance)

    def close(self):
        pass
