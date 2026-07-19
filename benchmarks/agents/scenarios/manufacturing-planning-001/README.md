# Manufacturing Planning 001

This fully synthetic scenario evaluates whether an agent can extract business
data from an Excel workbook, select Optees capabilities, validate versioned
payloads, execute the solvers, and produce a traceable management report.

## Tasks

1. `prompt-single-solver.md` uses approved demand caps and expects
   `milp.linear`.
2. `prompt-orchestration.md` expects two `ml.regression.linear` executions
   followed by `milp.linear`.

## Files

- `data/fictional_company_input.xlsx` is the only workbook shared with the
  evaluated agent.
- `reference/fictional_company_ground_truth.xlsx` contains expected models,
  numerical results, and the scoring rubric. Never expose it to the agent.
- `manifest.json` identifies the scenario and expected capability sequence.
- `generate_workbooks.py` regenerates and structurally validates both
  workbooks.

## Reproduction

From the repository root:

```bash
python benchmarks/agents/scenarios/manufacturing-planning-001/generate_workbooks.py
```

The frozen reference results were independently checked with the production
Optees capabilities. The direct task has optimum `A = 24`, `B = 3`, objective
`1125`. The orchestration task forecasts demand `A = 18`, `B = 13.8` and has
integer production optimum `A = 18`, `B = 6`, objective `1050`.

An exploratory Claude Cowork run and its generated reports are archived in
[`claude-cowork-manufacturing-2026-07-18`](../../studies/claude-cowork-manufacturing-2026-07-18/README.md).

An exploratory local Qwen run through the Ollama D0 harness is archived in
[`qwen-ollama-manufacturing-2026-07-20`](../../studies/qwen-ollama-manufacturing-2026-07-20/README.md).
That run uses the same direct-task numbers in its prompt and therefore validates
the agent-to-Optees execution loop, not workbook extraction.
