"""Request-scoped OpenRouter credentials and a bounded, read-only connection check."""

import json
import math
import os
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import certifi

from dylan.decision.provider import OPENROUTER_MODEL

BASE = "https://openrouter.ai/api/v1"
MODEL_ID = re.compile(r"[A-Za-z0-9~][A-Za-z0-9_.~-]*/[A-Za-z0-9][A-Za-z0-9_.:~-]{0,160}\Z")
PROVIDER_ENV = {
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "TYPESAFE_API_KEY",
    "DS_LEXICAL_PROVIDER",
    "DS_LEXICAL_MODEL",
    "DS_LEXICAL_BASE_URL",
    "DS_DECISION_PROVIDER",
    "DS_DECISION_MODEL",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_ENDPOINT",
    "TYPESAFE_BASE_URL",
}


class ConnectionFailure(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ConnectionFailure("OpenRouter returned an unexpected redirect.")


def bearer_key(authorization):
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise ConnectionFailure("Connect your OpenRouter key to use model features.", 401)
    key = authorization[7:]
    if not 8 <= len(key) <= 512 or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ConnectionFailure("Enter a valid OpenRouter API key.", 401)
    return key


def read_openrouter(path, key):
    if path not in {"/key", "/models/user?output_modalities=text,decisions"}:
        raise ValueError("Unsupported OpenRouter lookup")
    request = Request(
        BASE + path, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}
    )
    tls = ssl.create_default_context(cafile=certifi.where())
    opener = build_opener(HTTPSHandler(context=tls), NoRedirect())
    try:
        deadline = time.monotonic() + 12
        with opener.open(request, timeout=12) as response:
            chunks, size = [], 0
            while True:
                chunk = response.read1(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > 6 * 1024 * 1024 or time.monotonic() > deadline:
                    raise ConnectionFailure(
                        "OpenRouter's model list exceeded the connection limit. Try again."
                    )
                chunks.append(chunk)
        return json.loads(b"".join(chunks))
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise ConnectionFailure(
                "OpenRouter rejected this key or its permissions. Check the key and reconnect.", 401
            ) from None
        if exc.code == 402:
            raise ConnectionFailure(
                "OpenRouter reports insufficient credits for this key.", 402
            ) from None
        if exc.code == 429:
            raise ConnectionFailure(
                "OpenRouter is rate limiting this key. Retry shortly.", 429
            ) from None
        raise ConnectionFailure(f"OpenRouter returned HTTP {exc.code}. Try again later.") from None
    except (URLError, TimeoutError, OSError):
        raise ConnectionFailure(
            "OpenRouter could not be reached. Check your connection and retry."
        ) from None
    except (ValueError, TypeError):
        raise ConnectionFailure("OpenRouter returned an unreadable response.") from None


def price_per_million(value):
    try:
        price = float(value) * 1_000_000
        return price if math.isfinite(price) and price >= 0 else None
    except (TypeError, ValueError):
        return None


def connect(authorization):
    key = bearer_key(authorization)
    account = read_openrouter("/key", key)
    if not isinstance(account, dict) or not isinstance(account.get("data"), dict):
        raise ConnectionFailure("OpenRouter did not confirm this key. Please reconnect.")
    catalog = read_openrouter("/models/user?output_modalities=text,decisions", key)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("data"), list):
        raise ConnectionFailure("OpenRouter's model list was unavailable. Please reconnect.")
    models, seen, jev = [], set(), False
    for row in catalog["data"]:
        if not isinstance(row, dict):
            continue
        identifier = row.get("id", "")
        architecture = row.get("architecture") or {}
        if not isinstance(identifier, str) or not isinstance(architecture, dict):
            continue
        outputs = architecture.get("output_modalities", [])
        inputs = architecture.get("input_modalities", [])
        parameters = row.get("supported_parameters", [])
        if not isinstance(outputs, list):
            continue
        if "decisions" in outputs and row.get("canonical_slug") == OPENROUTER_MODEL:
            jev = True
        if (
            not MODEL_ID.fullmatch(identifier)
            or identifier in seen
            or "text" not in outputs
            or not isinstance(inputs, list)
            or "text" not in inputs
            or not isinstance(parameters, list)
            or "structured_outputs" not in parameters
        ):
            continue
        pricing = row.get("pricing") or {}
        if not isinstance(pricing, dict):
            pricing = {}
        seen.add(identifier)
        models.append(
            {
                "id": identifier,
                "name": str(row.get("name") or identifier)[:180],
                "input_per_million": price_per_million(pricing.get("prompt")),
                "output_per_million": price_per_million(pricing.get("completion")),
            }
        )
    models.sort(key=lambda row: (row["name"].lower(), row["id"]))
    default = next(
        (
            name
            for name in (
                "openai/gpt-4.1-mini",
                "deepseek/deepseek-v4.1-flash",
                "google/gemini-2.5-flash",
            )
            if name in seen
        ),
        models[0]["id"] if models else "",
    )
    return {
        "connected": True,
        "models": models,
        "default_model": default,
        "jev": {"available": jev, "model": OPENROUTER_MODEL, "name": "Jev 1.13"},
    }


def prepare_parse(payload, authorization, *, public=True):
    """Remove connection options from parser input; never put a key in its JSON."""
    if not isinstance(payload, dict):
        return payload, None
    payload = dict(payload)
    model = payload.pop("openrouter_model", None)
    if payload.get("lexical_mode") == "jev" and payload.get("allow_model_fallback") is False:
        model = None
    if any(name in payload for name in ("api_key", "openrouter_key", "authorization")):
        raise ValueError("Send the OpenRouter key in the Authorization header, not the parse data.")
    uses_model = (
        payload.get("lexical_mode") in ("model", "jev", "assisted") or payload.get("decision_mode") == "jev"
    )
    if not uses_model or (not public and not authorization):
        return payload, None
    key = bearer_key(authorization)
    if payload.get("lexical_mode") in ("model", "assisted") or (
        payload.get("lexical_mode") == "jev" and model is not None
    ):
        if not isinstance(model, str) or not MODEL_ID.fullmatch(model):
            raise ValueError("Choose an OpenRouter vocabulary model before using AI vocabulary.")
    else:
        model = None
    return payload, {"key": key, "model": model}


def worker_environment(connection=None, *, public=True):
    env = {k: v for k, v in os.environ.items() if not public or k not in PROVIDER_ENV}
    if public or connection:
        # No shared cache or decision log may retain one user's text for another.
        env["DS_EPHEMERAL_MODELS"] = "1"
        env["DS_JEV_LOG"] = os.devnull
    if connection:
        for name in PROVIDER_ENV:
            env.pop(name, None)
        env.update(
            OPENROUTER_API_KEY=connection["key"],
            DS_LEXICAL_PROVIDER="openrouter",
            DS_DECISION_PROVIDER="openrouter",
            DS_LEXICAL_MODEL=connection["model"] or "",
        )
    return env
