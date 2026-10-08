"""Hosted API parity, process isolation and enforceable public-demo bounds."""

import asyncio
import json
import subprocess
import sys

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from dylan import workbench_asgi as server  # noqa: E402

PAYLOAD = {"sentence": "john likes mary.", "grammar": "2026-english-mltt"}


@pytest.fixture
def client():
    with TestClient(server.app) as client:
        yield client


def test_configuration_and_static_files(client):
    config = client.get("/api/config")
    assert config.status_code == 200
    assert not config.json()["lexical"]["provider"]["configured"]
    assert not config.json()["lexical"]["selection"]["configured"]
    assert not config.json()["decision"]["configured"]
    assert client.get("/").status_code == 200
    assert client.get("/research.js").status_code == 200
    assert client.get("/data/wordnet.sqlite3").status_code == 404
    assert client.get("/.env").status_code == 404
    assert config.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    "grammar", ["2026-english-mltt", "2026-english-classical", "2015-english-ttr"]
)
def test_real_parser_and_streaming_final_result(client, grammar):
    payload = {**PAYLOAD, "grammar": grammar}
    response = client.post("/api/parse", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["complete"]
    stream = client.post("/api/parse/stream", json=payload)
    frames = [json.loads(line) for line in stream.text.splitlines()]
    assert stream.headers["content-type"].startswith("application/x-ndjson")
    assert frames[-1]["event"] == "result"
    assert frames[-1]["result"]["complete"]
    assert frames[-1]["result"]["grammar"] == grammar
    assert len(frames) > 1


@pytest.mark.parametrize(
    "option,status",
    [
        ({"lexical_mode": "model"}, 401),
        ({"lexical_mode": "jev"}, 401),
        ({"decision_mode": "jev"}, 401),
        ({"decision_mode": []}, 400),
    ],
)
def test_models_require_user_key_and_malformed_options_rejected(
    client, option, status, monkeypatch
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "host-secret-must-not-be-used")
    assert client.post("/api/parse", json={**PAYLOAD, **option}).status_code == status


def test_request_limits_and_origin(client):
    oversized = client.post("/api/parse", content=b"x" * 32769)
    assert oversized.status_code == 400 and "32768 bytes" in oversized.json()["error"]
    assert client.post("/api/parse", content=b"invalid").status_code == 400
    assert (
        client.post(
            "/api/parse", json=PAYLOAD, headers={"Origin": "https://elsewhere.example"}
        ).status_code
        == 403
    )
    assert (
        client.post("/api/parse", json=PAYLOAD, headers={"Origin": "http://testserver"}).status_code
        == 200
    )
    assert client.get("/api/not-found").status_code == 404


@pytest.mark.parametrize("grammar,text", [
    ("2026-english-mltt", "John walks. Unknown. He walks."),
    ("2026-smg-classical", "Είμαι γιατρός. Αμπρακατάμπρα. Εγώ σε ξέρω."),
])
def test_public_paragraph_stream_keeps_failure_and_later_sentences(client, grammar, text):
    response = client.post("/api/parse/stream", json={"paragraph": text, "grammar": grammar})
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]["event"] == "paragraph_start"
    result = events[-1]["result"]
    assert not result["complete"] and result["coverage"]["total"] == 3
    assert result["sentences"][2]["complete"]
    assert result["sentences"][2]["context_gaps"] == [1]


def test_lookup_validation_error_and_failure_distinction(client, monkeypatch):
    assert client.get("/api/research/english/search?q=a&q=b").status_code == 400
    assert client.get("/api/research/unknown").status_code == 404

    def unavailable(*args):
        raise server.SourceError("Corpus unavailable")

    monkeypatch.setattr(server, "dispatch", unavailable)
    response = client.get("/api/research/english/search?q=bank")
    assert response.status_code == 502 and response.json()["error"] == "Corpus unavailable"


@pytest.mark.parametrize("stream", [False, True])
def test_timeout_kills_worker_and_releases_slot(client, monkeypatch, stream):
    workers = []

    async def spawn():
        worker = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "import time; time.sleep(10)",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        workers.append(worker)
        return worker

    monkeypatch.setattr(server, "spawn_worker", spawn)
    monkeypatch.setattr(server, "PARSE_SECONDS", 0.05)
    response = client.post("/api/parse/stream" if stream else "/api/parse", json=PAYLOAD)
    if stream:
        assert "55-second limit" in json.loads(response.text)["result"]["error"]
    else:
        assert response.status_code == 408
    assert workers[0].returncode is not None
    assert server.PARSE_SLOTS.acquire(blocking=False)
    assert server.PARSE_SLOTS.acquire(blocking=False)
    server.PARSE_SLOTS.release()
    server.PARSE_SLOTS.release()


@pytest.mark.parametrize("stream", [False, True])
def test_large_output_is_an_explicit_error(client, monkeypatch, stream):
    monkeypatch.setattr(server, "MAX_RESPONSE_BYTES", 50)
    response = client.post("/api/parse/stream" if stream else "/api/parse", json=PAYLOAD)
    if stream:
        assert "error" in json.loads(response.text.splitlines()[-1])["result"]
    else:
        assert response.status_code == 413


def test_busy_parser_rejects_instead_of_queueing(client):
    assert server.PARSE_SLOTS.acquire(blocking=False)
    assert server.PARSE_SLOTS.acquire(blocking=False)
    try:
        assert client.post("/api/parse", json=PAYLOAD).status_code == 503
    finally:
        server.PARSE_SLOTS.release()
        server.PARSE_SLOTS.release()


def test_connect_endpoint_origin_query_and_credentials(client, monkeypatch):
    assert client.get("/api/config").json()["openrouter"]["enabled"]
    assert client.get("/openrouter.js").status_code == 200
    assert client.post("/api/openrouter/connect").status_code == 401
    assert client.post("/api/openrouter/connect?key=not-a-real-key").status_code == 400
    assert (
        client.post(
            "/api/openrouter/connect", headers={"Origin": "https://elsewhere.example"}
        ).status_code
        == 403
    )
    monkeypatch.setattr(
        server.openrouter_connection,
        "read_openrouter",
        lambda path, key: {"data": {} if path == "/key" else []},
    )
    response = client.post(
        "/api/openrouter/connect", headers={"Authorization": "Bearer fixture-secret"}
    )
    assert response.status_code == 200 and response.json()["connected"]
    assert "fixture-secret" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("stream", [False, True])
def test_actual_workers_use_each_visitors_credentials_and_selected_model(
    client, monkeypatch, stream
):
    environments = []
    original = asyncio.create_subprocess_exec

    async def spawn(*args, **kwargs):
        environments.append(kwargs["env"])
        return await original(*args, **kwargs)

    monkeypatch.setenv("OPENAI_API_KEY", "host-openai-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "host-openrouter-secret")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    endpoint = "/api/parse/stream" if stream else "/api/parse"
    for index in range(2):
        response = client.post(
            endpoint,
            json={
                **PAYLOAD,
                "lexical_mode": "model",
                "openrouter_model": f"provider/model-{index}",
            },
            headers={"Authorization": f"Bearer visitor-{index}-secret"},
        )
        assert response.status_code == 200
        result = json.loads(response.text.splitlines()[-1])["result"] if stream else response.json()
        assert result["complete"]  # Known words require no provider request.
        assert environments[-1]["OPENROUTER_API_KEY"] == f"visitor-{index}-secret"
        assert environments[-1]["DS_LEXICAL_MODEL"] == f"provider/model-{index}"
        assert "OPENAI_API_KEY" not in environments[-1]
        assert "secret" not in response.text
    assert client.post(endpoint, json=PAYLOAD).status_code == 200
    assert "OPENROUTER_API_KEY" not in environments[-1]
