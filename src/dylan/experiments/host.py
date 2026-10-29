"""Run composable configurations without importing a particular parsing theory."""

from dylan.experiments.contracts import Configuration, Observation, digest
from dylan.experiments.memory import Memory
from dylan.experiments.measurement import Measurement
from dylan.experiments.registry import create_engine, validate


def cues(analysis, representation):
    lexical = tuple(("lexical-bigram", *words[i:i + 2]) for words in [analysis.observation.text.lower().split()]
                    for i in range(len(words) - 1))
    if representation == "lexical":
        return lexical
    if not analysis.supported:
        return None
    return analysis.cues if representation == "native" else (*lexical, *analysis.cues)


class Session:
    def __init__(self, config=Configuration(), *, factory=create_engine):
        self.config = validate(config)
        self.engine = factory(config.grammar)
        self.memory = Memory(config.memory, config.decay)
        self.measurement = Measurement(config.measurement)
        self.events = []

    def observe(self, observation, *, trace=True):
        analysis = self.engine.analyse(observation, trace=trace)
        values = cues(analysis, self.config.representation)
        before = self.memory.snapshot()
        activation = self.memory.activation(values) if values is not None else None
        prediction = self.measurement.predict(activation)
        # An unsupported structural observation still advances the experimental
        # clock; absence of features is not represented as a recognized analysis.
        self.memory.observe(values or ())
        event = {"index": len(self.events), "analysis": analysis.to_dict(), "activation": activation,
                 "cue_count": len(set(values or ())), "prediction": prediction,
                 "memory_before": before, "memory_after": self.memory.snapshot()}
        self.events.append(event)
        return event

    def close(self):
        self.engine.close()


def run_pair(config, prime, target, *, left_context="", task="fragment", fillers=()):
    session = Session(config)
    try:
        for text in (prime, *fillers, target):
            session.observe(Observation(text, left_context, task))
        return {"configuration": config.to_dict(), "configuration_id": config.identity,
                "events": session.events, "trace_digest": digest(session.events),
                "scope": "Experimental memory/measurement demonstration; no fitted cognitive claim"}
    finally:
        session.close()
