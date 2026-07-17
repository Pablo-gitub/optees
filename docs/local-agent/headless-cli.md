# Optees Headless CLI

The headless CLI is the first external adapter over the local optimization
service. It executes the same application use cases as the desktop without
starting Qt and emits versioned, machine-readable contracts.

## Commands

When Optees is installed, use the `optees-cli` entry point. From a source
checkout, the equivalent command is `PYTHONPATH=src python -m optees.cli`.

```bash
optees-cli list-capabilities
optees-cli validate lp.continuous problem.json
optees-cli solve lp.continuous problem.json
```

Use `-` or omit the input argument to read one JSON object from stdin:

```bash
optees-cli solve lp.continuous - < problem.json
cat problem.json | optees-cli validate lp.continuous
```

`list-capabilities` returns the registered capability descriptors, their
contract versions, JSON schemas, availability, backend candidates, defaults,
and supported execution controls. Backend candidates are diagnostic metadata;
clients select the mathematical capability, not a concrete backend.

`validate` parses the versioned problem contract without running the solver.
Validation can therefore succeed while reporting `available: false` when the
payload is valid but an optional runtime dependency is unavailable.

`solve` validates the input, invokes the registered use case, and returns a
versioned execution envelope. Mathematical outcomes such as `infeasible` and
`unbounded` are valid execution envelopes, not technical error envelopes.

## Output Discipline

Operational commands write exactly one compact JSON document followed by a
newline to stdout. Clients should parse stdout and use the process exit code to
classify the outcome.

Human diagnostics are written to stderr. They deliberately avoid echoing the
complete input, file paths, solver exception text, or datasets. Unexpected
backend output is suppressed and replaced by a generic diagnostic; structured
solver diagnostics remain available in the JSON envelope.

`--help` is the only intentionally human-readable stdout mode.

## Stable Exit Codes

| Code | Meaning |
| ---: | --- |
| `0` | Valid request with an optimal or feasible result, successful validation, or successful discovery |
| `2` | Invalid command, JSON, or problem payload |
| `3` | Capability missing or unavailable in this installation |
| `4` | Mathematically infeasible problem |
| `5` | Cancelled execution or unsupported cancellation request |
| `6` | Technical execution or internal failure |
| `7` | Mathematically unbounded problem |
| `8` | Solver completed without a usable mathematical solution |

Callers must still inspect `job_status`, `mathematical_status`, and
`termination_reason`. Exit codes are process-level routing aids and do not
replace the versioned result contract.

## Current Scope

The registry currently exposes `lp.continuous`, `knapsack.zero_one`,
`knapsack.bounded`, `knapsack.unbounded`, and `knapsack.fractional`. It
also exposes `knapsack.multi_dimensional` for binary, bounded, unbounded, and
fractional quantity domains, `milp.linear` for mixed-integer linear models, and
`graph.shortest_path.dijkstra` for directed or undirected graphs with finite
non-negative weights, and `nlp.continuous_local` for safe-expression continuous
nonlinear optimization. NLP results are local numerical candidates and are not
global-optimality certificates. Educational supervised learning is available
through `ml.regression.linear` and `ml.classification.binary_logistic`, with
deterministic splits, coefficients, metrics, and row-level predictions. The
service intentionally has no HTTP server, queue, persistent job state,
arbitrary code execution, or unrestricted problem-format conversion.
Additional capabilities are migrated through the same registry and facade one
contract at a time.
