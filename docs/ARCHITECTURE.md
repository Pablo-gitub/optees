# Optees Architecture

Optees is a desktop, open-source tool to help technical and non-technical staff solve optimization problems with a clean, testable, and scalable architecture.

## Goals
- Clear separation of concerns (Clean Architecture)
- Easy to test (TDD), easy to extend
- Source-agnostic core (files, GUI, adapters)
- Prefer robust, well-maintained libraries; don’t reinvent the wheel

## Layered Model (6 layers)

### Responsibilities

* **Domain**
  Pure business logic & domain entities (Entities & Managers). No I/O, no library APIs.

* **Application**
  Use Cases orchestrate flows (parse → preprocess → solve → analyze → format). Services wrap solver calls (LP, MILP, Knapsack…). No UI or file format knowledge.

* **Data**
  Repositories + Adapters handling external resources: CSV/XLSX, MPS/MAT, Burkardt text, etc. Convert into *canonical dicts* for the Application layer.

* **Presentation**
  GUI (e.g., PyQt) – Views/Controllers. Only talks to Application Use Cases and maps DTOs ⇄ UI widgets.

* **Core**
  Project-specific shared utilities: logging, string management, config, global constants, error types.

* **Utility**
  Generic, reusable helpers: numerical routines, small algorithms. No project coupling.

### Canonical LP Problem (example)

Adapters should convert external data into:

```python
problem = {
  "sense": "min" | "max",
  "c": [...],
  "A_ub": [[...], ...], "b_ub": [...],     # optional
  "A_eq": [[...], ...], "b_eq": [...],     # optional
  "bounds": [[lb, ub], ...],               # optional; default (0, +inf)
  "var_names": ["x0","x1",...],            # optional
  "obj_offset": 0.0                        # optional
}
```

### Suggested folders

```
assets/
src/optees/
  application/
  core/
  data/
    adapters/
    repositories/
  domain/
  presentation/
  utility/
    io_lpnetlib.py
    io_knapsack.py
    lp_utils.py
    knapsack_utils.py
tests/
  application/
  data/
  utility/
docs/
```
