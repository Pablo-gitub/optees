# QP Consumer Handoff Evidence

- ID: `OPT-DS-QP-H`; status: implemented and independently reviewed.
- Owner: Gemini; independent review afterwards. No UI assignment.
- This is completion of existing QP handoff evidence, NOT OPT-DS-04 forecasting.
- Prerequisite: reviewed QP-I/QP-UI. Parent: [case-study roadmap](ROADMAP.md).

## Read and scope

Read AGENTS.md, architecture overview, testing/releasing guides, project roadmap,
case-study roadmap, QP contract and 02-qp-vertical-slice.md. Inspect QP production
codecs/service/validator and tests/data/qp plus the scenario manifest, README and
test_scenario_reference_cases.py. Inspect Git status before editing.

Add only tests/data/qp/manifest.json, tests/data/qp/README.md, focused QP manifest
tests and the relevant documentation/roadmaps. Existing QP fixture and example
bytes must remain unchanged. No solver, descriptor, transport, UI, dependency,
version bump, deployment workflow or simulator edits. In particular preserve
unrelated local changes to .github/workflows/deploy-website.yml.

## Required implementation

Use the scenario manifest's format and aggregation algorithm, not a parallel
hash convention. Document how its file paths are resolved; every manifest path
must refer to a real file within the repository, never an absolute local path.
Cover the QP reference cases and the standalone resource-allocation example,
plus the new README. Do not duplicate or rewrite those JSON files for convenience.
If the scenario convention cannot safely cover the external example path, use
an explicitly documented repository-root path base and test it; do not introduce
ambiguous mixed bases. The manifest must not hash itself.

Record manifest version, qp.continuous capability ID, problem/result/contract
versions read from production descriptors, actual Optees version and an existing
full Git commit identifying the tested baseline. Never invent a commit or use
the future manifest commit (self-reference). The fixture baseline identifies
evidence; it is NOT a requirement to execute precisely that historical commit.
Consumers record the actual executable version/commit/backend/options separately.

README must explain: supported continuous convex QP scope; objective convention
1/2 x^T Q x + c^T x; location of analytic cases, infeasible/invalid/tampered
cases and independent-validation expectations; numerical comparison rules from
existing tests; no bitwise cross-platform optimizer guarantee; offline checksum
verification; required environment/backend and explicit missing-dependency failure.
Do not present the standalone input example as a golden expected result unless
one already exists and is referenced accurately.

Tests must verify the real manifest, files and aggregate digest, compare versions
with production discovery, and run existing reference cases through production
code. Baseline SHA must resolve during authoring; do not require Git history in
installed-package tests or dynamically compare it to HEAD forever. Negative
tests must show a changed covered byte/path/hash is detected, without modifying
the committed source fixtures. Reuse existing checksum helpers where appropriate.

## Gate and stop

- [x] Planning scope, identity semantics and evidence frozen.
- [x] Manifest and README complete; original fixture bytes preserved.
- [x] Production QP reference tests and manifest corruption tests pass.
- [x] Focused Ruff/format and diff checks pass; documentation links verified.
- [x] Independent review accepted after correcting the meaning of partial
  validation: no independent KKT/stationarity check is performed without dual
  data. A production-service regression verifies this; README and aggregate
  manifest hashes were refreshed without changing the original JSON fixtures.

Review evidence: all 11 QP fixture/manifest tests pass; focused Ruff/format and
diff checks pass. No solver or public contract changed.

Run the QP reference tests and new focused tests using the configured optees
environment with PYTHONPATH=src; apply docs/guides/testing.md for any broader
test needs. No live network or native package build is needed for this evidence
work. Report exact commands, results and baseline SHA. Update general and detailed
roadmaps before one local atomic commit; no AI attribution or push. Stop after
handoff. Forecasting, MIQP and registry remain unauthorized by this block.
