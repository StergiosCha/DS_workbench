"""Loopback HTTP server for the DS Workbench, with isolated Python parse workers."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import sys
import threading
import selectors
import time
from urllib.parse import parse_qs, urlsplit

from dylan.workbench_api import configuration, validate_request
from dylan import openrouter_connection

from dylan.workbench_paths import WEB_ROOT, WORKING_ROOT
_WORKERS = threading.BoundedSemaphore(2)
_LOOKUPS = threading.BoundedSemaphore(4)


class WorkbenchHandler(SimpleHTTPRequestHandler):
    """Serve the app and its small same-origin JSON API."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'",
        )
        super().end_headers()

    def send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/api/config":
            self.send_json({**configuration(), "openrouter": {"enabled": True}})
        elif urlsplit(self.path).path.startswith("/api/research/"):
            self.research_lookup()
        elif urlsplit(self.path).path.startswith("/api/"):
            self.send_json({"error": "Unknown API endpoint."}, 404)
        else:
            super().do_GET()

    def research_lookup(self) -> None:
        from dylan.research_sources import SourceError, dispatch

        if not _LOOKUPS.acquire(blocking=False):
            self.send_json({"error": "Source lookups are busy. Please retry shortly."}, 503)
            return
        try:
            if len(self.path) > 4096:
                raise ValueError("The lookup URL is too long.")
            parts = urlsplit(self.path)
            params = parse_qs(parts.query, keep_blank_values=True, max_num_fields=12)
            if any(len(values) != 1 for values in params.values()):
                raise ValueError("Repeated lookup options are not supported.")
            result = dispatch(parts.path, {key: values[0] for key, values in params.items()})
            self.send_json(result)
        except KeyError:
            self.send_json({"error": "Unknown research endpoint."}, 404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except SourceError as exc:
            self.send_json({"error": str(exc)}, 502)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            _LOOKUPS.release()

    def do_POST(self) -> None:
        endpoint = urlsplit(self.path).path
        if endpoint == "/api/openrouter/connect":
            self.connect_openrouter()
            return
        if endpoint not in {"/api/parse", "/api/parse/stream"}:
            self.send_json({"error": "Unknown API endpoint."}, 404)
            return
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            self.send_json({"error": "Use the workbench from this server’s address."}, 403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32768:
                raise ValueError("The request body must be between 1 and 32768 bytes.")
            payload = json.loads(self.rfile.read(size))
            payload, connection = openrouter_connection.prepare_parse(
                payload, self.headers.get("Authorization"), public=False
            )
            validate_request(payload)
        except openrouter_connection.ConnectionFailure as exc:
            self.send_json({"error": str(exc)}, exc.status)
            return
        except (ValueError, UnicodeDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        if not _WORKERS.acquire(blocking=False):
            self.send_json({"error": "The parser is busy. Please try again shortly."}, 503)
            return
        try:
            if endpoint == "/api/parse/stream":
                self.stream_parse(payload, connection)
                return
            worker = subprocess.run(
                [sys.executable, "-m", "dylan.workbench_api"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=55,
                cwd=WORKING_ROOT,
                env=openrouter_connection.worker_environment(connection, public=False),
                check=False,
            )
            if worker.returncode != 0:
                self.send_json(
                    {"error": "The parser worker stopped unexpectedly. Try a shorter sentence."},
                    500,
                )
                return
            result = json.loads(worker.stdout)
            self.send_json(result, 422 if "error" in result else 200)
        except subprocess.TimeoutExpired:
            self.send_json(
                {"error": "Parsing reached the 55-second limit. Try a shorter sentence."}, 408
            )
        except (OSError, json.JSONDecodeError):
            self.send_json({"error": "The parser worker could not return a result."}, 500)
        finally:
            _WORKERS.release()

    def connect_openrouter(self) -> None:
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            self.send_json({"error": "Use the workbench from this server’s address."}, 403)
            return
        if urlsplit(self.path).query:
            self.send_json({"error": "Connection options must not be put in the URL."}, 400)
            return
        if not _LOOKUPS.acquire(blocking=False):
            self.send_json({"error": "Connections are busy. Please retry shortly."}, 503)
            return
        try:
            self.send_json(openrouter_connection.connect(self.headers.get("Authorization")))
        except openrouter_connection.ConnectionFailure as exc:
            self.send_json({"error": str(exc)}, exc.status)
        finally:
            _LOOKUPS.release()

    def stream_parse(self, payload: dict, connection=None) -> None:
        """Flush parser frames as NDJSON; bound worker life even on disconnect."""
        payload = {**payload, "stream": True}
        with subprocess.Popen(
            [sys.executable, "-m", "dylan.workbench_api"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=WORKING_ROOT,
            env=openrouter_connection.worker_environment(connection, public=False),
        ) as worker:
            try:
                worker.stdin.write(json.dumps(payload).encode())
                worker.stdin.close()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                deadline = time.monotonic() + 55
                with selectors.DefaultSelector() as selector:
                    selector.register(worker.stdout, selectors.EVENT_READ)
                    while time.monotonic() < deadline:
                        if not selector.select(timeout=1):
                            continue
                        data = worker.stdout.read1(65536)
                        if not data:
                            return
                        self.wfile.write(data)
                        self.wfile.flush()
                self.wfile.write(
                    b'{"event":"result","result":{"error":"Parsing reached the 55-second limit."}}\n'
                )
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if worker.poll() is None:
                    worker.kill()
                worker.wait()


def make_server(port: int = 8000) -> ThreadingHTTPServer:
    if not (WEB_ROOT / "index.html").is_file():
        raise FileNotFoundError("Workbench assets are missing; reinstall the workbench distribution.")
    return ThreadingHTTPServer(
        ("127.0.0.1", port), partial(WorkbenchHandler, directory=str(WEB_ROOT))
    )


def main() -> None:
    from dylan.workbench_environment import load_environment

    load_environment()
    parser = argparse.ArgumentParser(description="Run DS Workbench with the local Python engine.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--lexical-model",
        help="Model/deployment for optional lexical proposals (or DS_LEXICAL_MODEL)",
    )
    args = parser.parse_args()
    if args.lexical_model:
        os.environ["DS_LEXICAL_MODEL"] = args.lexical_model
    with make_server(args.port) as server:
        print(f"DS Workbench: http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
