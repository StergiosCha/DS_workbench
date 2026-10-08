"""One local JSONL record per decision request."""

import json
from pathlib import Path
from threading import Lock

_LOCK = Lock()


def append_jsonl(path, record):
    path = Path(path)
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(encoded)
