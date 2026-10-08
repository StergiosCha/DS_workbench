"""Apply measured or recorded model preferences without deleting alternatives."""

from dylan.decision.client import content_hash
from dylan.decision.questions.fanout_v1 import questions
from dylan.decision.state import fanout_state


def lexical_key(action):
    return content_hash([action.word, action.action_type, action.parameters, action._source_lines])


def priors(record, question, ids):
    if not record or record.get("stub") or record.get("action_taken") not in {"runtime_ordering", "recorded_ordering"}:
        return {}
    answer = record["answers"].get(question, {})
    values = answer.get("probabilities", {})
    choice = answer.get("choice")
    if choice not in ids or values.get(choice, 0) < 0.50:
        return {}
    return {identity: values[identity] for identity in ids}


class FanoutRanker:
    def __init__(self, parser):
        self.parser = parser
        self.seen = set()

    def __call__(self, parent, edges):
        client = self.parser.decision_client
        if client is None or len(edges) < 2:
            return
        signature = (id(parent), tuple(sorted(edge.edge_id for edge in edges)))
        if signature in self.seen:
            return
        self.seen.add(signature)
        # API Choices support 255 options, including the uncertain option.
        # Large fan-outs retain deterministic order and are reported, not cut.
        if len(edges) > 254:
            return
        state = fanout_state(self.parser, parent, edges)
        ids = [candidate["id"] for candidate in state["candidates"]]
        record = client.decide(state, questions(state["candidates"]), idea=2,
                               deterministic_order=ids, replay_context={
                                   "replay_edges": {identity: edge.edge_id for identity, edge in zip(ids, edges)},
                                   "replay_parent": parent.tuple_id,
                               })
        weights = priors(record, "continuation", ids)
        for identity, edge in zip(ids, edges):
            if identity in weights:
                edge.prior = weights[identity]
