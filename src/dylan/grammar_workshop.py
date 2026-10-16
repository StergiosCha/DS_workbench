"""Editable, reusable personal grammar packs and model-free contribution checks."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import time

from dylan.decision.gates import grammar_hash
from dylan.experimental_grammar import GRAMMARS, compile_proposal
from dylan.lexical_expansion import expand
from dylan.nlp.types import utterance_from_text

NOTICE = "Personal grammar: DS checks the displayed rules, including your edits. Saving or passing examples does not make them part of the shared reviewed grammar."
FIELDS = {
    "version",
    "name",
    "grammar",
    "base_hash",
    "seed_sentence",
    "proposal",
    "notes",
    "tests",
    "origin",
}


def tokens(sentence):
    return [w.word for w in utterance_from_text("Dylan", sentence).words]


def sentence_check(sentence):
    if (
        not isinstance(sentence, str)
        or not sentence.strip()
        or len(sentence) > 500
        or len(tokens(sentence)) > 40
    ):
        raise ValueError("Each grammar-pack example needs 1–40 tokens and at most 500 characters.")


def validate_pack(pack):
    if (
        not isinstance(pack, dict)
        or set(pack) != FIELDS
        or type(pack["version"]) is not int
        or pack["version"] != 1
    ):
        raise ValueError(
            "Expected a version 1 DS grammar pack with its name, grammar, base hash, seed sentence, proposal, notes, tests and origin."
        )
    if len(json.dumps(pack, ensure_ascii=False).encode()) > 24000:
        raise ValueError("A personal grammar pack must be at most 24 KB.")
    if not isinstance(pack["name"], str) or not 1 <= len(pack["name"].strip()) <= 80:
        raise ValueError("Give the grammar pack a name of 1–80 characters.")
    if not isinstance(pack["grammar"], str) or pack["grammar"] not in GRAMMARS:
        raise ValueError(
            "Personal rules support native English and Standard Greek Classical/Constructive grammars."
        )
    if not isinstance(pack["base_hash"], str) or not re.fullmatch(
        r"[a-f0-9]{64}", pack["base_hash"]
    ):
        raise ValueError("The grammar pack needs its original grammar hash.")
    if pack["base_hash"] != grammar_hash(pack["grammar"]):
        raise ValueError(
            "The base grammar has changed. Review and rebase this pack before applying it."
        )
    sentence_check(pack["seed_sentence"])
    if not isinstance(pack["notes"], str) or len(pack["notes"]) > 4000:
        raise ValueError("Keep review notes within 4000 characters.")
    origin = pack["origin"]
    if (
        not isinstance(origin, dict)
        or set(origin) != {"model", "proposal_hash"}
        or any(not isinstance(v, str) or len(v) > 160 for v in origin.values())
    ):
        raise ValueError(
            "Origin records the model and original proposal hash as text; it is provenance, not a review certificate."
        )
    if (
        not isinstance(pack["proposal"], dict)
        or set(pack["proposal"]) != {"declarations", "rules"}
        or not isinstance(pack["proposal"]["rules"], list)
        or not pack["proposal"]["rules"]
    ):
        raise ValueError("A pack needs declarations and at least one lexical rule.")
    if not isinstance(pack["tests"], list) or len(pack["tests"]) > 8:
        raise ValueError("Use up to eight regression examples per pack.")
    for example in pack["tests"]:
        if (
            not isinstance(example, dict)
            or set(example) != {"sentence", "complete", "meaning"}
            or type(example["complete"]) is not bool
        ):
            raise ValueError(
                "Each example needs sentence, complete (true/false) and meaning (text, or empty)."
            )
        sentence_check(example["sentence"])
        if (
            not isinstance(example["meaning"], str)
            or len(example["meaning"]) > 1500
            or (not example["complete"] and example["meaning"])
        ):
            raise ValueError("Expected meanings are optional text for positive examples only.")
    return pack


def digest(pack):
    return hashlib.sha256(json.dumps(pack, sort_keys=True).encode()).hexdigest()


def validate_options(payload):
    if type(payload.get("grammar_pack_check", False)) is not bool:
        raise ValueError("grammar_pack_check must be boolean.")
    if "grammar_pack" not in payload:
        if payload.get("grammar_pack_check"):
            raise ValueError("Choose a grammar pack to check.")
        return
    pack = validate_pack(payload["grammar_pack"])
    if payload.get("grammar") != pack["grammar"] or "paragraph" in payload or "dialogue" in payload:
        raise ValueError(
            "A personal grammar pack applies only to sentences in its own grammar/backend."
        )
    if (
        payload.get("experimental_rules")
        or payload.get("compare_jev")
        or payload.get("decision_mode", "off") != "off"
        or payload.get("lexical_mode", "off") not in {"off", "bundled", "dictionary", "corpus"}
        or payload.get("allow_model_fallback") is not False
    ):
        raise ValueError(
            "Personal grammar replay and review require all AI off; no new model requests are needed."
        )
    if payload.get("n_best", 1) != 1:
        raise ValueError("Personal grammar replay currently returns one analysis.")


def prepare(parser, pack, words):
    # Retain the dictionary declarations on which a generated program depended,
    # even when its original example is no longer the current input. These are
    # vocabulary seeds only; they do not supply discourse context or input words.
    seed = list(dict.fromkeys(tokens(pack["seed_sentence"]) + list(words)))
    mode = "dictionary" if "english" in pack["grammar"] else "corpus"
    report = expand(parser, pack["grammar"], seed, mode, allow_model_fallback=False)
    surfaces = [r.get("surface") for r in pack["proposal"]["rules"] if isinstance(r, dict)]
    compiled, theory = compile_proposal(pack["proposal"], parser, surfaces)
    return report, compiled, theory


def parse_pack(payload, on_event=None, *, trace="actions", seconds=8):
    from dylan.workbench_api import parse_request
    from dylan.paragraph_workbench import time_budget

    validate_options(payload)
    pack = payload["grammar_pack"]
    started = time.monotonic()
    plain = {k: v for k, v in payload.items() if k not in {"grammar_pack", "grammar_pack_check"}}
    plain.update(
        top_n=0,
        strict=True,
        n_best=1,
        reading_traces=False,
        lexical_mode="dictionary" if "english" in pack["grammar"] else "corpus",
    )
    records = []
    with time_budget(seconds):
        baseline = parse_request(plain, _trace=False)
        blocked = bool(
            baseline.get("failure")
            and baseline["failure"]["kind"] in {"pcc_violation", "constraint_violation"}
        )

        def setup(parser):
            report, compiled, theory = prepare(parser, pack, tokens(payload["sentence"]))
            parser.semantic_profile = theory
            for record, action in reversed(compiled):
                record = {
                    **record,
                    "source": "personal",
                    "morphology": "User-saved rule; inspect program",
                    "pack_hash": digest(pack),
                }
                action.metadata = record
                parser.lexicon.setdefault(record["surface"], []).insert(0, action)
                records.insert(0, record)
            parser.lexicon.invalidate_vocab_cache()
            report["entries"] += records
            report["remaining"] = [
                w for w in tokens(payload["sentence"]) if w not in parser.lexicon
            ]
            return report

        result = baseline if blocked else parse_request(plain, on_event, _setup=setup, _trace=trace)
    result["personal_grammar"] = {
        "name": pack["name"],
        "pack_hash": digest(pack),
        "pack": deepcopy(pack),
        "rules": records,
        "applied": not blocked,
        "blocked_by_reviewed_constraint": blocked,
        "notice": NOTICE,
        "selected_rule_ids": [
            r["rule_id"]
            for r in records
            if "experimental:" + r["rule_id"] in result.get("templates", [])
        ],
        "baseline": {
            "complete": baseline["complete"],
            "failure": baseline["failure"],
            "meaning": baseline["words"][-1].get("normalized"),
        },
    }
    result["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return result


def check_pack(pack):
    from dynamicsyntax import icp
    from dylan.paragraph_workbench import SentenceDeadline

    validate_pack(pack)
    parser = icp(pack["grammar"], strict=True, top_n=0)
    try:
        prepare(parser, pack, [])
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {
            "pack_hash": digest(pack),
            "compiles": False,
            "message": str(exc),
            "cases": [],
            "all_matched": False,
            "model_requests": 0,
        }
    finally:
        parser.close()
    rows = []
    for example in pack["tests"]:
        try:
            result = parse_pack(
                {
                    "sentence": example["sentence"],
                    "grammar": pack["grammar"],
                    "grammar_pack": pack,
                    "allow_model_fallback": False,
                    "lexical_mode": "off",
                },
                trace=False,
                seconds=5,
            )
            meaning = result["words"][-1].get("normalized")
            failure = result.get("failure")
            known = all(w["known"] for w in result["diagnostics"]["lexical_coverage"])
            limited = failure and failure["kind"] == "search_limit"
            matches = result["complete"] == example["complete"] and (
                not example["meaning"] or example["meaning"] == meaning
            )
            status = (
                "inconclusive"
                if limited or (not example["complete"] and not known)
                else "matched"
                if matches
                else "mismatch"
            )
            rows.append(
                {
                    "example": example,
                    "status": status,
                    "complete": result["complete"],
                    "meaning": meaning,
                    "failure": failure,
                    "all_tokens_known": known,
                    "selected_rule_ids": result["personal_grammar"]["selected_rule_ids"],
                }
            )
        except (ValueError, TypeError, KeyError, AttributeError, SentenceDeadline) as exc:
            rows.append(
                {
                    "example": example,
                    "status": "inconclusive",
                    "message": str(exc) or "Parser deadline reached.",
                }
            )
    return {
        "pack_hash": digest(pack),
        "compiles": True,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "cases": rows,
        "all_matched": bool(rows) and all(r["status"] == "matched" for r in rows),
        "has_positive": any(t["complete"] for t in pack["tests"]),
        "has_negative": any(not t["complete"] for t in pack["tests"]),
        "has_expected_meaning": any(t["meaning"] for t in pack["tests"]),
        "model_requests": 0,
        "notice": "These are your supplied regression expectations, not independent grammaticality judgments. A negative case with unknown words or a search limit is inconclusive.",
    }


def export_grammar(pack, output):
    """Materialize a new standalone grammar directory for review, never overwrite."""
    from dynamicsyntax import icp, parse
    from dynamicsyntax._session import resolved_grammar_path
    from dylan.paragraph_workbench import time_budget

    report = check_pack(pack)
    if not (report["all_matched"] and report["has_positive"] and report["has_negative"]):
        raise ValueError(
            "Before building a contribution, supply passing positive and negative examples; inspect inconclusive cases."
        )
    output = Path(output)
    if output.exists():
        raise ValueError("Choose a new output directory; existing grammars are never overwritten.")
    parser = icp(pack["grammar"], strict=True, top_n=0)
    try:
        words = [w for t in pack["tests"] for w in tokens(t["sentence"])]
        _, compiled, theory = prepare(parser, pack, words)
        with resolved_grammar_path(pack["grammar"]) as source:
            shutil.copytree(source, output)
        originals = icp(pack["grammar"], strict=True, top_n=0)
        try:
            support = [
                (word, action)
                for word, actions in parser.lexicon.items()
                for action in actions[len(originals.lexicon.get(word, [])) :]
            ]
        finally:
            originals.close()
        prefix = "personal_" + digest(pack)[:12]
        actions_text, front_rows, support_rows = [], [], []
        for i, (word, action, personal) in enumerate(
            [(r["surface"], a, True) for r, a in compiled] + [(w, a, False) for w, a in support]
        ):
            name = f"{prefix}_{i}"
            actions_text.append(name + "(UNUSED)\n" + "\n".join(action._source_lines) + "\n")
            (front_rows if personal else support_rows).append(f"{word} {name} none")
        actions_path = output / "lexical-actions.txt"
        actions_path.write_text(
            actions_path.read_text()
            + "\n\n// Personal grammar contribution; pending shared review.\n"
            + "\n".join(actions_text)
        )
        lexicon_path = output / "lexicon.txt"
        lexicon_path.write_text(
            "\n".join(front_rows)
            + "\n"
            + lexicon_path.read_text()
            + "\n"
            + "\n".join(support_rows)
            + "\n"
        )
        (output / "semantics.json").write_text(
            json.dumps(theory, ensure_ascii=False, indent=2) + "\n"
        )
        # Check the actual serialized grammar, not just its in-memory overlay.
        standalone = []
        for example in pack["tests"]:
            with time_budget(5):
                result = parse(example["sentence"], output, strict=True, top_n=0)
            complete = bool(result.ok and result.tree and result.tree.is_complete())
            meaning = str(result.semantics) if result.semantics is not None else None
            if (
                result.cap_hit
                or complete != example["complete"]
                or (example["meaning"] and example["meaning"] != meaning)
            ):
                raise ValueError(
                    "The serialized grammar failed a regression check; inspect the output before using it."
                )
            standalone.append(
                {"sentence": example["sentence"], "complete": complete, "meaning": meaning}
            )
        report["standalone"] = standalone
        (output / "grammar-pack.json").write_text(
            json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
        )
        (output / "review-results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        return report
    finally:
        parser.close()
