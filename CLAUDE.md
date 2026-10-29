# DS Workbench: Claude Code entry point

Read [the current handover](docs/design/claude-code-handover-2026-10-30.md)
before continuing this research work. It identifies completed implementation,
scientific limitations, verification and the next milestone.

- Work on `codex/hybrid-syntax-research`. The public workbench is a separate
  baseline; this branch has not been merged or deployed.
- The intended architecture is a modular linguistic experiment host. DS is a
  preserved reference configuration; CCG has its own engine. The existing LFG,
  feature, construction and MG fragments retain their explicitly bounded roles.
- The next milestone is integrating the selected published test battery, starting
  with versioned ingestion and coverage diagnostics. The literature selection
  is documented; its benchmark runner is not implemented yet.
- Keep human observations, synthetic recovery, illustrative predictions and AI
  judgments distinguishable. Unknown vocabulary/search limits are not negative
  grammaticality judgments. Raw parser counters are not surprisal.
- Follow the handover's source/version and validation requirements when changing
  experiments. Preserve the frozen DS references and existing public imports.
- Local `.env` credentials and raw `build/` artifacts stay local. Reuse configured
  providers without printing or committing secrets. User-owned untracked papers,
  reports and Arash scripts are listed in the handover; preserve them.

Setup and ordinary usage: [README](README.md).
Architecture: [modular experiments](docs/design/modular-experiments.md).
Next test battery: [literature selection](docs/design/literature-test-battery.md).
