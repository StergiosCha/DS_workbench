"""Vercel entrypoint; deliberately does not load local .env files."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
# Vercel extends sys.path for bundled dependencies; child interpreters need the
# same paths as well as the source tree, without relying on an editable install.
os.environ["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(sys.path))
os.environ["DS_ENGLISH_CORPORA"] = str(ROOT / "data" / "corpora")
os.environ["DS_DICTIONARY_PATH"] = str(ROOT / "data" / "wordnet.sqlite3")
os.environ["DS_LEXICAL_CACHE"] = "/tmp/ds-workbench/lexical.sqlite3"
os.environ["DS_JEV_LOG"] = "/tmp/ds-workbench/jev.jsonl"

from dylan.workbench_asgi import app  # noqa: E402, F401
