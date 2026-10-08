# Entry decision stub parity

Measured 2026-09-27 with `scripts/replay_entries.py` after the approved M3 vocabulary merge. Decisions off and neutral stub logging produced identical outcomes, completion, semantic strings, cap reports and search counters over all 691 corpus runs whose grammar exists. The 21 runs targeting unavailable historical/other grammars are outside this parser comparison and remain grammar gaps in the coverage report.

There were zero mismatches, zero execution errors and zero live model calls. The replay collected 61 winning lexical entries at ambiguous words. These are parser-path labels for future calibration, not independent linguistic judgments or 61 distinct lexical types. Full local details are in ignored `build/decision/entry-replay.json` and its JSONL audit.

`DecisionClient` pins `jev-1.13.0`, validates typed distributions, and logs question and state hashes. The parser's client defaults to `None`. An explicitly attached client records neutral entry decisions; even a configured key and model name cannot enable live runtime inference while the gate is unmeasured. Offline calibration is a separate explicit call. No API key is recorded in the audit.

Edges have optional priors and a deterministic id tie-break after the existing completion and induction heuristics. The runtime stub sets no priors and prunes no candidates. Lexical actions retain their template parameters for inspection. Input snapshots use the active dialogue path, so abandoned repair tokens do not become left context.

Live entry ranking remains **unmeasured and disabled**. No accuracy or speed improvement is claimed. Fan-out ranking and workbench decision controls belong to M4.
