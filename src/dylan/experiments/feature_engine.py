"""A declared CCG/application fragment with optional typed number constraints.

The engine sees words only, never suite IDs, regions, conditions or gold labels.
NP heads are propagated through actual categorial derivations. Constraints are
checked when an NP combines with S\\NP; PP objects do not replace the NP head.
The same lexicon and chart are used by all five component configurations.
"""

from dataclasses import dataclass, replace
from pathlib import Path

from dylan.experiments.contracts import Analysis, digest
from dylan.experiments.ccg_engine import structural_cues
from dylan.hybrid import ccg, features
from dylan.hybrid.terms import app, const, lam, var

MODES = {
    "ccg-feature-head-v1": (True, True, "head"),
    "ccg-feature-none-v1": (False, False, "head"),
    "ccg-feature-nearest-v1": (True, True, "nearest"),
    "ccg-feature-no-agreement-v1": (False, True, "head"),
    "ccg-feature-no-binding-v1": (True, False, "head"),
}
TYPES = features.linguistic_types()
NP, N, S, VP = (ccg.cat(c) for c in ("NP", "N", "S", "S\\NP"))
CAP, MAX_WORDS = 256, 32


@dataclass(frozen=True)
class Nominal:
    lemma: str
    number: str
    word: str

    def to_dict(self):
        return {"lemma": self.lemma, "number": self.number, "word": self.word}


@dataclass(frozen=True)
class Sign:
    core: ccg.Sign
    nominal: Nominal | None = None
    last_nominal: Nominal | None = None
    verb_number: str | None = None
    reflexive_number: str | None = None
    checks: tuple = ()

    def key(self):
        return (str(self.core.category), str(self.core.meaning), self.nominal,
                self.last_nominal, self.verb_number, self.reflexive_number)

    def to_dict(self):
        return {"derivation": self.core.to_dict(),
                "head": self.nominal.to_dict() if self.nominal else None,
                "last_nominal": self.last_nominal.to_dict() if self.last_nominal else None,
                "verb_number": self.verb_number, "reflexive_number": self.reflexive_number,
                "checks": list(self.checks)}


def lexicon():
    """Source-informed development vocabulary, declared without condition labels.

    Includes unused regular controls; noun plurals are lexical morphology, not
    inferred from a target's expected answer. Masculine reference is contextual.
    """
    result = {}

    def add(word, category, meaning, **kwargs):
        result.setdefault(tuple(word.split()), []).append(
            Sign(ccg.Sign(ccg.cat(category), meaning, tuple(word.split())), **kwargs))

    nouns = {
        "author": "authors", "pilot": "pilots", "doctor": "doctors",
        "farmer": "farmers", "manager": "managers", "customer": "customers",
        "officer": "officers", "teacher": "teachers", "senator": "senators",
        "consultant": "consultants", "guard": "guards", "clerk": "clerks",
        "architect": "architects", "athlete": "athletes", "actor": "actors",
        "minister": "ministers", "driver": "drivers", "secretary": "secretaries",
        "executive": "executives", "student": "students", "sailor": "sailors",
        "mechanic": "mechanics", "person": "people", "feeling": "feelings",
    }
    for lemma, plural in nouns.items():
        for word, number in ((lemma, "sg"), (plural, "pl")):
            nominal = Nominal(lemma, number, word)
            add(word, "N", const(lemma), nominal=nominal, last_nominal=nominal)
            if word in {"people", "feelings"}:
                add(word, "NP", app(const("bare_plural"), const(lemma)),
                    nominal=nominal, last_nominal=nominal)
    for word in ("the", "a", "many"):
        add(word, "NP/N", lam("p", app(const(word), var("p"))))
    add("taxi", "N/N", lam("p", app(const("taxi"), var("p"))))
    add("good", "ADJ", const("good"))
    add("good", "N/N", lam("p", app(const("good"), var("p"))))
    add("good", "NP/NP", lam("x", app(const("good"), var("x"))))
    for word in ("love", "tennis"):
        nominal = Nominal(word, "sg", word)
        add(word, "NP", const(word), nominal=nominal, last_nominal=nominal)
    for word in ("next to", "behind", "in front of", "near", "to the side of", "across from"):
        name = word.replace(" ", "_")
        add(word, "(NP\\NP)/NP",
            lam("o", lam("h", app(app(const(name), var("h")), var("o")))))
    add("to", "PP/NP", lam("x", var("x")))
    add("to", "TO/VI", lam("p", var("p")))
    add("gamble", "VI", lam("s", app(const("gamble"), var("s"))))
    add("playing", "VG/NP", lam("o", lam("s", app(app(const("play"), var("s")), var("o")))))
    for singular, plural, predicate in (
        ("interests", "interest", "interest"), ("knows", "know", "know"),
        ("likes", "like", "like"), ("admires", "admire", "admire"),
        ("enjoys", "enjoy", "enjoy"),
    ):
        for word, number in ((singular, "sg"), (plural, "pl")):
            add(word, "(S\\NP)/NP", lam("o", lam("s", app(app(const(predicate), var("s")), var("o")))),
                verb_number=number)
    for word, number in (("likes", "sg"), ("like", "pl"), ("enjoys", "sg"), ("enjoy", "pl")):
        argument = "TO" if word in {"likes", "like"} else "VG"
        predicate = "like" if argument == "TO" else "enjoy"
        add(word, f"(S\\NP)/{argument}",
            lam("p", lam("s", app(app(const(predicate), var("s")), app(var("p"), var("s"))))),
            verb_number=number)
    for word, number in (("is", "sg"), ("are", "pl")):
        add(word, "(S\\NP)/ADJ", lam("p", lam("s", app(var("p"), var("s")))), verb_number=number)
        add(word, "(S\\NP)/VG",
            lam("p", lam("s", app(const("progressive"), app(var("p"), var("s"))))),
            verb_number=number)
    for word, number in (("brings", "sg"), ("bring", "pl")):
        add(word, "(S\\NP)/NP",
            lam("o", lam("s", app(app(const("bring"), var("s")), var("o")))), verb_number=number)
        add(word, "((S\\NP)/PP)/NP",
            lam("o", lam("r", lam("s", app(app(app(const("bring_to"), var("s")), var("o")), var("r"))))),
            verb_number=number)
    for word in ("hurt", "injured", "suspected", "embarrassed", "disguised", "hated", "doubted"):
        add(word, "(S\\NP)/NP",
            lam("o", lam("s", app(app(const(word), var("s")), var("o")))))
    for word, number in (("himself", "sg"), ("themselves", "pl")):
        # Reflexive interpretation is completed with the local subject below.
        add(word, "NP", const("local_reflexive"), reflexive_number=number)
    return result


def check_number(controller, requirement, mechanism, enabled):
    actual = features.nominal_description(number=controller.number, person="3")
    expected = features.nominal_description(number=requirement, person="3")
    try:
        unified = features.unify(actual, expected, TYPES).canonical()
        passes = True
    except features.UnificationError:
        unified, passes = None, False
    return {"mechanism": mechanism, "controller": controller.to_dict(),
            "required_number": requirement, "enabled": enabled, "passes": passes,
            "actual": actual.canonical(), "required": expected.canonical(), "unified": unified}


def combine(left, right, mode):
    agreement, binding, controller_mode = MODES[mode]
    answers, rejected = [], []
    for core in ccg.combine(left.core, right.core, composition=False):
        checks = left.checks + right.checks
        nominal = None
        if core.category in {N, NP}:
            # Backward NP modification preserves the head on its left.
            nominal = left.nominal if core.rule == "<" else right.nominal
        verb_number = left.verb_number or right.verb_number
        reflexive_number = left.reflexive_number or right.reflexive_number
        last = right.last_nominal or left.last_nominal
        if left.core.category == NP and right.core.category == VP and core.category == S:
            controller = left.nominal if controller_mode == "head" else left.last_nominal
            if controller is None:
                continue
            new_checks = []
            if right.verb_number:
                new_checks.append(check_number(controller, right.verb_number, "subject_verb", agreement))
            if right.reflexive_number:
                new_checks.append(check_number(controller, right.reflexive_number, "local_reflexive", binding))
            checks += tuple(new_checks)
            if any(c["enabled"] and not c["passes"] for c in new_checks):
                rejected.append({"words": core.words, "checks": list(checks),
                                 "subject_head": left.nominal.to_dict(),
                                 "unconstrained_derivation": core.to_dict()})
                continue
            if right.reflexive_number:
                # This fragment has one local reflexive object. Bind its
                # interpretation structurally to the subject, in every mode.
                from dylan.hybrid.terms import Term, normalize

                def bind(term):
                    if term.kind == "const" and term.name == "local_reflexive":
                        return left.core.meaning
                    return Term(term.kind, term.name, tuple(bind(a) for a in term.children))
                core = replace(core, meaning=normalize(bind(core.meaning)))
        answers.append(Sign(core, nominal, last, verb_number, reflexive_number, checks))
    return answers, rejected


class FeatureEngine:
    def __init__(self, identifier):
        if identifier not in MODES:
            raise ValueError("Unknown feature configuration")
        self.identifier, self.vocabulary = identifier, lexicon()

    def analyse(self, observation, *, trace=True):
        words = (observation.left_context + " " + observation.text).lower().split()
        vocabulary_hash = digest({" ".join(k): [s.to_dict() for s in v] for k, v in self.vocabulary.items()})
        provenance = {
            "lexicon_sha256": vocabulary_hash,
            "implementation_sha256": digest([Path(__file__).read_text(), Path(ccg.__file__).read_text(),
                                             Path(features.__file__).read_text()]),
            "mode": self.identifier, "cell_cap": CAP, "max_words": MAX_WORDS,
            "tokenization": "lowercase whitespace; multiword lexical entries use observed spans only",
            "scope": "Application-only CCG plus local number constraints; contextual masculine reference",
            "cue_contract": "Rule/category tuples from retained complete CCG derivations; no fitted memory claim",
            "analyses": [], "rejections": [],
        }
        if len(words) > MAX_WORDS:
            return Analysis(self.identifier, observation, "unsupported_length", False, False, provenance=provenance)
        known = {word for phrase in self.vocabulary for word in phrase}
        unknown = [{"word": w, "index": i} for i, w in enumerate(words) if w not in known]
        if unknown:
            provenance["failure"] = unknown
            return Analysis(self.identifier, observation, "unsupported_lexicon", False, False, provenance=provenance)
        cells, frames, limited, attempts, root_rejections = {}, [], False, 0, []
        for end in range(1, len(words) + 1):
            current_rejections = []
            for start in range(end - 1, -1, -1):
                answers = {s.key(): s for s in self.vocabulary.get(tuple(words[start:end]), [])}
                for split in range(start + 1, end):
                    for left in cells[start, split]:
                        for right in cells[split, end]:
                            attempts += 1
                            combined, rejected = combine(left, right, self.identifier)
                            if start == 0:
                                current_rejections.extend(rejected)
                            for sign in combined:
                                if sign.key() in answers or len(answers) < CAP:
                                    answers[sign.key()] = sign
                                else:
                                    limited = True
                cells[start, end] = list(answers.values())
            root_rejections = current_rejections
            if trace:
                frames.append({"index": end - 1, "word": words[end - 1],
                               "observed": words[:end],
                               "categories": sorted({str(s.core.category) for s in cells[0, end]}),
                               "heads": [s.nominal.to_dict() for s in cells[0, end] if s.nominal],
                               "rejected_constraints": current_rejections})
        roots = cells[0, len(words)]
        complete = [s for s in roots if s.core.category == S]
        supported = complete or (roots if observation.task == "fragment" else [])
        status = "complete" if complete else "recognized_fragment" if supported else (
            "constraint_rejection" if root_rejections else "unsupported_structure")
        if limited:
            status, supported, complete = "search_limit", [], []
        provenance["analyses"] = [s.to_dict() for s in complete] if trace else []
        provenance["rejections"] = root_rejections
        provenance["diagnostic_coverage"] = status in {"complete", "constraint_rejection"}
        return Analysis(self.identifier, observation, status, bool(supported), bool(complete),
                        cues=structural_cues([s.core for s in supported]),
                        meanings=tuple(sorted({str(s.core.meaning) for s in complete})), states=frames,
                        counters={"combination_attempts": attempts, "chart_cells": len(cells)},
                        provenance=provenance)

    def close(self):
        pass


def register():
    from dylan.experiments.registry import GRAMMARS, register_grammar

    for identifier in MODES:
        if identifier not in GRAMMARS:
            register_grammar(identifier, {
                "family": "CCG + typed features", "language": "en",
                "role": "hybrid" if identifier == "ccg-feature-head-v1" else "ablation",
                "processing": "incremental application chart; local typed number constraints",
                "semantics": "lambda terms; local reflexive bound to subject",
                "reference": "literature-diagnostic-v1; source-informed development fragment",
                "max_words": MAX_WORDS,
            }, FeatureEngine)
