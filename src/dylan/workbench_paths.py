"""Locate read-only assets independently of the working directory.

Source checkouts use their editable files; normal wheel installs use packaged
assets. Worker caches belong in the launch directory, never in site-packages.
"""

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = _ROOT if (_ROOT / "src/dylan/workbench_paths.py").is_file() else None
_PACKAGE = Path(__file__).resolve().parents[1] / "dynamicsyntax"
WEB_ROOT = SOURCE_ROOT / "workbench" if SOURCE_ROOT else _PACKAGE / "workbench_assets"
WORKING_ROOT = SOURCE_ROOT or Path.cwd()


def data_path(relative: str) -> Path:
    """Resolve bundled evidence, or an explicitly selected external data tree."""
    override = os.environ.get("DS_WORKBENCH_DATA")
    if override:
        root = Path(override).expanduser().resolve()
    else:
        root = SOURCE_ROOT / "data" if SOURCE_ROOT else _PACKAGE / "workbench_data"
    return root / relative
