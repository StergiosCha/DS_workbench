"""Template-constrained vocabulary expansion for the two native English grammars.

Validation licenses a template instantiation, not the truth of a lexical analysis.
Neither model output nor a successful derivation is a grammaticality judgment.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3

from dylan import lexical_provider
from dylan.clause_inventory import CONNECTIVES

VERSION = 7
GRAMMARS = {"2026-english-classical", "2026-english-mltt"}
TEMPLATES = {
    "proper": {"arity": 1, "morphology": "invariant", "description": "Name with a nominal sort"},
    "noun": {
        "arity": 1,
        "morphology": "singular",
        "description": "Singular count noun; domain = parent sort",
    },
    "plural-noun": {
        "arity": 1, "morphology": "plural",
        "description": "Plural count-noun form supplying the individual restrictor of distributive all; domain = singular lemma's parent sort. Does not license bare plurals or collective readings.",
    },
    "adjective": {
        "arity": 1,
        "morphology": "invariant",
        "description": "Intersective adjective on object",
    },
    "predicative-adjective": {
        "arity": 1, "morphology": "invariant",
        "description": "Predicative property on object; no attributive/intersective reading is licensed",
    },
    "intransitive": {
        "arity": 1,
        "morphology": "finite",
        "description": "Active finite verb; subject domain",
    },
    "transitive": {
        "arity": 2,
        "morphology": "finite",
        "description": "Active finite verb; subject and direct-object domains",
    },
    "clausal": {
        "arity": 1,
        "morphology": "finite",
        "description": "Active finite verb selecting a finite clause (with optional that); domain = subject sort. Content argument is supplied by the template.",
    },
    "ditransitive": {
        "arity": 3, "morphology": "finite",
        "description": "Give frame with two DPs: giver, recipient, theme; e.g. gives Mary a book.",
    },
    "dative-to": {
        "arity": 3, "morphology": "finite",
        "description": "Give frame with a theme DP and obligatory to-recipient; domains remain giver, recipient, theme.",
    },
    "prepositional-on": {
        "arity": 2, "morphology": "finite",
        "description": "Verb selecting an obligatory on + DP complement; domains = subject, complement. Requires lexical evidence for on, e.g. relies on Mary.",
    },
    "prepositional-to": {
        "arity": 2, "morphology": "finite",
        "description": "Motion verb selecting a to + destination DP; domains = subject, destination. Requires lexical evidence, e.g. goes to the park. Not a recipient, infinitival to or arbitrary location adjunct.",
    },
    "prepositional-into": {
        "arity": 2, "morphology": "finite",
        "description": "Motion verb selecting an into + destination DP; domains = subject, destination. Use only for supported motion readings. Optional into/onto/toward path modifiers have separate LINK rules.",
    },
}
# Content-word expansion cannot instantiate closed-class programs. The separate
# construction interface selects reviewed finite-clause templates.
PROTECTED = set(
    """
a an the some any no not every each all most many few several both either neither
this that these those such what which who whom whose when where why how whatever
i me my mine myself we us our ours ourselves you your yours yourself yourselves
he him his himself she her hers herself it its itself they them their theirs themselves
there here one ones something anything nothing everything someone anyone everyone nobody
am is are was were be been being do does did done doing have has had having
can could may might must shall should will would ought need dare used
and or but nor yet so if whether because although though while unless until since
as than then therefore however also too only even just again already ever never
to of in on at for from with by about into onto upon over under through between
among before after during without within across against around toward towards out off up down
yes yeah yep no nope okay ok please hello hi thanks goodbye
sorry oops pardon wait
τον το την του της τους τις τα να δεν εν ci aton ato
""".split()
)
PROTECTED.update(CONNECTIVES["en"])
RESERVED = set(
    """
prop type set cn e t entity top unit true false i lam pi sigma arrow app fst snd pair meaning
and or not implies eps tau iota choice_eps choice_tau choice_iota definite cn_body cn_var predication refine exists forall fun fix cofix
let in match with end return as if then else where record parameter definition check
object quickly x y z a b c p q v u s r
""".split()
)
SYMBOL = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
SURFACE = re.compile(r"[a-z][a-z-]{0,39}\Z")
FIELDS = {"surface", "lemma", "template", "symbol", "domains", "morphology", "evidence"}


def proposal(
    surface, lemma, template, domains, *, symbol=None, evidence="Bundled lexical extension"
):
    return {
        "surface": surface,
        "lemma": lemma,
        "template": template,
        "symbol": symbol or lemma,
        "domains": domains,
        "morphology": TEMPLATES[template]["morphology"],
        "evidence": evidence,
    }


def bundled_entries() -> dict[str, list[dict]]:
    """An explicit inflection table, not suffix guessing or a hidden model substitute."""
    entries = []
    for lemma, parent in [
        ("cat", "animal"),
        ("child", "human"),
        ("teacher", "human"),
        ("student", "human"),
        ("book", "object"),
        ("letter", "object"),
    ]:
        entries.append(proposal(lemma, lemma, "noun", [parent]))
    for lemma, forms, domains in [
        ("sleep", "sleep sleeps slept", ["animal"]),
        ("run", "run runs ran", ["animal"]),
        ("laugh", "laugh laughs laughed", ["human"]),
        ("smile", "smile smiles smiled", ["human"]),
        ("greet", "greet greets greeted", ["human", "human"]),
        ("admire", "admire admires admired", ["human", "object"]),
        ("read", "read reads", ["human", "object"]),
        ("write", "write writes wrote", ["human", "object"]),
        ("see", "see sees saw", ["animal", "object"]),
    ]:
        template = "intransitive" if len(domains) == 1 else "transitive"
        entries.extend(proposal(form, lemma, template, domains) for form in forms.split())
    entries += [
        proposal("alice", "alice", "proper", ["human"]),
        proposal("red", "red", "adjective", ["object"]),
    ]
    result = {}
    for entry in entries:
        result.setdefault(entry["surface"], []).append(entry)
    return result


def configuration() -> dict:
    from dylan.lexical_dictionary import configuration as dictionary_configuration
    from dylan.lexical_selection import configuration as selection_configuration
    from dylan.greek_lexical_dictionary import configuration as greek_configuration
    from dylan.greek_lexical_evidence import configuration as evidence_configuration

    return {
        "grammars": sorted(GRAMMARS | set(greek_configuration()["grammars"])),
        "greek_corpus": greek_configuration(),
        "greek_sources": evidence_configuration(),
        "templates": TEMPLATES,
        "provider": lexical_provider.configuration(),
        "dictionary": dictionary_configuration(),
        "selection": selection_configuration(),
        "examples": ["a cat sleeps.", "every teacher greets a child.", "mary reads a book."],
        "coverage": "English names, singular count nouns, distributive all + plural nouns (including all the), intersective adjectives and active verbs: intransitive, transitive, give frames, finite clauses or a selected on-complement. Plural restrictors denote individuals; bare plurals and collective readings remain unsupported. Morphology is recorded; tense, full agreement and a/an phonology are not enforced by this fragment.",
    }


def validate_options(payload: dict) -> None:
    from dylan.jev_comparison import validate_options as validate_comparison
    validate_comparison(payload)
    from dylan.greek_lexical_evidence import validate_options as validate_sources
    validate_sources(payload)
    if payload.get("lexical_mode", "off") not in ("off", "bundled", "dictionary", "model", "jev", "corpus", "assisted"):
        raise ValueError("Choose off, bundled, dictionary, corpus, model, assisted or jev lexical expansion.")


def schema(profile: dict | None = None) -> dict:
    fields = {key: {"type": "string"} for key in FIELDS - {"domains"}}
    fields["template"]["enum"] = list(TEMPLATES)
    fields["morphology"]["enum"] = ["finite", "singular", "plural", "invariant"]
    fields["domains"] = {"type": "array", "items": {"type": "string"}}
    if profile is not None:
        fields["domains"]["items"]["enum"] = sorted({"object", *profile["subtyping"]})
    return {
        "type": "object",
        "properties": {
            "entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": fields,
                    "required": sorted(FIELDS),
                    "additionalProperties": False,
                },
            }
        },
        "required": ["entries"],
        "additionalProperties": False,
    }


def _identifier(value) -> bool:
    return (
        isinstance(value, str)
        and bool(SYMBOL.fullmatch(value))
        and value not in RESERVED
        and not re.fullmatch(r"[xyz][0-9]+", value)
        and not value.startswith(("mk_", "as_"))
    )


def validate_entries(
    raw, unknown: list[str], lexicon, profile: dict, controls=(), *, max_entries=24,
    max_analyses=3,
) -> tuple[list, dict]:
    """Validate and instantiate a whole batch before mutating either engine object."""
    if not isinstance(raw, dict) or set(raw) != {"entries"}:
        raise ValueError("Expected an object containing only entries.")
    entries = raw["entries"]
    if not isinstance(entries, list) or len(entries) > max_entries:
        raise ValueError(f"At most {max_entries} lexical analyses may be proposed.")
    theory = deepcopy(profile)
    counts, signatures = Counter(), set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ValueError("A lexical analysis has missing or unexpected fields.")
        word, lemma, template = entry["surface"], entry["lemma"], entry["template"]
        if not isinstance(word, str) or not SURFACE.fullmatch(word) or word not in unknown:
            raise ValueError("Proposals must address requested English surface forms.")
        if word in lexicon or word in PROTECTED or word in controls:
            raise ValueError(f"Cannot replace an entry or extend a closed class: {word}.")
        if not isinstance(lemma, str) or not SURFACE.fullmatch(lemma) or lemma in PROTECTED:
            raise ValueError(f"Unsupported lemma for {word}.")
        if not isinstance(template, str) or template not in TEMPLATES:
            raise ValueError("Only approved open-class templates may be instantiated.")
        # Preserve lexical identity: sharing an action frame is not synonym
        # replacement. Check the regular finite -s forms without claiming to
        # implement a complete English morphological analyser.
        if template in {"proper", "noun", "adjective", "predicative-adjective"} and lemma != word:
            raise ValueError(
                f"The supported invariant/singular entry must preserve the lemma of {word}."
            )
        if template == "plural-noun":
            from dylan.lexical_dictionary import is_plural_of
            if not is_plural_of(word, lemma):
                raise ValueError(f"The plural {word} does not match the singular lemma {lemma}.")
        if TEMPLATES[template]["morphology"] == "finite" and word.endswith("s"):
            regular = {lemma, lemma + "s", lemma + "es"}
            if lemma.endswith("y"):
                regular.add(lemma[:-1] + "ies")
            if word not in regular:
                raise ValueError(f"The proposed lemma does not match the finite form {word}.")
        spec = TEMPLATES[template]
        domains = entry["domains"]
        if (
            not isinstance(domains, list)
            or len(domains) != spec["arity"]
            or any(not isinstance(d, str) or not SYMBOL.fullmatch(d) for d in domains)
        ):
            raise ValueError(f"Invalid argument domains for {word}.")
        if entry["morphology"] != spec["morphology"] or not _identifier(entry["symbol"]):
            raise ValueError(f"Unsupported morphology or semantic symbol for {word}.")
        stem = lemma.replace("-", "_")
        if entry["symbol"] != stem and not entry["symbol"].startswith(stem + "_"):
            raise ValueError(f"The semantic symbol must preserve the lemma of {word}.")
        if not isinstance(entry["evidence"], str) or not 1 <= len(entry["evidence"]) <= 300:
            raise ValueError("Each proposed analysis needs a short source explanation.")
        counts[word] += 1
        signature = (word, template, entry["symbol"], tuple(domains))
        if counts[word] > max_analyses or signature in signatures:
            raise ValueError(f"Use at most {max_analyses} distinct analyses per form.")
        signatures.add(signature)
    base_sorts = {"object", *theory["subtyping"]}
    # Nouns introduce sorts first, so verb signatures can mention a new noun sort.
    for entry in [e for e in entries if e["template"] in {"noun", "plural-noun"}]:
        symbol, parents = entry["symbol"], entry["domains"]
        if parents[0] not in base_sorts or symbol == parents[0]:
            raise ValueError("New noun sorts need an existing, distinct parent sort.")
        if symbol in theory["constants"] or symbol in theory["predicates"]:
            raise ValueError(f"Semantic symbol collision: {symbol}.")
        previous = theory["subtyping"].get(symbol)
        if previous is not None and previous != parents:
            raise ValueError(f"Cannot redefine nominal sort: {symbol}.")
        theory["subtyping"][symbol] = parents
    sorts = {"object", *theory["subtyping"]}
    compiled = []
    for entry in entries:
        symbol, domains, template = entry["symbol"], entry["domains"], entry["template"]
        if any(domain not in sorts for domain in domains):
            raise ValueError(f"Undeclared argument sort for {entry['surface']}.")
        if template not in {"noun", "plural-noun"}:
            namespace = "constants" if template == "proper" else "predicates"
            other = "predicates" if namespace == "constants" else "constants"
            value = domains[0] if template == "proper" else domains
            if template == "clausal":
                value = [*domains, "Content"]
            if symbol in sorts or symbol in theory[other]:
                raise ValueError(f"Semantic symbol collision: {symbol}.")
            if symbol in theory[namespace] and theory[namespace][symbol] != value:
                raise ValueError(f"Cannot redefine the signature of {symbol}.")
            if template in {"adjective", "predicative-adjective"} and domains != ["object"]:
                raise ValueError("The current adjective template requires the object domain.")
            theory[namespace][symbol] = value
        params = [symbol] if template in {"noun", "plural-noun", "adjective", "predicative-adjective"} else [symbol, *domains]
        program = template
        if TEMPLATES[template]["morphology"] == "finite" and entry["surface"] == entry["lemma"]:
            program += "-base"
            # Existing base forms require do-support; dictionary lemmas also
            # need their ordinary finite use when agreement is not enforced.
            action = lexicon.instantiate_template(entry["surface"], template, params)
            compiled.append((deepcopy(entry), action))
        action = lexicon.instantiate_template(entry["surface"], program, params)
        compiled.append((deepcopy(entry), action))
        if template == "plural-noun":
            action = lexicon.instantiate_template(entry["surface"], "contextual-plural-noun", params)
            compiled.append((deepcopy(entry), action))
        if template == "adjective":
            action = lexicon.instantiate_template(entry["surface"], "predicative-adjective", params)
            compiled.append((deepcopy(entry), action))
            action = lexicon.instantiate_template(entry["surface"], "plural-adjective", params)
            compiled.append((deepcopy(entry), action))
            action = lexicon.instantiate_template(entry["surface"], "contextual-plural-adjective", params)
            compiled.append((deepcopy(entry), action))
    return compiled, theory


def _install(parser, compiled, theory, provenance) -> list[dict]:
    records = []
    for entry, action in compiled:
        action.metadata = {key: entry[key] for key in ("lemma", "evidence", "morphology", "template", "symbol", "domains")}
        action.metadata.update({"source": provenance.get("source")})
        if "evidence_ids" in entry:
            action.metadata.update({k: entry[k] for k in ("evidence_ids", "evidence_method")})
        parser.lexicon.setdefault(entry["surface"], []).append(action)
        records.append(
            {
                **entry,
                **provenance,
                "program": list(action._source_lines),
                "validation": "Template, morphology, symbol and signature checks passed",
            }
        )
    parser.lexicon.invalidate_vocab_cache()
    parser.semantic_profile = theory
    return records


def _cache_path() -> Path:
    return Path(os.environ.get("DS_LEXICAL_CACHE", ".ds-workbench/lexical.sqlite3"))


def _cache(key: str, value: dict | None = None) -> dict | None:
    if os.environ.get("DS_EPHEMERAL_MODELS") == "1":
        return None
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=1) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS proposals (key TEXT PRIMARY KEY, data TEXT)")
        if value is not None:
            connection.execute(
                "INSERT OR REPLACE INTO proposals VALUES (?, ?)", (key, json.dumps(value))
            )
            # Bound the experimental cache; entries are expendable proposal records.
            connection.execute(
                "DELETE FROM proposals WHERE rowid NOT IN (SELECT rowid FROM proposals ORDER BY rowid DESC LIMIT 500)"
            )
            return None
        row = connection.execute("SELECT data FROM proposals WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None


def expand(
    parser, grammar: str, tokens: list[str], mode: str, *, controls=(), on_event=None,
    allow_model_fallback=True,
) -> dict:
    report = {"mode": mode, "status": "off", "entries": [], "notices": [], "remaining": [], "model_requests": 0}
    if mode == "off":
        return report
    if mode == "corpus":
        from dylan.greek_lexical_dictionary import GRAMMARS as GREEK, expand as expand_greek
        if grammar in GREEK:
            return expand_greek(parser, tokens, controls)
        report.update(status="unsupported", notices=["The corpus lexicon supports Standard Modern Greek."])
        return report
    if grammar not in GRAMMARS:
        report.update(
            status="unsupported",
            notices=[
                "Lexical expansion currently supports the native English grammars. This grammar uses its original lexicon."
            ],
        )
        return report
    unknown = list(
        dict.fromkeys(t for t in tokens if t not in parser.lexicon and t not in controls)
    )
    report["originally_missing"] = unknown
    if mode == "jev":
        from dylan.lexical_selection import prepare

        return prepare(parser, grammar, tokens, unknown, report, controls, allow_model_fallback=allow_model_fallback)
    bundled = bundled_entries()
    entries = [entry for word in unknown for entry in bundled.get(word, [])]
    compiled, theory = validate_entries(
        {"entries": entries},
        unknown,
        parser.lexicon,
        parser.semantic_profile,
        controls,
        max_entries=len(entries),
    )
    report["entries"] += _install(
        parser, compiled, theory, {"source": "bundled", "version": VERSION}
    )
    remaining = [word for word in unknown if word not in parser.lexicon]
    if mode == "dictionary":
        from dylan.lexical_dictionary import candidates, configuration as dictionary_configuration

        report["dictionary"] = dictionary_configuration()
        report["morphology"] = {}
        if not report["dictionary"]["installed"]:
            report["notices"].append("The optional WordNet dictionary is not installed.")
        for word in remaining:
            try:
                proposals, analyses = candidates(word)
                report["morphology"][word] = analyses
                compiled, theory = validate_entries(
                    {"entries": proposals}, [word], parser.lexicon, parser.semantic_profile,
                    controls, max_entries=len(proposals), max_analyses=len(proposals),
                )
                report["entries"] += _install(parser, compiled, theory, {
                    "source": "dictionary", "dictionary": report["dictionary"]["source"],
                })
            except (OSError, sqlite3.Error, ValueError) as exc:
                report["notices"].append(f"Dictionary proposals for {word} were unavailable: {exc}")
        report.update(status="dictionary", remaining=[word for word in unknown if word not in parser.lexicon])
        return report
    report.update(status="ready", remaining=remaining)
    candidates = [word for word in remaining if SURFACE.fullmatch(word) and word not in PROTECTED]
    if mode != "model" or not candidates:
        return report
    if len(candidates) > 8:
        report["notices"].append("Model expansion is limited to eight unknown forms per request.")
        report["status"] = "limited"
        return report
    if on_event:
        on_event({"event": "lexical", "message": "Resolving unknown words with lexical templates…"})
    config = lexical_provider.settings()
    # Context-specific proposals never become global lexical facts. The key also
    # invalidates on grammar/template/theory and provider changes.
    from dynamicsyntax._session import resolved_grammar_path

    with resolved_grammar_path(grammar) as root:
        fingerprint = {p.name: p.read_text() for p in Path(root).glob("*.txt")}
    context = {
        "tokens": tokens,
        "unknown": candidates,
        "templates": TEMPLATES,
        "allowed_domains": sorted({"object", *parser.semantic_profile["subtyping"]}),
        "theory": parser.semantic_profile,
    }
    key = hashlib.sha256(
        json.dumps(
            [VERSION, grammar, context, fingerprint, config["url"], config["model"]], sort_keys=True
        ).encode()
    ).hexdigest()
    try:
        cached = _cache(key)
    except (OSError, sqlite3.Error, ValueError):
        cached = None
        report["notices"].append("The proposal cache is unavailable; expansion can still run.")
    try:
        if cached:
            raw, provenance = cached["proposal"], cached["provenance"]
        else:
            report["model_requests"] += 1
            raw, provider = lexical_provider.propose(context, schema(parser.semantic_profile))
            provenance = {
                "source": "model",
                **provider,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        compiled, theory = validate_entries(
            raw, candidates, parser.lexicon, parser.semantic_profile, controls
        )
        report["entries"] += _install(
            parser, compiled, theory, {**provenance, "cached": bool(cached)}
        )
        if not cached:
            try:
                _cache(key, {"proposal": raw, "provenance": provenance})
            except (OSError, sqlite3.Error):
                report["notices"].append("Validated proposals could not be cached.")
        report["status"] = "cached" if cached else "proposed"
    except lexical_provider.ProposalUnavailable as exc:
        report["status"] = "unavailable"
        report["notices"].append(str(exc))
    except ValueError as exc:
        report["status"] = "rejected"
        report["rejected_proposals"] = raw
        report["notices"].append(
            f"Proposal batch rejected: {exc} None of its entries were installed."
        )
    except (KeyError, TypeError):
        report["status"] = "rejected"
        report["notices"].append(
            "The proposal batch failed validation; none of its entries were installed."
        )
    report["remaining"] = [word for word in unknown if word not in parser.lexicon]
    return report
