"""Exercise a wheel from outside the checkout; run with the installed Python -I.

Requires the hosting extra. No AI or remote evidence requests are made.
The caller should use a temporary working directory. Not a coverage benchmark.
"""

import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import dynamicsyntax as ds
from dylan.greek_lexical_dictionary import configuration, source
from dylan.workbench_asgi import app
from dylan.workbench_paths import SOURCE_ROOT, WEB_ROOT, WORKING_ROOT, data_path
from dylan.workbench_server import make_server


def main():
    assert SOURCE_ROOT is None, "This check must import an installed wheel, not src/."
    assert "site-packages" in Path(ds.__file__).parts, ds.__file__
    assert WORKING_ROOT == Path.cwd()
    assert (WEB_ROOT / "index.html").is_file()
    assert configuration()["installed"] and source()["entries"]
    assert data_path("greek-clitics/corpus.jsonl").is_file()
    assert app.routes[-1].name == "workbench"
    for grammar in ("2026-english-classical", "2026-english-mltt", "2015-english-ttr"):
        result = ds.parse("john likes mary.", grammar)
        assert result.ok and result.tree.is_complete() and result.cap_hit is None, grammar

    server = make_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def get(path):
        with urlopen(base + path, timeout=15) as response:
            return response.read()

    def post(payload, stream=False):
        request = Request(base + "/api/parse" + ("/stream" if stream else ""),
                          data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=60) as response:
            body = response.read()
        return json.loads(body.splitlines()[-1])["result"] if stream else json.loads(body)

    checks = []
    try:
        for path in ("/", "/app.js", "/openrouter.js", "/research.js", "/styles.css"):
            assert get(path), path
        assert json.loads(get("/api/config"))["grammars"]
        for path in ("/.env", "/data/greek-lexicon/gdt-train.json"):
            try:
                get(path)
            except HTTPError as exc:
                assert exc.code == 404
            else:
                raise AssertionError(f"Private path exposed: {path}")
        for backend in ("classical", "mltt"):
            cases = [
                (f"2026-english-{backend}", "John, who Mary knows, walks.", "off", True),
                (f"2026-smg-{backend}", "της τον έδωσε.", "corpus", True),
                (f"2026-english-{backend}", "John walks because.", "off", False),
            ]
            for grammar, sentence, lexical_mode, expected in cases:
                for stream in (False, True):
                    result = post({"grammar": grammar, "sentence": sentence,
                                   "lexical_mode": lexical_mode, "decision_mode": "off"}, stream)
                    assert result["complete"] == expected, result.get("error", result.get("failure"))
                    assert result["cap_hit"] is None
                    checks.append({"grammar": grammar, "sentence": sentence,
                                   "stream": stream, "complete": result["complete"]})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(json.dumps({"version": ds.__version__, "checks_passed": len(checks),
                      "installed_package": str(Path(ds.__file__).parent),
                      "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
