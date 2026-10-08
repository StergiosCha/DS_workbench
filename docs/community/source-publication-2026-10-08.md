# Workbench source snapshot — 8 October 2026

Public repository: <https://github.com/StergiosCha/DS_workbench>.

This is a development source snapshot, with the engine, native English/Greek
grammars, browser application, optional model integrations, tests, community
extension tutorial, technical reports, slides and 53-work research library.
The running demo is <https://ds-workbench.vercel.app/>; publishing this source
does not redeploy that application or publish a package to PyPI.

The snapshot preserves public upstream history through commit
`3441c4ad2e968a9e0df1f9b0aa213f62d84fc598` and adds the accumulated workbench
extensions as one source commit. Local development branches and uncommitted
work were retained separately. Account configuration, credentials, downloaded
source PDFs, generated dictionary databases and private development handovers
are excluded. See `LICENSE` and `THIRD_PARTY_NOTICES.md` for software and data
terms; no new blanket licence is assigned.

## Publication checks

The isolated source snapshot was checked on macOS with Python 3.12.8:

- Full pytest discovery: 1,892 tests. The initial run passed 1,855, skipped
  six, and failed 31 because WordNet was absent or local HTTP binding was
  denied by the execution sandbox. After building the pinned WordNet index
  and allowing the local test server, all 31 failed tests passed. Together
  these runs cover 1,886 passing tests and six skips; this is not described
  as a second complete-suite run.
- Ruff passes for tests and the updated library browser checker.
- Legacy TTR grammar mirrors match the canonical grammar.
- Both corpus families execute from the isolated source checkout, and the
  coverage report passes its check across 146 groups.
- Source distribution and wheel build, and the archive-content checks pass.
- The wheel installed in a fresh environment outside the checkout passes
  12 HTTP/streaming checks and basic parsing in all three semantic backends.
- The independent grammar-extension tutorial passes 12 checks from that
  installed wheel, without AI.
- All 11 offline library browser checks pass; all 53 citations round-trip
  through BibTeX/CSL with matching titles, author arrays and issued dates.
  The structural library validator passes.
- Staged files were checked for private/account paths and common credential
  patterns. No matching credentials were found. Source PDFs and caches were
  not added to the repository.

The pinned WordNet preparation is now explicit in CI and the maintainer
instructions. Core bundled grammar examples still work without that optional
index. No live model requests were used by these publication checks.

## Research corrections included

KCC15 now follows the printed Chatzikyriakidis–Kempson–Cann author order.
The expansion report correctly distinguishes 12 newly added works with PDFs
from three source additions to existing works. The library's aggregate label
is “research cards”; abstract-level readings retain their stated limits.
Browser checks handle multiple cards per work and the expanded catalogue.
The unavailable OpenAlex scratch artifacts remain an explicitly recorded gap.

These checks establish reproducibility of the stated fragment and packaging
behaviour. They do not establish general open-text semantic accuracy or equal
coverage across Classical, Constructive and TTR.
