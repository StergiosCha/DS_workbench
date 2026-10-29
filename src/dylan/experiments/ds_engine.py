"""Adapter around the preserved DS baseline; DS-specific objects stay here."""

from pathlib import Path

from dylan.experiments.contracts import Analysis, digest
from dylan.hybrid.traces import DSAdapter


class DSEngine:
    def __init__(self, identifier):
        self.identifier = identifier
        grammar = "2026-english-classical" if identifier == "ds-english-v1" else "2026-smg-classical"
        self.adapter = DSAdapter(grammar, extensions=("polydefinites",) if identifier == "ds-greek-poly-v1" else ())

    def analyse(self, observation, *, trace=True):
        # Structural cue extraction needs lexical action identities even when
        # the caller omits verbose native states from its output.
        result = self.adapter.probe(observation.text, left_context=observation.left_context,
                                    complete=observation.task == "sentence")
        supported = result["status"] in {"recognized_fragment", "complete"}
        actions = []
        for frame in result["frames"]:
            if not frame["context"]:
                actions.extend(program["template"] or program["name"]
                    for edge in frame["selected_actions"] for program in edge["programs"])
        structural = {("ds-action", *actions[i:i + n]) for n in (2, 3) for i in range(len(actions) - n + 1)}
        meaning = tuple(label for node in result["state"]["nodes"] if node["address"] == "0"
                        for label in node["labels"] if label.startswith("Fo("))
        return Analysis(self.identifier, observation, result["status"], supported,
            result["status"] == "complete" or (supported and result["state"]["complete"]),
            tuple(sorted(structural)), meaning, result["frames"] if trace else [], result["search"],
            {"grammar_sha256": result["grammar_sha256"], "baseline": "c285928",
             "adapter_sha256": digest(Path(__file__).read_text()), "native_state": result["state"] if trace else None,
             "cue_contract": "Selected-path action-template 2/3-grams; lossy, not action equivalence",
             "processing": result["ambiguity"]})

    def close(self):
        self.adapter.close()
