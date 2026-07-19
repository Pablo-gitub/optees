# Agent Benchmarks

This directory will contain executable, versioned experiments comparing agents
solving the same synthetic business scenarios without Optees and with Optees.

The protocol, repository structure, metrics, privacy rules, and publication
gate are defined in [`docs/AGENT_BENCHMARKS.md`](../../docs/AGENT_BENCHMARKS.md).

The first executable scenario is
[`manufacturing-planning-001`](scenarios/manufacturing-planning-001/README.md).
It covers a direct MILP task and a regression-to-MILP orchestration task using
fully synthetic company data.

The first recorded exploratory integration run is
[`claude-cowork-manufacturing-2026-07-18`](studies/claude-cowork-manufacturing-2026-07-18/README.md).
It preserves Claude-generated DOCX/PDF reports and their hashes while clearly
recording the metadata still missing for a publishable paired benchmark.

The first recorded local-LLM solver run is
[`qwen-ollama-manufacturing-2026-07-20`](studies/qwen-ollama-manufacturing-2026-07-20/README.md).
It preserves an Optees D0/Qwen terminal transcript, a ground-truth review, and
known response defects. Its prompt contains the numerical inputs, so it tests
the agent-to-solver loop but not Excel ingestion.

Scientific solver datasets remain under `tests/data/` and are documented in
`docs/DATASETS.md`; they must not be mixed with these agent-effectiveness
experiments.
