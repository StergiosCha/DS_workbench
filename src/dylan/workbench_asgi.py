"""Public ASGI workbench with request-scoped model credentials and isolated workers."""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from dylan.research_sources import SourceError, dispatch
from dylan.workbench_api import configuration, validate_request
from dylan import openrouter_connection

from dylan.workbench_paths import WEB_ROOT, WORKING_ROOT

ROOT = WORKING_ROOT
PARSE_SECONDS = 55
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
PARSE_SLOTS = threading.BoundedSemaphore(2)
LOOKUP_SLOTS = threading.BoundedSemaphore(4)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    )
    return response


@app.get("/api/config")
def public_configuration():
    result = configuration()
    result["lexical"]["provider"].update(
        configured=False, message="Connect your OpenRouter key to enable model proposals."
    )
    result["lexical"]["selection"]["configured"] = False
    result["decision"]["configured"] = False
    result["openrouter"] = {"enabled": True}
    return result


@app.post("/api/openrouter/connect")
def connect_openrouter(request: Request):
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        return JSONResponse({"error": "Use the workbench from this server’s address."}, 403)
    if request.url.query:
        return JSONResponse({"error": "Connection options must not be put in the URL."}, 400)
    if not LOOKUP_SLOTS.acquire(blocking=False):
        return JSONResponse({"error": "Connections are busy. Please retry shortly."}, 503)
    try:
        return openrouter_connection.connect(request.headers.get("authorization"))
    except openrouter_connection.ConnectionFailure as exc:
        return JSONResponse({"error": str(exc)}, exc.status)
    finally:
        LOOKUP_SLOTS.release()


@app.get("/api/research/{endpoint:path}")
def research_lookup(endpoint: str, request: Request):
    if not LOOKUP_SLOTS.acquire(blocking=False):
        return JSONResponse({"error": "Source lookups are busy. Please retry shortly."}, 503)
    try:
        if len(str(request.url)) > 4096:
            raise ValueError("The lookup URL is too long.")
        values = parse_qs(request.url.query, keep_blank_values=True, max_num_fields=12)
        if any(len(v) != 1 for v in values.values()):
            raise ValueError("Repeated lookup options are not supported.")
        return dispatch("/api/research/" + endpoint, {k: v[0] for k, v in values.items()})
    except KeyError:
        return JSONResponse({"error": "Unknown research endpoint."}, 404)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, 400)
    except SourceError as exc:
        return JSONResponse({"error": str(exc)}, 502)
    finally:
        LOOKUP_SLOTS.release()


async def stop_worker(worker):
    if worker is not None:
        if worker.returncode is None:
            try:
                worker.kill()
            except ProcessLookupError:
                pass
        # A paused stdout pipe can keep asyncio.wait() pending after the process
        # exits. Drain it after killing, without retaining an oversized response.
        if worker.stdout is not None:
            while await worker.stdout.read(65536):
                pass
        await worker.wait()


async def spawn_worker(connection=None):
    # Source checkout imports must also work in the isolated child process.
    env = {
        **openrouter_connection.worker_environment(connection),
        "PYTHONPATH": os.pathsep.join(dict.fromkeys([str(ROOT / "src"), *sys.path])),
    }
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "dylan.workbench_api",
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        limit=MAX_RESPONSE_BYTES + 1,
    )


def error_frame(message):
    return (json.dumps({"event": "result", "result": {"error": message}}) + "\n").encode()


async def stream_parse(payload, connection=None):
    worker = None
    try:
        deadline = time.monotonic() + PARSE_SECONDS
        worker = await spawn_worker(connection) if connection else await spawn_worker()
        worker.stdin.write(json.dumps({**payload, "stream": True}).encode())
        await worker.stdin.drain()
        worker.stdin.close()
        total = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            line = await asyncio.wait_for(worker.stdout.readline(), remaining)
            if not line:
                await asyncio.wait_for(worker.wait(), max(0.01, deadline - time.monotonic()))
                if worker.returncode:
                    yield error_frame("The parser worker stopped. Try a shorter sentence.")
                return
            total += len(line)
            if total > MAX_RESPONSE_BYTES:
                yield error_frame(
                    "This trace is too large for the hosted demo. Request fewer readings or a shorter sentence."
                )
                return
            yield line
    except TimeoutError:
        yield error_frame("Parsing reached the 55-second limit. Try a shorter sentence.")
    except (OSError, ValueError):
        yield error_frame(
            "The parser worker could not return a bounded trace. Try a shorter sentence."
        )
    finally:
        try:
            await stop_worker(worker)
        finally:
            PARSE_SLOTS.release()


async def parse_once(payload, connection=None):
    worker = None
    try:
        # Use the same bounded line protocol without streaming to the caller.
        worker = await spawn_worker(connection) if connection else await spawn_worker()
        worker.stdin.write(json.dumps({**payload, "stream": False}).encode())
        await worker.stdin.drain()
        worker.stdin.close()
        output = bytearray()
        async with asyncio.timeout(PARSE_SECONDS):
            while chunk := await worker.stdout.read(65536):
                output.extend(chunk)
                if len(output) > MAX_RESPONSE_BYTES:
                    return JSONResponse(
                        {
                            "error": "This analysis is too large for the hosted demo. Request fewer readings."
                        },
                        413,
                    )
            await worker.wait()
        if worker.returncode:
            raise ValueError("Worker stopped")
        result = json.loads(output)
        return JSONResponse(result, 422 if "error" in result else 200)
    except TimeoutError:
        return JSONResponse(
            {"error": "Parsing reached the 55-second limit. Try a shorter sentence."}, 408
        )
    except (OSError, ValueError):
        return JSONResponse({"error": "The parser worker could not return a result."}, 500)
    finally:
        try:
            await stop_worker(worker)
        finally:
            PARSE_SLOTS.release()


@app.post("/api/parse")
@app.post("/api/parse/stream")
async def parse_endpoint(request: Request):
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        return JSONResponse({"error": "Use the workbench from this server’s address."}, 403)
    try:
        if int(request.headers.get("content-length", "0")) > 32768:
            raise ValueError("The request body must be at most 32768 bytes.")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 32768:
                raise ValueError("The request body must be at most 32768 bytes.")
        payload = json.loads(body)
        payload, connection = openrouter_connection.prepare_parse(
            payload, request.headers.get("authorization")
        )
        validate_request(payload)
    except openrouter_connection.ConnectionFailure as exc:
        return JSONResponse({"error": str(exc)}, exc.status)
    except (ValueError, UnicodeDecodeError) as exc:
        return JSONResponse({"error": str(exc)}, 400)
    except TypeError:
        return JSONResponse({"error": "Invalid parse option type."}, 400)
    if not PARSE_SLOTS.acquire(blocking=False):
        return JSONResponse({"error": "The parser is busy. Please try again shortly."}, 503)
    if request.url.path.endswith("/stream"):
        return StreamingResponse(
            stream_parse(payload, connection), media_type="application/x-ndjson"
        )
    return await parse_once(payload, connection)


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
def unknown_api(path: str):
    return JSONResponse({"error": "Unknown API endpoint."}, 404)


app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="workbench")
