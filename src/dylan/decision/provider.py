"""Explicit credential routing for the native Jev System One API."""

import os

DIRECT_MODEL = "jev-1.13.0"
OPENROUTER_MODEL = "typesafe/jev-1.13-20260917"


def settings():
    provider = os.getenv("DS_DECISION_PROVIDER") or (
        "openrouter" if os.getenv("OPENROUTER_API_KEY") else "typesafe"
    )
    if provider == "openrouter":
        return {
            "provider": provider, "model": OPENROUTER_MODEL,
            "endpoint": "https://openrouter.ai/api/v1/systemone",
            "key": os.getenv("OPENROUTER_API_KEY", ""),
        }
    if provider == "typesafe":
        return {
            "provider": provider, "model": DIRECT_MODEL,
            "endpoint": "https://api.typesafe.ai/v1/systemone",
            "key": os.getenv("TYPESAFE_API_KEY", ""),
        }
    raise ValueError("DS_DECISION_PROVIDER must be openrouter or typesafe")
