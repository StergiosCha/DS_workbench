"""Declared observation models. Default coefficients are illustrative, not fitted."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Measurement:
    kind: str
    intercept: float = math.log(.8)
    activation_slope: float = -.12
    sigma: float = .25

    def __post_init__(self):
        if not isinstance(self.kind, str) or self.kind not in {"lognormal-v1", "shifted-lognormal-v1"}:
            raise ValueError("Unknown measurement component")
        if not all(math.isfinite(x) for x in (self.intercept, self.activation_slope, self.sigma)) or self.sigma <= 0:
            raise ValueError("Invalid observation-model parameters")

    @property
    def shift(self):
        return .15 if self.kind == "shifted-lognormal-v1" else 0.

    def predict(self, activation):
        if activation is None:
            return {"status": "unavailable", "reason": "required representation unsupported"}
        mu = self.intercept + self.activation_slope * activation
        return {"status": "illustrative", "mean_rt_ms": 1000 * (self.shift + math.exp(mu + self.sigma**2 / 2)),
                "median_rt_ms": 1000 * (self.shift + math.exp(mu)),
                "parameters": {"intercept": self.intercept, "activation_slope": self.activation_slope,
                               "sigma": self.sigma, "shift_seconds": self.shift},
                "interpretation": "Unfitted demonstration of a measurement component; not a human RT estimate"}
