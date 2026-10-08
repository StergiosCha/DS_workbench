"""BYOK model discovery, credential isolation and no cross-user proposal cache."""

from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from urllib.error import HTTPError

import pytest

from dylan import lexical_provider, openrouter_connection as connection
from dylan.lexical_expansion import proposal
from dylan.workbench_api import parse_request

KEY = "fixture-user-secret"
MODEL = "openai/gpt-4.1-mini"


def model(identifier=MODEL, **updates):
    return {
        "id": identifier,
        "name": identifier,
        "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
        "supported_parameters": ["structured_outputs"],
        "pricing": {"prompt": "0.0000004", "completion": "0.0000016"},
        **updates,
    }


def test_connection_only_checks_key_and_lists_compatible_user_models(monkeypatch):
    calls = []
    rows = [
        model("other/variable", pricing={"prompt": "-1", "completion": "1e309"}),
        model(),
        model(),
        model("other/chat", supported_parameters=["json_mode"]),
        model("other/null", architecture={"output_modalities": None}),
        model("other/null-parameters", supported_parameters=None),
        model(
            "other/image",
            architecture={"input_modalities": ["image"], "output_modalities": ["text"]},
        ),
        {
            "id": "typesafe/jev-1.13",
            "canonical_slug": connection.OPENROUTER_MODEL,
            "architecture": {"output_modalities": ["decisions"]},
        },
    ]

    def read(path, key):
        assert key == KEY
        calls.append(path)
        return {"data": {"label": "private account label"}} if path == "/key" else {"data": rows}

    monkeypatch.setattr(connection, "read_openrouter", read)
    result = connection.connect(f"Bearer {KEY}")
    assert calls == ["/key", "/models/user?output_modalities=text,decisions"]
    assert [row["id"] for row in result["models"]] == [MODEL, "other/variable"]
    assert result["models"][0]["input_per_million"] == pytest.approx(0.4)
    assert result["models"][0]["output_per_million"] == pytest.approx(1.6)
    assert result["models"][1]["input_per_million"] is None
    assert result["models"][1]["output_per_million"] is None
    assert result["default_model"] == MODEL and result["jev"]["available"]
    assert KEY not in json.dumps(result) and "private account label" not in json.dumps(result)


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "Basic abcdefgh",
        "Bearer short",
        "Bearer white space",
        "Bearer bad\nsecret",
        "Bearer " + "x" * 513,
    ],
)
def test_invalid_credentials_never_reach_provider(monkeypatch, authorization):
    monkeypatch.setattr(
        connection, "read_openrouter", lambda *_: pytest.fail("Unexpected network call")
    )
    with pytest.raises(connection.ConnectionFailure) as error:
        connection.connect(authorization)
    assert error.value.status == 401


def test_provider_failure_does_not_echo_credentials_or_response_body(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == connection.BASE + "/key"
            assert request.headers["Authorization"] == f"Bearer {KEY}"
            assert not request.data
            raise HTTPError(request.full_url, 401, "rejected " + KEY, {}, io.BytesIO(KEY.encode()))

    monkeypatch.setattr(connection, "build_opener", lambda *_: Opener())
    with pytest.raises(connection.ConnectionFailure) as error:
        connection.read_openrouter("/key", KEY)
    assert error.value.status == 401 and KEY not in str(error.value)
    with pytest.raises(ValueError):
        connection.read_openrouter("https://elsewhere.example", KEY)
    with pytest.raises(connection.ConnectionFailure, match="redirect"):
        connection.NoRedirect().redirect_request(
            None, None, None, None, None, "https://elsewhere.example"
        )


def test_parse_options_keep_credentials_out_of_parser_json():
    payload = {"sentence": "john likes mary.", "lexical_mode": "model", "openrouter_model": MODEL}
    prepared, credentials = connection.prepare_parse(payload, f"Bearer {KEY}")
    assert "openrouter_model" not in prepared and "openrouter_model" in payload
    assert KEY not in json.dumps(prepared)
    assert credentials == {"key": KEY, "model": MODEL}
    for field in ("api_key", "openrouter_key", "authorization"):
        with pytest.raises(ValueError, match="Authorization header"):
            connection.prepare_parse({**payload, field: KEY}, None)
    with pytest.raises(ValueError, match="Choose"):
        connection.prepare_parse(
            {**payload, "openrouter_model": "https://evil.example/model"}, f"Bearer {KEY}"
        )
    assert connection.prepare_parse(payload, None, public=False)[1] is None
    assert connection.prepare_parse({"lexical_mode": "dictionary"}, f"Bearer {KEY}")[1] is None


def test_jev_only_never_configures_the_selected_analysis_model():
    payload = {"lexical_mode": "jev", "allow_model_fallback": False, "openrouter_model": MODEL}
    prepared, credentials = connection.prepare_parse(payload, f"Bearer {KEY}")
    assert prepared["allow_model_fallback"] is False
    assert credentials == {"key": KEY, "model": None}
    assert connection.worker_environment(credentials)["DS_LEXICAL_MODEL"] == ""


def test_parallel_users_have_separate_worker_environments_without_host_fallback(monkeypatch):
    for variable in connection.PROVIDER_ENV:
        monkeypatch.setenv(variable, "host-value")
    before = dict(os.environ)
    credentials = [
        {"key": f"user-{index}-secret", "model": f"provider/model-{index}"} for index in range(20)
    ]
    with ThreadPoolExecutor(4) as executor:
        environments = list(executor.map(connection.worker_environment, credentials))
    for credential, env in zip(credentials, environments):
        assert env["OPENROUTER_API_KEY"] == credential["key"]
        assert env["DS_LEXICAL_MODEL"] == credential["model"]
        assert env["DS_LEXICAL_PROVIDER"] == env["DS_DECISION_PROVIDER"] == "openrouter"
        assert "OPENAI_API_KEY" not in env and "TYPESAFE_API_KEY" not in env
        assert env["DS_EPHEMERAL_MODELS"] == "1" and env["DS_JEV_LOG"] == os.devnull
    assert not connection.PROVIDER_ENV.intersection(connection.worker_environment())
    assert dict(os.environ) == before


def test_ephemeral_model_proposals_never_read_or_write_shared_cache(monkeypatch, tmp_path):
    calls = []

    def propose(*args):
        calls.append(True)
        return {"entries": [proposal("sneezes", "sneeze", "intransitive", ["human"])]}, {
            "provider": "fixture",
            "model": MODEL,
        }

    monkeypatch.setattr(lexical_provider, "propose", propose)
    monkeypatch.setenv("DS_EPHEMERAL_MODELS", "1")
    cache = tmp_path / "shared.sqlite3"
    monkeypatch.setenv("DS_LEXICAL_CACHE", str(cache))
    for _ in range(2):
        result = parse_request(
            {"sentence": "john sneezes.", "grammar": "2026-english-mltt", "lexical_mode": "model"}
        )
        assert result["complete"]
    assert len(calls) == 2 and not cache.exists()
