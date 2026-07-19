# Qwen Ollama Manufacturing Study - 2026-07-20

This exploratory run tested whether the Optees Ollama D0 harness could turn a
natural-language manufacturing problem into a validated MILP execution through
the packaged Optees `0.9.0rc3` loopback service.

## Scope

The prompt contains all numerical inputs. Unlike the Claude Cowork study, this
run does **not** test workbook discovery or Excel extraction. It evaluates the
agent's capability discovery, model selection, payload construction,
validation, solver execution, result retrieval, and management-level Markdown
explanation.

## Recorded Environment

| Field | Value |
| --- | --- |
| Provider | Ollama, local |
| Client | Optees D0 terminal harness |
| Model | `qwen3.5:9b` |
| Model digest prefix | `6488c96fa5fa` |
| Optees version reported by the result | `0.9.0rc3` |
| Condition | Optees required |

## Result

The agent selected `milp.linear` and completed the expected tool sequence:

1. `optees_list_capabilities`
2. `optees_get_capability`
3. `optees_validate_problem`
4. `optees_create_job`
5. `optees_get_job_status`
6. `optees_get_job_result`

It reported Product A = 24, Product B = 3, and objective EUR 1,125. These
values match the private reference workbook for
[`manufacturing-planning-001`](../../scenarios/manufacturing-planning-001/README.md).
It also reported the solver status as `optimal` and the independent validation
status as `verified`.

## Manual Review

This is a successful exploratory integration run, but not yet a publishable
comparative benchmark:

- The capability choice, tool order, numerical result, resource slacks, and
  reported Optees version are correct.
- The response initially states an incorrect machine-hour total of 78, then
  immediately recalculates the same expression correctly as 60. The final
  table and recommendation use the correct value.
- The conclusion says global optimality is not guaranteed even after recording
  an `optimal` CP-SAT status and zero gap. Independent validation alone does not
  prove optimality, but the solver certificate supports the reported optimum;
  the wording should distinguish those two sources more cleanly.
- The original tool request/response payloads, latency, token usage, repeated
  trials, and an unaided control condition were not recorded.
- No spreadsheet was supplied to the harness, so this run must not be cited as
  evidence of Excel ingestion.

The complete user prompt, visible tool-event trace, and final response are
preserved in [`outputs/terminal-transcript.txt`](outputs/terminal-transcript.txt).
See `manifest.json` for machine-readable metadata and the transcript hash.
