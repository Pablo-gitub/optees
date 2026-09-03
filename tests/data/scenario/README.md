# Linear Scenario Min-Max and Max-Min Handoff Fixtures

## Overview

This directory contains deterministic, domain-neutral reference fixtures, invalid probes,
and tampered validation test cases for finite linear scenario optimization in Optees
(`scenario.linear.min_max_loss` and `scenario.linear.max_min_reward`).

These fixtures serve as the frozen handoff baseline for downstream consumers, including the
Decision Simulator, enabling independent verification and regression testing without any
runtime dependency on the Optees codebase.

## Normative Content and Tolerances

- **Normative specifications**:
  - `problem` definitions comply strictly with Problem Schema Version 1 (`contract_version: "1"`).
  - `expected_public_result` definitions comply strictly with Result Schema Version 1.
  - `mathematical_status` values (`optimal`, `infeasible`, `unbounded`) are exact string enums.
  - `binding_scenario_ids` lists are exact, deterministically ordered sequences.
  - Detail error codes (`scenario.*`) and validation check codes (`scenario.*`) are exact strings.

- **Tolerance-based numerical comparisons**:
  - Continuous optimization results (`guaranteed_value`, `variables.*.value`, `scenario_values.*.value`)
    are subject to floating-point solver tolerances. Numerical assertions should use relative
    and absolute tolerances (e.g. `abs=1e-5, rel=1e-5`).
  - Binding scenario identification uses the model's configured `binding_tolerance` (default `1e-6`).

## Limitations

- **Feasible Incumbent and Time Limit**:
  Timeouts and intermediate feasible incumbents depend non-deterministically on CPU clock speed,
  machine load, and OS scheduling across heterogeneous test platforms. To prevent fragile or
  fabricated artifacts, golden outputs for solver timeouts are not frozen as universal byte-exact
  fixtures. The contract specifies status mappings should a backend encounter them.

## Verification of Hashes

Every file in this directory is cataloged in `manifest.json`.

1. **Individual file hashes**:
   Each file digest is computed as lowercase SHA-256 over raw file bytes:
   ```bash
   sha256sum reference_cases.json README.md
   ```
2. **Aggregate manifest hash**:
   The `aggregate_sha256` in `manifest.json` is computed as the SHA-256 digest of the
   lexicographically ordered file entries formatted as:
   ```
   <sha256>  <relative_path>\n
   ```

## Decision Simulator Handoff Instructions

Downstream consumers (such as the Decision Simulator) should:
1. Copy the fixture bundle (`reference_cases.json`, `README.md`, `manifest.json`) into their repository.
2. Record the exact producer Git commit hash, Optees version (`0.10.2`), and baseline commit
   (`d6fa7afecca8dae9755741ed37db09308fcdde6c`) in their vendor or provenance metadata.
3. Verify file bytes against the recorded SHA-256 digests in `manifest.json`.
4. Run their local scenario and policy evaluations against these fixtures without importing
   internal Optees Python modules.
