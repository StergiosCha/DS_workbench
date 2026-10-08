"""Cited examples and coverage metadata, separate from the executable grammars.

Judgments below annotate a bounded comparison corpus. They never license/reject
a parse. Other failed inputs receive no inferred grammaticality judgment.
"""

from functools import lru_cache
import json
from pathlib import Path

from dylan.nlp.types import whitespace_tokenize

SOURCE = {
    "id": "historical-chapter",
    "author": "Stergios Chatzikyriakidis",
    "title": "The Historical Development of the clitic systems of Standard Modern, Cypriot and Pontic Greek",
    "location": "Local chapter manuscript, Introduction and sections 2–5",
}

DIALECTS = {
    "smg": {
        "label": "Standard Modern Greek",
        "short": "Standard Greek",
        "gate": "[↓₁⁺]?Ty(x) ∨ Mood(Imp) ∨ Mood(Ger)",
        "explanation": "Finite indicatives take preverbal clitics. Imperatives and gerunds permit postverbal clitics in this fragment.",
    },
    "cypriot": {
        "label": "Cypriot Greek",
        "short": "Cypriot",
        "gate": "(PROCL ∧ [↓₁⁺]?Ty(x)) ∨ (¬PROCL ∧ ⟨↓₁⁺⟩Ty(x))",
        "explanation": "Enclisis in the bare finite clause; negation and na license proclisis. Fronting depends on parsing strategy and discourse, and is outside this fragment.",
    },
    "pontic": {
        "label": "Pontic Greek",
        "short": "Pontic",
        "gate": "⟨↓₁⁺⟩Ty(x)",
        "explanation": "The described Pontic system requires a parsed verb before the clitic, including under negation. This is not a claim about every Pontic/Romeyka variety.",
    },
    "grico": {
        "label": "Grico (Salentino Greek)",
        "short": "Grico",
        "gate": "[↓⁺]?∃x.Tn(x) ∨ (Mood(Imp) ∧ [↓₁⁺][↓₀]?Ty(x))",
        "explanation": "Genitives precede accusatives in the described Grico clusters, including imperatives. The imperative genitive gate requires object positions still to require a type.",
    },
}

# Sentences are illustrations of sourced placement patterns, not a claim that
# every adapted spelling/verb substitution is a verbatim historical citation.
CASES = [
    {
        "id": "smg-finite",
        "dialect": "smg",
        "environment": "finite",
        "sentence": "τον αγαπά.",
        "reverse": "αγαπά τον.",
        "ascii": "ton agapa.",
        "reverse_ascii": "agapa ton.",
        "gloss": "S/he loves him.",
        "explanation": "The indicative requires proclisis. After αγαπά the functor spine is typed, so [↓₁⁺]?Ty(x) fails; Mood(Imp) is absent.",
    },
    {
        "id": "smg-neg",
        "dialect": "smg",
        "environment": "negation",
        "sentence": "δεν τον ξέρω.",
        "reverse": "δεν ξέρω τον.",
        "ascii": "den ton ksero.",
        "reverse_ascii": "den ksero ton.",
        "gloss": "I do not know him.",
        "explanation": "Negation does not license indicative enclisis in Standard Greek. The clitic must precede the verb.",
    },
    {
        "id": "smg-imp",
        "dialect": "smg",
        "environment": "imperative",
        "sentence": "γράφε το!",
        "reverse": "το γράφε!",
        "ascii": "grafe to!",
        "reverse_ascii": "to grafe!",
        "gloss": "Write it!",
        "explanation": "The imperative requires enclisis. A preceding clitic has already built fixed nodes, so the imperative’s [↓⁺]?∃x.Tn(x) trigger fails.",
    },
    {
        "id": "smg-na",
        "dialect": "smg",
        "environment": "na",
        "sentence": "να το γράψει.",
        "reverse": "να γράψει το.",
        "ascii": "na to grapsi.",
        "reverse_ascii": "na grapsi to.",
        "gloss": "For him/her to write it.",
        "explanation": "Na clauses take preverbal clitics. The perfective nonpast γράψει is distinct from the imperative γράψε.",
    },
    {
        "id": "cg-finite",
        "dialect": "cypriot",
        "environment": "finite",
        "sentence": "ιξέρω τον.",
        "reverse": "τον ιξέρω.",
        "ascii": "iksero ton.",
        "reverse_ascii": "ton iksero.",
        "gloss": "I know him.",
        "explanation": "In this bare clause there is no proclitic trigger. The clitic requires the already typed verb spine; this excludes clause-initial τον in the modeled environment.",
    },
    {
        "id": "cg-neg",
        "dialect": "cypriot",
        "environment": "negation",
        "sentence": "εν τον ιξέρω.",
        "reverse": "εν ιξέρω τον.",
        "ascii": "en ton iksero.",
        "reverse_ascii": "en iksero ton.",
        "gloss": "I do not know him.",
        "explanation": "En licenses proclisis. Its PROCL feature blocks the enclitic branch, while the preverbal branch requires an untyped verb spine.",
    },
    {
        "id": "cg-imp",
        "dialect": "cypriot",
        "environment": "imperative",
        "sentence": "γράφε το!",
        "reverse": "το γράφε!",
        "ascii": "grafe to!",
        "reverse_ascii": "to grafe!",
        "gloss": "Write it!",
        "explanation": "With no proclitic trigger, the imperative precedes the clitic. The clitic can then inspect the typed verb spine.",
    },
    {
        "id": "cg-na",
        "dialect": "cypriot",
        "environment": "na",
        "sentence": "να το γράψει.",
        "reverse": "να γράψει το.",
        "ascii": "na to grapsi.",
        "reverse_ascii": "na grapsi to.",
        "gloss": "For him/her to write it.",
        "explanation": "Na licenses proclisis in this Cypriot fragment; postverbal placement is excluded in this environment.",
    },
    {
        "id": "pg-finite",
        "dialect": "pontic",
        "environment": "finite",
        "sentence": "ekser aton.",
        "reverse": "aton ekser.",
        "ascii": "εξέρ ατον.",
        "reverse_ascii": "ατον εξέρ.",
        "gloss": "I know him.",
        "explanation": "The Pontic clitic requires a typed functor spine: the verb must have parsed. Source transcription eksér aton; the demo offers ASCII and simplified Greek aliases.",
    },
    {
        "id": "pg-neg",
        "dialect": "pontic",
        "environment": "negation",
        "sentence": "ci kser aton.",
        "reverse": "ci aton kser.",
        "ascii": "κι ξέρ ατον.",
        "reverse_ascii": "κι ατον ξέρ.",
        "gloss": "I do not know him.",
        "explanation": "Unlike Cypriot en, Pontic ci does not switch placement to proclisis. The typed-spine requirement still forces the clitic after the verb.",
    },
    {
        "id": "grico-imp-cluster",
        "dialect": "grico",
        "environment": "imperative",
        "sentence": "do mu to.",
        "reverse": "do to mu.",
        "ascii": "do mu to.",
        "reverse_ascii": "do to mu.",
        "gloss": "Give it to me.",
        "nodes": 7,
        "explanation": "Grico permits genitive then accusative after the imperative. An accusative already gives the object a type, so the subsequent genitive fails the [↓₁⁺][↓₀]?Ty(x) condition.",
        "source": {
            "id": "chatzikyriakidis-thesis",
            "file": "chatzikyriakidis-phdthesis.pdf",
            "label": "(3.89)-(3.90), analysis (3.104)",
            "page": 132,
            "page_kind": "PDF page (1-based)",
        },
    },
]

COVERAGE = (
    "Small clitic fragment: third-person accusatives, pro-drop monotransitive verbs, "
    "negation; Standard/Cypriot also imperatives and na. Greek script and listed ASCII aliases. "
    "Context fixes speaker, hearer, pro, him and theme. Clusters/PCC, full DPs, fronting, "
    "doubling, relatives, auxiliaries and gerunds are not implemented here."
)

THESIS_COVERAGE = (
    "Maintained SMG and Grico fragments: person-sensitive accusatives and genitives, "
    "monotransitive and ditransitive verbs, imperative cluster order and strong PCC. "
    "Unfixed nodes, case filters, MERGE and SUBSTITUTION determine clitic combinations. "
    "SMG also has negation, na, future-particle and gerund entries. Coverage is limited to "
    "the reviewed lexicon. SMG case-marked names support SVO/VSO/OVS and structural "
    "clitic coreference. SMG also has singular accusative indefinite DPs and initial nominative "
    "proper-name topics linked to a clause with a matching referent. Common-noun definites, "
    "full discourse conditions, relatives and tense semantics remain pending. "
    "Plural references carry person and number but no collective/distributive distinction."
)

PONTIC_COVERAGE = (
    "Maintained Pontic fragment: postverbal clitics, negation, ditransitives and imperative "
    "templates. Coupled m ese(n) and m a entries build fixed and unfixed argument nodes. "
    "The weak-PCC pattern is reported for some speakers, not every Pontic variety. "
    "Coverage is limited to the reviewed forms; full DPs and tense semantics remain pending."
)

HISTORY = [
    {
        "id": "koine",
        "label": "Hellenistic / Roman Koine",
        "title": "Variable placement before categorical triggers",
        "evidence": "Koine evidence is not a uniform categorical second-position system. The chapter’s Oxyrhynchus table (after Pappas 2006:323) records both orders with adverbs, objects, subjects, PPs, complementizers and wh-expressions; clause-initial preverbal clitics are rare. These papyri do not stand for every period or register of Koine.",
        "analysis": "In Chatzikyriakidis’s DS proposal, the clitic initially needs only a ?Ty(t) node. Early placement can reduce the search for an anaphoric referent; the observed preferences need not all be lexical prohibitions. This is an analysis of the variation, not an uncontested absence of syntax.",
        "trigger": "?Ty(t) → clitic actions; preferences depend on discourse and processing",
        "counts": [
            ["Clause initial", 4, 231],
            ["Adverbs", 34, 14],
            ["NP object", 21, 15],
            ["NP subject", 10, 13],
            ["PP", 13, 37],
            ["Complementizers", 17, 37],
            ["Wh-expressions", 18, 16],
        ],
    },
    {
        "id": "mainland",
        "label": "Medieval mainland → Standard",
        "title": "Proclitic environments generalize",
        "evidence": "The chapter distinguishes medieval mainland, Cypriot and Pontic patterns. Mainland proclisis has spread across more environments; bare-clause enclisis is still available in the medieval system. Historical texts and counts are evidence about particular corpora, not categorical judgments for all speakers.",
        "analysis": "The proposed route is routinization: frequent choices become lexical parsing conditions. Unfixed-node and situation-node strategies first license proclisis. Speaker/hearer mismatches between unfixed and LINK analyses then expand the environments until a general ‘no verb parsed yet’ trigger emerges. Imperative/gerund enclisis survives in the modern system.",
        "trigger": "unfixed / situation triggers → [↓₁⁺]?Ty(x) ∨ Mood(Imp/Ger)",
    },
    {
        "id": "cyprus",
        "label": "Medieval Cypriot → Cypriot",
        "title": "A restricted strategy becomes more general",
        "evidence": "Medieval Cypriot has fewer generalized proclitic environments in this account. Modern Cypriot retains the contrast between default enclisis and proclitic triggers. Fronted constituents can pattern differently according to discourse/prosody and analysis; they should not be reduced to ‘any preceding word’.",
        "analysis": "The DS proposal broadens an unfixed-node trigger initially restricted to wh-elements to other fronted constituents, while preserving the distinction from LINK/topic strategies. Negation, modal particles and relevant subordination remain important. The executable demo currently models only negation and na among these triggers.",
        "trigger": "WH-specific unfixed trigger → general unfixed trigger; event-trigger and enclitic branches retained",
    },
    {
        "id": "pontus",
        "label": "Medieval Pontic → Pontic",
        "title": "The postverbal condition becomes general",
        "evidence": "Medieval Pontic evidence in the chapter is sparse and less amenable to a single generalized proclitic environment. The modern Pontic system described has postverbal clitics even under negation and wh-elements. Broader Pontic/Romeyka variation needs separately identified data.",
        "analysis": "The proposed change drops several item-specific proclitic conditions and retains the already general ‘verb parsed’ condition. This yields the opposite result from Standard Greek. Routinization is offered as one contributor; corpus gaps and possible regional Koine differences prevent treating this as a demonstrated single causal history.",
        "trigger": "item-specific proclitic disjunctions + enclisis → ⟨↓₁⁺⟩Ty(x)",
    },
]


def configuration():
    grammars = {}
    for dialect, info in DIALECTS.items():
        for backend in ("classical", "mltt"):
            grammars[f"2026-{dialect}-{backend}"] = {
                **info,
                "dialect": dialect,
                "backend": backend,
                "coverage": (THESIS_COVERAGE if dialect in {"smg", "grico"}
                             else PONTIC_COVERAGE if dialect == "pontic" else COVERAGE),
                "examples": [
                    {"sentence": c["sentence"], "label": c["gloss"]}
                    for c in CASES
                    if c["dialect"] == dialect
                ],
            }
            if dialect == "smg":
                grammars[f"2026-{dialect}-{backend}"]["examples"].extend([
                    {"sentence": "ο γιώργος περπατάει επειδή η μαρία περπατάει αργότερα.",
                     "label": "Finite causal LINK and temporal modifier; maintained extension"},
                    {"sentence": "όταν η μαρία περπατάει, ο γιώργος περπατάει.",
                     "label": "Finite temporal clause; maintained extension"},
                    {"sentence": "ο γιώργος περπατάει παρότι η μαρία περπατάει αργότερα.",
                     "label": "Finite concessive clause; maintained extension"},
                    {"sentence": "ο γιώργος, τον ξέρω.",
                     "label": "Hanging topic via LINK; verb adaptation of thesis (2.95)"},
                    {"sentence": "o γiorγos xtipise to γiani.",
                     "label": "Subject MERGE or topic LINK: request multiple complete analyses"},
                    {"sentence": "το διάβασα ένα βιβλίο.",
                     "label": "Indefinite DP and clitic; shortened adaptation of thesis (B.4)"},
                ])
    return {
        "grammars": grammars,
        "cases": CASES,
        "history": HISTORY,
        "source": SOURCE,
        "other_dialects": "Grico's reviewed cluster fragment is executable in both semantic modes. Cretan belongs to the default-enclisis/triggered-proclisis comparison group in the chapter and currently has no executable grammar.",
    }


@lru_cache(maxsize=4)
def _corpus_rows(path: str, mtime_ns: int):
    del mtime_ns
    return tuple(json.loads(line) for line in Path(path).read_text().splitlines() if line.strip())


def matched_corpus_case(grammar, tokens):
    from dylan.workbench_paths import data_path

    path = data_path("greek-clitics/corpus.jsonl")
    if not path.exists():
        return None
    def content(text):
        return [t for t in whitespace_tokenize(text) if t not in {".", "!", "?", ";", ";"}]
    clean = [t for t in tokens if t not in {".", "!", "?", ";", ";"}]
    matches = [row for row in _corpus_rows(str(path), path.stat().st_mtime_ns)
               if grammar in row.get("grammars", []) and row["judgment"].get("source")
               and row["judgment"]["status"] != "not_stated"
               and any(clean == content(row[key]) for key in ("surface", "ascii") if row.get(key))]
    if not matches:
        return None
    statuses = {row["judgment"]["status"] for row in matches}
    status = next(iter(statuses)) if len(statuses) == 1 else "conflicting_sources"
    first = matches[0]
    return {
        "case": first["id"], "corpus_ids": [row["id"] for row in matches],
        "status": {"licensed": "licensed_pattern", "starred": "excluded_in_described_variety",
                   "variable": "variable_in_described_variety"}.get(status, status),
        "source": first["judgment"]["source"],
        "explanation": f"The cited corpus records this input as {status}; parser outcomes do not determine that judgment.",
        "scope": first.get("notes", ""),
        "human_labels": first.get("human_labels"),
    }


def matched_case(grammar, tokens):
    info = configuration()["grammars"].get(grammar)
    if not info:
        return matched_corpus_case(grammar, tokens)
    clean = [t for t in tokens if t not in {".", "!", "?", ";", ";"}]
    for case in CASES:
        if case["dialect"] != info["dialect"]:
            continue
        for key in ("sentence", "ascii", "reverse", "reverse_ascii"):
            expected = [
                t for t in whitespace_tokenize(case[key]) if t not in {".", "!", "?", ";", ";"}
            ]
            if clean == expected:
                return {
                    "case": case["id"],
                    "status": "excluded_in_described_variety"
                    if key.startswith("reverse")
                    else "licensed_pattern",
                    "explanation": case["explanation"],
                    "source": case.get("source", SOURCE),
                    "scope": "Placement of weak object clitics in this stated environment; not a strong-pronoun reading.",
                }
    return matched_corpus_case(grammar, tokens)


def pcc_diagnostic(grammar, tokens, lexicon, failure):
    """Explain the clitic reading of an already failed genitive + acc12 cluster.

    This annotates a grammar failure; it neither licenses a parse nor assigns
    an independent judgment to the whole input. The genitive must be
    unambiguous; any non-clitic readings of the second word are distinguished.
    Grammars with different clitic systems are deliberately excluded.
    """
    if grammar not in {f"2026-{dialect}-{backend}" for dialect in ("smg", "grico")
                       for backend in ("classical", "mltt")}:
        return None
    index = failure["index"]
    if index < 1:
        return None
    before, current = lexicon.lookup(tokens[index - 1]), lexicon.lookup(tokens[index])
    if (not before or not current
            or any(a.action_type != "clitic-gen" for a in before)
            or not any(a.action_type == "clitic-acc12" for a in current)):
        return None
    other_readings = any(a.action_type != "clitic-acc12" for a in current)
    return {
        "kind": "pcc",
        "tokens": tokens[index - 1:index + 1],
        "explanation": (
            f"Person–Case Constraint (PCC), under the clitic reading: “{tokens[index - 1]}” is a genitive clitic and "
            f"“{tokens[index]}” is a first/second-person accusative clitic. "
            "In this grammar both target the same locally unfixed node, where their "
            "referent/case requirements clash. The cluster is blocked; the tree shown "
            "is only the prefix before the second clitic."
            + (" Other lexical readings of the second word also failed to extend this prefix; "
               "the PCC explanation applies to its clitic reading." if other_readings else "")
        ),
        "source": "Chatzikyriakidis (2010), chapter 6, especially the acc12 entry (6.49); implemented clitic-gen/clitic-acc12 templates.",
    }


def assessment(grammar, tokens, lexicon, failure, complete, *, controls=()):
    """Keep lexical coverage, parsing and linguistic evidence independently visible."""
    directory = getattr(lexicon, "_resource_dir", None)
    profile_path = Path(directory) / "semantics.json" if directory else None
    profile = json.loads(profile_path.read_text()) if profile_path and profile_path.exists() else {}
    coverage = [
        {
            "token": token,
            "index": index,
            "known": bool(lexicon.lookup(token)) or token in controls,
            "source": "parser_control" if token in controls else "lexicon",
        }
        for index, token in enumerate(tokens)
    ]
    judgment = matched_case(grammar, tokens) or {
        "status": "not_assessed",
        "explanation": "No independent grammaticality judgment is recorded for this input. Parser acceptance or failure alone is not such a judgment.",
    }
    constraint = None
    if failure:
        if failure.get("kind") == "search_limit":
            pass
        elif not coverage[failure["index"]]["known"]:
            failure["kind"] = "lexicon_gap"
        elif failure.get("kind") in {
            "semantic_type_mismatch",
            "missing_context",
            "repair_unavailable",
            "context_boundary",
        }:
            pass
        elif (constraint := pcc_diagnostic(grammar, tokens, lexicon, failure)):
            failure["kind"] = "pcc_violation"
            failure["message"] = constraint["explanation"]
        elif judgment["status"] == "excluded_in_described_variety":
            failure["kind"] = "constraint_violation"
            failure["message"] = judgment["explanation"]
        elif (
            profile.get("fragment") == "greek-clitics"
            and sum(any(a.action_type == "clitic" for a in lexicon.lookup(t)) for t in tokens) > 1
        ):
            failure["kind"] = "construction_gap"
            failure["message"] = (
                "This small Greek grammar covers a single object clitic. Clusters are outside its coverage; this is not a PCC or grammaticality judgment."
            )
        else:
            failure["kind"] = "unresolved_parse_failure"
            failure["message"] += (
                " No grammaticality judgment follows: the construction may be outside this grammar’s coverage."
            )
    return {
        "parse_status": "complete" if complete else "stopped" if failure else "incomplete",
        "lexical_coverage": coverage,
        "judgment": judgment,
        "grammar_constraint": constraint,
    }
