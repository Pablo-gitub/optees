# Nonlinear Programming Feature Plan

## Document Status

- **State:** maintenance
- **Shipped baseline:** the continuous, box-bounded local-optimization vertical
  slice with desktop, JSON, tests, and educational material
- **Remaining scope:** external benchmark hardening; nonlinear constraints,
  least squares, quadratic programming, minimax, and global methods are later
  family expansions
- **Result boundary:** a converged candidate is not a proof of global optimality

This document is the implementation contract for **Phase 1: Nonlinear
Programming**. It deliberately starts with one complete, continuous,
single-objective workflow instead of exposing several incomplete NLP methods.

`docs/roadmaps/project.md` owns product sequencing; this document owns the
technical checklist for the first NLP vertical slice.

## Scope And Mathematical Contract

The first released NLP model is the continuous problem

```text
minimize or maximize    f(x)
subject to              l_i <= x_i <= u_i,  i = 1, ..., n
                         x in R^n
```

where `f` is a scalar nonlinear expression and each bound may be absent. A
maximization is solved internally as `minimize -f(x)` and is reported again in
the original sense.

The solver returns a **local numerical candidate**. `Converged` means that the
selected numerical method met its termination criterion; it never proves that
no better point exists elsewhere in the feasible region. The UI, result model,
examples, and documentation must preserve this distinction.

### Included

- continuous decision variables;
- optional lower and upper bounds;
- a required feasible initial point;
- a scalar objective with `min` or `max` sense;
- BFGS and Nelder-Mead for unbounded formulations;
- L-BFGS-B for box-bounded formulations;
- objective-expression validation, JSON import/export, formulation and result
  views, localized educational content, and regression coverage.

### Explicitly Deferred

- nonlinear equality or inequality constraints;
- least-squares, quadratic-programming, and root-finding workflows;
- global optimization, nonlinear min-max/max-min, and multi-objective NLP;
- automatic/symbolic derivatives and user-provided Python functions;
- LLM-generated NLP drafts in the Modeling Assistant.

Nonlinear constraints and global methods become Phase 4 work only after this
contract has stable tests and user-facing terminology.

## Safety And Numerical Rules

1. **No `eval`, `exec`, imports, attributes, indexing, comprehensions, or
   lambdas.** The expression field is parsed as Python syntax but evaluated by
   a small, explicit AST interpreter with an empty execution environment.
2. The initial point must have one finite numeric value per variable and must
   satisfy every declared bound before a solver is called.
3. Each objective evaluation must produce a finite scalar. Division by zero,
   an invalid domain such as `log(-1)`, and `NaN`/infinity terminate safely with
   an explanatory failure, never a fabricated solution.
4. Method capabilities are validated before execution. The first slice keeps
   BFGS and Nelder-Mead unbounded even though SciPy may support additional
   behaviour for some methods; L-BFGS-B is the dedicated bounded method.
5. Numeric tolerances in tests are asserted with documented absolute/relative
   tolerances, not fragile exact floating-point equality.

The initial method selection reflects the maintained
[`scipy.optimize.minimize` API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html):
it minimizes scalar objectives from an initial vector and exposes BFGS,
Nelder-Mead, and L-BFGS-B. L-BFGS-B is the bounded method in this first
contract.

## Stable Data Contracts

### Domain Objects

```text
NLPVariable
  name: str                 # unique, e.g. x1
  label: str                # optional user-facing description
  lower_bound: float | None
  upper_bound: float | None
  initial_value: float

NLPObjective
  expression: str
  sense: MIN | MAX

NLPOptions
  method: BFGS | NELDER_MEAD | L_BFGS_B
  max_iterations: int
  tolerance: float | None

NLPModel
  variables: tuple[NLPVariable, ...]
  objective: NLPObjective
  options: NLPOptions

NLPSolution
  status: CONVERGED | ITERATION_LIMIT | FAILED | NOT_SOLVED
  objective_value: float | None
  variable_values: dict[str, float]
  iterations: int | None
  evaluations: int | None
  termination_message: str | None
  convergence_history: tuple[float, ...]
```

The final names can follow local conventions, but the meanings above are
public behaviour. `Optimal` must not be used as an NLP result status.

### Canonical Solver Dictionary

The use case maps the domain model to a framework-neutral payload:

```python
{
    "sense": "min" | "max",
    "expression": "(x1 - 2)**2 + (x2 + 1)**2",
    "variables": ["x1", "x2"],
    "initial_point": [0.0, 0.0],
    "bounds": [(None, None), (0.0, 5.0)],
    "method": "BFGS" | "Nelder-Mead" | "L-BFGS-B",
    "max_iterations": 1_000,
    "tolerance": 1e-8,
}
```

The `NLPSolverPort` consumes and returns only this contract. The SciPy adapter
is the only layer allowed to know `scipy.optimize.OptimizeResult`.

### Versioned JSON

The NLP JSON format starts at version `"1"`:

```json
{
  "version": "1",
  "problem_type": "nonlinear_programming",
  "variables": [
    {"name": "x1", "label": "first coordinate", "lb": null, "ub": null,
     "initial": -1.2}
  ],
  "objective": {"sense": "min", "expression": "(1 - x1)**2"},
  "solver_options": {"method": "BFGS", "max_iterations": 1000,
                     "tolerance": 1e-8}
}
```

The JSON reader uses the same domain and expression validation as manual input.
No JSON field can bypass those invariants.

## Sequential Delivery Checklist

### 1. Foundation: Domain And Safe Expressions

- [x] Add NLP value objects, model, solution, and solver-status definitions
      under `src/optees/domain/`.
- [x] Add a pure expression module under `src/optees/utility/` that parses a
      restricted AST and evaluates it against a supplied variable mapping.
- [x] Allow only numeric literals, declared variable names, parentheses,
      `+`, `-`, `*`, `/`, `**`, unary signs, and a documented small function
      set: `abs`, `sin`, `cos`, `tan`, `exp`, `log`, and `sqrt`.
- [x] Reject unknown names, unsupported syntax, non-finite constants, unsafe
      constructs, and invalid arithmetic with clear domain errors.
- [x] Test valid expressions, function domains, unknown variables, syntax
      errors, malicious-looking expressions, bound consistency, unique names,
      and initial-point feasibility.

**Exit criterion:** a model can be constructed and its objective evaluated
locally without SciPy or GUI imports.

### 2. Solver Port, Use Case, And SciPy Adapter

- [x] Add `NLPSolverPort`, `SolveNLPUseCase`, and `ScipyNLPSolverAdapter`
      following LP/MILP dependency direction.
- [x] Replace the legacy `solve_non_linear_problem` placeholder with a
      focused NLP utility or remove it after callers move to the port. Keep
      unrelated heuristic placeholders out of the NLP implementation.
- [x] Convert max objectives only at the adapter boundary and restore the
      original objective value before returning a result.
- [x] Map SciPy outcomes to `Converged`, `IterationLimit`, and `Failed` with
      raw method, iteration/evaluation counts, and termination message in
      extras.
- [x] Collect an objective history through a callback where the selected method
      supports it. An unavailable history is represented explicitly, never
      invented from the final value.
- [x] Test a convex quadratic, a bounded boundary solution, maximization,
      method/bounds incompatibility, non-finite objective values, solver
      exceptions, and forced iteration limits.

**Exit criterion:** canonical payloads solve deterministically through the
port and produce honest numerical statuses.

### 3. Reference Cases And Dataset Policy

- [x] Add small, source-documented analytic reference cases under
      `tests/data/nlp/` with expected minimizers, objective values, starting
      points, and method/tolerance budget.
- [x] Cover Rosenbrock, Himmelblau, a bounded nonlinear quadratic, and a
      maximization case. Use one intended basin for multi-modal Himmelblau;
      tests must not assume a unique global point where one does not exist.
- [x] Add unit and end-to-end regressions that validate finite objective,
      feasibility, expected basin/value tolerance, and result wording.
- [x] Extend `docs/reference/datasets.md` to call these **analytic reference cases**,
      not scientific benchmark files, until a redistributable external NLP
      corpus with published results is included.

**Exit criterion:** every supported solver path has a stable, documented
numerical regression case suitable for normal CI.

### Deferred: External Scientific Benchmark Integration

- [ ] Select a redistributable continuous-NLP corpus with published reference
      information and compatible usage terms.
- [ ] Document whether each case verifies a local basin, a known global value,
      feasibility, or numerical robustness; current local methods must never
      be evaluated as if they proved a global optimum.
- [ ] Add source metadata, checksum, parser or adapter boundaries, and a small
      deterministic CI subset. Mark larger performance cases separately.

This work belongs to the cross-family benchmark-hardening phase in
`docs/roadmaps/project.md`; analytic reference cases remain mandatory for this
first vertical slice.

### 4. JSON Import And Export

- [x] Implement `nlp_json_io.py` with `load`, `dump`, structural validation,
      and conversion to/from `NLPModel`.
- [x] Add a JSON example under `examples/`; i18n-backed import help belongs to
      the formulation workflow.
- [x] Test valid round trips, schema-version errors, unknown methods, unsafe
      expressions, invalid initial points, and no-loss conversion of bounds.

**Exit criterion:** manually entered and imported formulations follow the same
validation route and can reproduce each other.

### 5. Formulation Workflow

- [x] Add `NLPView` and controller/main-window routing using the LP/MILP
      composition and theme conventions.
- [x] Provide variable rows with name/description, lower and upper bounds, and
      initial value. Add/delete behaviour keeps objective variable references
      valid or reports them clearly.
- [x] Provide expression input, min/max selector, method selector, iteration
      cap, tolerance, JSON import, and a compact info action for each
      non-obvious field.
- [x] Dynamically explain capability restrictions: bounded models select
      L-BFGS-B; unbounded models may select BFGS or Nelder-Mead.
- [x] Validate before navigation and preserve the user formulation when
      validation fails.
- [x] Add presentation tests for initial render, edit/solve flow, validation,
      import flow, and both English and Italian labels.

**Exit criterion:** a user can formulate and solve every reference case without
editing JSON.

### 6. Solution Workflow

- [x] Add an NLP solution view distinct from LP/MILP result pages.
- [x] Show method, local candidate, original-sense objective, status,
      iterations/evaluations, termination reason, and bounds feasibility.
- [x] Display the convergence trace only when it was captured; otherwise show
      that the chosen method did not provide a trace.
- [x] State in the UI that convergence is local and depends on initial point
      and method; never render an “optimal” badge for this phase.
- [x] Test converged, iteration-limited, invalid, and failed result rendering.

**Exit criterion:** the visible result gives a technically correct explanation
of what the numerical run established.

### 7. Education, Assistant, QA, And Release

- [x] Add English and Italian Example and Problem Description pages covering
      local minima, initial points, bounds, method choice, and the reference
      functions.
- [x] Add JSON, solver-option, expression, and solution-status info dialogs
      consistent with LP/MILP/Knapsack UI.
- [x] Update the rule-based Modeling Assistant so it labels NLP as available
      after the view ships; structured NLP drafting remains deferred.
- [x] Update `docs/reference/algorithms.md`, `docs/reference/datasets.md`, and the project roadmap
      to reflect only implemented behaviour. Tag-specific release notes remain
      part of the release commit/tag workflow.
- [x] Run the full test suite, build the desktop bundle, check i18n/docs/icons
      are included, and run an offscreen smoke start before tagging a release.

**Exit criterion:** NLP meets the Product Standard in
`docs/roadmaps/project.md` and no UI element advertises a deferred NLP feature.

## Test Matrix

| Layer | Required coverage |
| --- | --- |
| Expression safety | valid arithmetic/functions, variables, unsupported AST, invalid domains, non-finite values |
| Domain | bounds, names, initial point, method capability, objective sense |
| Application | canonical mapping and result mapping without SciPy |
| Adapter | quadratic convergence, bounded minimum, max conversion, limits, failures |
| JSON | version, schema, round trip, shared validation |
| Presentation | formulation, import, validation, solution states, EN/IT text |
| Regression | Rosenbrock, Himmelblau basin, bounded quadratic, maximization |
| Packaging | full suite, bundle asset inspection, offscreen startup |

## Commit Boundaries

Keep commits reviewable and independently testable:

1. `Add safe nonlinear domain model and expression evaluator`
2. `Solve continuous nonlinear programs with SciPy`
3. `Add nonlinear optimization reference cases and JSON import`
4. `Add nonlinear programming formulation workflow`
5. `Show continuous nonlinear optimization results`
6. `Document and localize nonlinear programming workflow`
7. `Verify nonlinear programming release readiness`

The exact split may merge adjacent small steps, but domain safety must never be
mixed with a large presentation change.

## Definition Of Done

Phase 1 is complete only when all checklist items are checked, the full suite
passes, the packaged application starts with NLP documentation available, and
the documentation accurately says that this is local continuous optimization
with box bounds rather than global or generally constrained NLP.
