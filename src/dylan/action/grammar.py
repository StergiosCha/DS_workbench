"""Computational grammar from ``computational-actions.txt`` (Java ``Grammar``)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from loguru import logger as loguru_logger

from dylan.action.computational_action import ComputationalAction
from dylan.action.lexicon import strip_block_comments

logger = logging.getLogger(__name__)

_URL_PREFIX = re.compile(r"^https?://", re.IGNORECASE)
_FILE_PREFIX = re.compile(r"^file:", re.IGNORECASE)


def _disabled_rule_names(raw_lines: list[str]) -> list[str]:
    """Rule names inside whole-line ``//* ... *//`` blocks: the first non-blank line of each block."""
    names: list[str] = []
    in_block = False
    want_name = False
    for raw in raw_lines:
        line = raw.strip()
        if not in_block:
            if line.startswith("//*") and "*//" not in line:
                in_block = True
                want_name = True
            continue
        if "*//" in line:
            in_block = False
            want_name = False
            continue
        if want_name and line:
            names.append(line.lstrip("*+").strip())
            want_name = False
    return names


class Grammar(dict[str, ComputationalAction]):
    """Map of computational action name → ``ComputationalAction``."""

    FILE_NAME = "computational-actions.txt"

    def __init__(self, dir_or_url: str | Path | None = None, *, strict: bool = False) -> None:
        """Load rules from *dir_or_url*; with *strict*, validation problems raise ``ValueError``."""
        super().__init__()
        self._strict = strict
        self._source_path: Path | None = None
        # Names of rules that sit inside ``//* ... *//`` blocks in the file (disabled, not loaded),
        # in file order, so lint can report them instead of them vanishing silently.
        self.disabled_rule_names: list[str] = []
        if dir_or_url is None:
            return
        self._load_from_disk(dir_or_url)

    def _load_from_disk(self, dir_or_url: str | Path) -> None:
        """Read computational-actions.txt from *dir_or_url*."""
        s = str(dir_or_url)
        if _URL_PREFIX.match(s) or _FILE_PREFIX.match(s):
            logger.warning("URL grammar loading not implemented for %s", s)
            return
        path = Path(dir_or_url) / self.FILE_NAME
        if not path.is_file():
            logger.error("Missing computational actions file %s", path)
            return
        self._source_path = path
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        self.disabled_rule_names = _disabled_rule_names(raw_lines)
        cleaned = strip_block_comments(raw_lines)
        self._init_actions(cleaned)
        logger.info("Loaded %s computational actions", len(self))

    def _init_actions(self, cleaned_lines: list[str | None]) -> None:
        """Parse computational-action blocks (already block-comment-stripped)."""
        name: str | None = None
        always_good = False
        backtrack_on_success = False
        lines: list[str] = []
        for raw in cleaned_lines:
            if raw is None:
                continue
            line = raw.strip()
            if not line and not lines:
                continue
            if not line and lines:
                if name is not None:
                    self._commit(name, lines, always_good, backtrack_on_success)
                name = None
                lines = []
                always_good = False
                backtrack_on_success = False
                continue
            if name is None:
                name = line
                always_good = name.startswith("*")
                if always_good:
                    name = name[1:]
                backtrack_on_success = name.startswith("+")
                if backtrack_on_success:
                    name = name[1:]
                logger.debug(
                    "New computational action: %s (always_good=%s, backtrack_on_success=%s)",
                    name,
                    always_good,
                    backtrack_on_success,
                )
            else:
                lines.append(line)
        if name is not None and lines:
            self._commit(name, lines, always_good, backtrack_on_success)

    def _commit(
        self,
        name: str,
        lines: list[str],
        always_good: bool,
        backtrack_on_success: bool,
    ) -> None:
        if name in self:
            source = self._source_path if self._source_path is not None else self.FILE_NAME
            msg = (
                f"Duplicate computational action {name!r} in {source}: "
                "keeping first occurrence, ignoring redefinition"
            )
            if self._strict:
                raise ValueError(msg)
            loguru_logger.warning(msg)
            return
        completion = "!completion" in lines
        executable = [line for line in lines if line != "!completion"]
        action = ComputationalAction(
            name, executable, always_good, backtrack_on_success, completion=completion
        )
        self[name] = action
        logger.debug("Added computational action %s", action)


Grammar.loadFromDisk = Grammar._load_from_disk  # type: ignore[attr-defined]
Grammar.initActions = Grammar._init_actions  # type: ignore[attr-defined]
