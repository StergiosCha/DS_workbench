"""Package discovery and explicit source-to-wheel runtime resource mappings."""

from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup

_ROOT = Path(__file__).resolve().parent


def _packages() -> list[str]:
    """Return engine packages and the explicitly mapped resource packages."""
    names = set(find_packages(where=str(_ROOT / "src")))
    names.update({"dynamicsyntax.resources", "dynamicsyntax.workbench_assets",
                  "dynamicsyntax.workbench_data"})
    return sorted(names)


setup(
    packages=_packages(),
    package_dir={
        "": "src",
        "dynamicsyntax.resources": "resources",
        "dynamicsyntax.workbench_assets": "workbench",
        "dynamicsyntax.workbench_data": "data",
    },
)
