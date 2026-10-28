"""A bounded CCG: application, harmonic composition, optional forward type raising.

Lexicon and combinators are explicit. An empty result means no derivation in
this fragment, not impossibility in categorial grammar.
"""

from dataclasses import dataclass

from dylan.hybrid.terms import Term, app, const, lam, names, normalize, var


def fresh(base, *terms):
    used = set().union(*(names(term) for term in terms))
    while base in used:
        base += "_"
    return base


@dataclass(frozen=True)
class Category:
    atom: str = ""
    result: "Category | None" = None
    argument: "Category | None" = None
    slash: str = ""

    def __str__(self):
        return self.atom if self.atom else f"({self.result}{self.slash}{self.argument})"


def cat(text):
    text = text.strip()
    while text.startswith("(") and text.endswith(")"):
        depth, enclosed = 0, True
        for index, char in enumerate(text):
            depth += (char == "(") - (char == ")")
            if depth == 0 and index < len(text) - 1:
                enclosed = False
                break
        if not enclosed:
            break
        text = text[1:-1]
    depth = 0
    for index in range(len(text) - 1, -1, -1):
        char = text[index]
        depth += (char == ")") - (char == "(")
        if depth == 0 and char in {"/", "\\"}:
            return Category(result=cat(text[:index]), argument=cat(text[index + 1:]), slash=char)
    if not text or any(c in text for c in "()/\\"):
        raise ValueError(f"Invalid category {text}")
    return Category(atom=text)


def fun(result, argument, slash="/"):
    return Category(result=result, argument=argument, slash=slash)


@dataclass(frozen=True)
class Sign:
    category: Category
    meaning: Term
    words: tuple[str, ...]
    rule: str = "lexical"
    children: tuple["Sign", ...] = ()

    def to_dict(self):
        return {"category": str(self.category), "meaning": str(normalize(self.meaning)),
                "words": self.words, "rule": self.rule, "children": [c.to_dict() for c in self.children]}


def combine(left, right, *, composition=True):
    a, b = left.category, right.category
    answers = []
    z = fresh("z", left.meaning, right.meaning)
    if a.slash == "/" and a.argument == b:
        answers.append((a.result, app(left.meaning, right.meaning), ">"))
    if b.slash == "\\" and b.argument == a:
        answers.append((b.result, app(right.meaning, left.meaning), "<"))
    if composition and a.slash == b.slash == "/" and a.argument == b.result:
        answers.append((fun(a.result, b.argument), lam(z, app(left.meaning, app(right.meaning, var(z)))), ">B"))
    if composition and a.slash == b.slash == "\\" and b.argument == a.result:
        answers.append((fun(b.result, a.argument, "\\"), lam(z, app(right.meaning, app(left.meaning, var(z)))), "<B"))
    return [Sign(c, normalize(m), left.words + right.words, r, (left, right)) for c, m, r in answers]


def raise_np(sign, target=None):
    if sign.category != cat("NP"):
        raise ValueError("This fragment type-raises NP only")
    target = target or cat("S")
    f = fresh("f", sign.meaning)
    return Sign(fun(target, fun(target, cat("NP"), "\\")),
                lam(f, app(var(f), sign.meaning)), sign.words, ">T", (sign,))


def lexicon():
    data = {}

    def add(word, category, meaning=None):
        data.setdefault(word, []).append(Sign(cat(category), meaning or const(word), (word,)))

    for word in ["john", "mary", "you", "him", "it", "she", "we", "they"]:
        add(word, "NP")
    for word in ["book", "friend", "day", "story", "man", "woman", "time"]:
        add(word, "N")
    for word in ["his", "your", "her", "the", "a", "any"]:
        add(word, "NP/N", lam("n", app(const(word), var("n"))))
    for word in ["make", "read", "likes", "met", "know"]:
        add(word, "(S\\NP)/NP", lam("o", lam("s", app(app(const(word), var("s")), var("o")))))
    for word in ["walks", "sleeps"]:
        add(word, "S\\NP", lam("s", app(const(word), var("s"))))
    for word in ["will", "could", "must"]:
        add(word, "(S\\NP)/(S\\NP)", lam("v", app(const(word), var("v"))))
    for word in ["and", "or", "but"]:
        for category in ["NP", "N", "S", "S\\NP"]:
            c = cat(category)
            data.setdefault(word, []).append(Sign(fun(fun(c, c, "\\"), c),
                lam("r", lam("l", app(app(const(word), var("l")), var("r")))), (word,)))
    return data


def parse(text, *, vocabulary=None, composition=True, type_raising=False, cap=256):
    words = text.lower().split()
    if not words or len(words) > 12:
        raise ValueError("CCG fragment supports 1–12 words")
    vocabulary = vocabulary or lexicon()
    unknown = [w for w in words if w not in vocabulary]
    if unknown:
        return {"status": "unsupported_lexicon", "unknown": unknown, "analyses": []}
    chart, limited = {}, False
    for i, word in enumerate(words):
        entries = list(vocabulary[word])
        if type_raising:
            entries += [raise_np(s) for s in entries if s.category == cat("NP")]
        chart[i, i + 1] = entries
    for width in range(2, len(words) + 1):
        for start in range(len(words) - width + 1):
            end, answers = start + width, {}
            for split in range(start + 1, end):
                for left in chart[start, split]:
                    for right in chart[split, end]:
                        for sign in combine(left, right, composition=composition):
                            key = (str(sign.category), str(sign.meaning))
                            if key not in answers and len(answers) >= cap:
                                limited = True
                            else:
                                answers[key] = sign
            chart[start, end] = list(answers.values())
    analyses = chart[0, len(words)]
    return {"status": "search_limit" if limited else "derived" if analyses else "no_derivation_in_fragment",
            "analyses": [s.to_dict() for s in analyses],
            "config": {"composition": composition, "type_raising": type_raising, "cell_cap": cap}}
