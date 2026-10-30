"""Versioned, optional exports of native analyses for the LingEmbed viewer.

No shared syntactic ontology is imposed on grammar engines. The CCG adapter
replays recorded prefixes and checks their states before exporting derivations;
it never obtains earlier structures by pruning a completed sentence.
"""

from copy import deepcopy
from pathlib import Path

from dylan.experiments.contracts import digest

SCHEMA = "lingembed.analysis.v1"
MAX_ALTERNATIVES = 8


def ds_structure(state):
    addresses = {node["address"] for node in state["nodes"]}
    nodes, edges = [], []
    for native in state["nodes"]:
        address, labels = native["address"], native["labels"]
        types = [label for label in labels if label.startswith(("Ty(", "?Ty("))]
        meanings = [label for label in labels if label.startswith("Fo(")]
        nodes.append({"id": address, "label": address, "type": " · ".join(types),
                      "meaning": " · ".join(meanings), "labels": list(labels), "span": None})
        if address[:-1] in addresses:
            edges.append({"source": address[:-1], "target": address,
                          "role": address[-1], "order": None})
    return {"id": "selected-state", "kind": "ds-address-tree", "root": "0",
            "nodes": nodes, "edges": edges,
            "metadata": {"pointer": state["pointer"], "complete": state["complete"],
                         "alignment": "No lexical span inferred for semantic nodes",
                         "topology": "Stored addresses, including LINK and unfixed steps; not constituency"}}


def ccg_structure(sign, alternative):
    nodes, edges = [], []

    def visit(value, address, start):
        end = start + len(value["words"])
        nodes.append({"id": address, "label": value["category"], "type": value["category"],
                      "meaning": value["meaning"], "labels": [value["rule"]], "span": [start, end]})
        position = start
        for index, child in enumerate(value["children"]):
            child_id = f"{address}.{index}"
            edges.append({"source": address, "target": child_id, "role": value["rule"], "order": index})
            visit(child, child_id, position)
            position += len(child["words"])

    visit(sign, "r", 0)
    return {"id": f"derivation-{alternative}", "kind": "ccg-derivation", "root": "r",
            "nodes": nodes, "edges": edges,
            "metadata": {"words": list(sign["words"]), "alignment": "Half-open native token spans"}}


def _ccg_frames(analysis):
    # Lazy imports preserve the host's independent-engine boundary.
    from dylan.experiments.ccg_engine import CCGEngine, Chart
    from dylan.hybrid import ccg

    engine = CCGEngine(analysis["engine"])
    lexicon_hash = digest({word: [entry.to_dict() for entry in entries]
                          for word, entries in engine.vocabulary.items()})
    provenance = analysis["provenance"]
    implementation_hash = digest([Path(__file__).with_name("ccg_engine.py").read_text(),
                                  Path(ccg.__file__).read_text()])
    if implementation_hash != provenance.get("implementation_sha256"):
        raise ValueError("CCG export requires the recorded implementation version")
    if (lexicon_hash != provenance.get("lexicon_sha256")
            or engine.composition != provenance.get("composition")
            or engine.type_raising != provenance.get("type_raising")):
        raise ValueError("CCG export requires the recorded lexicon and combinator settings")
    chart = Chart(composition=engine.composition, type_raising=engine.type_raising)
    frames = []
    for recorded in analysis["states"]:
        if chart.state() != recorded["before"]:
            raise ValueError("CCG prefix replay does not match the recorded input state")
        word = recorded["word"]
        if word not in engine.vocabulary:
            raise ValueError("CCG trace contains an unrecorded lexical entry")
        chart.append(word, engine.vocabulary[word])
        if chart.state() != recorded["after"]:
            raise ValueError("CCG prefix replay does not match the recorded output state")
        alternatives = chart.analyses
        frames.append({"index": recorded["index"], "stage": "word", "word": word,
                       "context": recorded["context"], "accepted": True,
                       "observed": list(chart.words), "native_state": deepcopy(recorded["after"]),
                       "structures": [ccg_structure(sign.to_dict(), index)
                                      for index, sign in enumerate(alternatives[:MAX_ALTERNATIVES])],
                       "available_structures": len(alternatives),
                       "omitted_structures": max(0, len(alternatives) - MAX_ALTERNATIVES)})
    return frames


def export_analysis(value):
    """Return a display/encoding projection; retain completion and coverage limits."""
    analysis = value.to_dict() if hasattr(value, "to_dict") else value
    identifier = analysis["engine"]
    if identifier in {"ccg-original-v1", "ccg-incremental-v1", "ccg-application-v1"}:
        frames = _ccg_frames(analysis)
        projection = {
            "preserves": ["exported derivations: categories, normalized meaning strings, rules, token spans",
                          "recorded prefix chart summaries", "retained alternative counts"],
            "omits": ["derivations after the first eight per prefix", "non-full-span derivation trees",
                      "executable lambda-term objects"],
            "selection": "First retained derivations in native chart order; no probability or ranking implied",
            "verification": "Replayed each prefix against its recorded before/after chart state",
        }
    elif identifier in {"ds-english-v1", "ds-greek-v1", "ds-greek-poly-v1"}:
        frames = [{"index": frame["index"], "stage": "word", "word": frame["word"],
                   "context": frame["context"], "accepted": frame["accepted"],
                   "observed": list(frame["observed"]), "native_state": deepcopy(frame["after"]),
                   "structures": [ds_structure(frame["after"])],
                   "available_structures": 1, "omitted_structures": 0}
                  for frame in analysis["states"]]
        final = analysis["provenance"].get("native_state")
        if frames and final and final != frames[-1]["native_state"]:
            frames.append({"index": len(frames), "stage": "completion", "word": "",
                           "context": False, "accepted": None,
                           "observed": list(frames[-1]["observed"]), "native_state": deepcopy(final),
                           "structures": [ds_structure(final)],
                           "available_structures": 1, "omitted_structures": 0})
        projection = {
            "preserves": ["selected native tree: addresses, all label strings, pointer and pending requirements",
                          "recorded observed-word states", "separate post-input completion state when changed"],
            "omits": ["alternative search paths", "lexical action programs", "executable semantic objects"],
            "selection": "Native first-success path; semantic nodes have no invented word alignment",
            "verification": "Copied native snapshots; no reparse or future-state projection",
        }
    else:
        raise ValueError("No LingEmbed adapter for this grammar package")
    provenance = analysis["provenance"]
    fingerprints = {key: val for key, val in provenance.items() if key.endswith("sha256")}
    return {"schema": SCHEMA, "source": {"project": "DS Workbench", "engine": identifier,
            "adapter": "lingembed-export-v1", "adapter_sha256": digest(Path(__file__).read_text()),
            "analysis_sha256": digest(analysis), "fingerprints": fingerprints},
            "observation": deepcopy(analysis["observation"]), "status": analysis["status"],
            "supported": analysis["supported"], "complete": analysis["complete"],
            "tokens": [{"index": f["index"], "text": f["word"], "context": f["context"]}
                       for f in frames if f["stage"] == "word"],
            "frames": frames, "projection": projection,
            "scope": "Native symbolic trace and explicit encoding projection; not neural or human evidence"}
