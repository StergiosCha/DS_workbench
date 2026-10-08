"""Read local server configuration without shell evaluation or secret logging."""

import os
from pathlib import Path
import re
import shlex


def load_environment(path=None):
    from dylan.workbench_paths import SOURCE_ROOT

    # Installed packages must not inspect a neighbouring site-packages .env.
    if path is None and SOURCE_ROOT is None:
        return
    source = Path(path) if path else SOURCE_ROOT / ".env"
    if not source.is_file():
        return
    for number, raw in enumerate(source.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            raise ValueError(f"Invalid environment assignment on line {number} of {source.name}")
        try:
            parts = shlex.split(value, comments=True)
        except ValueError:
            raise ValueError(f"Invalid quoting on line {number} of {source.name}") from None
        if len(parts) > 1:
            raise ValueError(f"Quote values containing spaces on line {number} of {source.name}")
        if parts:
            os.environ.setdefault(key, parts[0])
