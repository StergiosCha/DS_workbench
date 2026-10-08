# Handover verification · 7 October 2026

This is a local packaging/onboarding check, not a new linguistic-coverage
evaluation and not a public package release. Platform: macOS, Python 3.12.8.

| Check | Result |
| --- | --- |
| Independent grammar tutorial, source environment | 12/12 exact-meaning/completion checks; Classical and Constructive; no AI. |
| Same tutorial, clean installed-wheel environment | 12/12; installed resources copied into independent grammar directories. |
| Wheel loaded outside checkout with Python `-I` | Pass: `dynamicsyntax` imports from the temporary environment's site-packages. |
| Installed local HTTP and streaming | 12/12 outcomes: English LINK relatives, Greek GDT ditransitive, incomplete causal clause; both native backends and both response modes. |
| Installed Python parser | Complete basic parse in Classical, Constructive and inherited TTR. |
| Static/data boundary | Interface/config available; `.env` and data paths not served. Greek lexical index and judgment fixtures packaged. ASGI app imports. |
| Source server/Greek/paragraph regressions | 92 passed. One existing Starlette HTTP-client deprecation warning. |
| Whole-suite audit | 1,862 passed, 3 skipped, 4 failures initially; the failures and focused follow-up are described below. |
| Test lint and document build | Ruff passes for tests and new Python helpers; updated walkthrough compiles with zero overfull boxes. |

The audit found two stale lexical-cut assertions after the nonrestrictive
period entry was added. They now expect that additional cut; all 24 readings
tests pass. One HTTP test initially lacked sandbox permission to bind a port;
it passes with loopback permission. The fourth failure was an absent external
`pst-tree.sty`, despite `latexmk` being installed. The optional TeX smoke test
now checks its external package prerequisites and reports a specific skip.
Its PDF compile is not claimed to pass on this machine. These are focused
follow-ups to the full audit, not a second complete suite run.

The inherited TTR grammar logs skipped/malformed lexical entries during
loading; the successful basic TTR probe does not establish strict validity or
coverage of that whole grammar. The broader research catalogue tracks TTR
auditing separately. Local network binding required sandbox permission;
no remote model or corpus request was used by the installation checks.

Reproduce using `scripts/check_installed_workbench.py`,
`examples/community/extend_grammar.py`, and the maintainer build instructions.
`scripts/check_release_contents.py` checks the wheel/source archive for the
required handover files and excluded private paths. Per-artifact SHA-256 sums
belong beside the built files, not inside a self-referential archive manifest.
CI now has a separate installed-package job; its remote result is not claimed
by this local check.
