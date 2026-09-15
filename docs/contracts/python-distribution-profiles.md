# Python Distribution Profiles Contract

## Status

- **Decision:** accepted for implementation
- **Gate:** `DIST-PY-C`
- **Scope:** Python dependency ownership, import boundaries, build targets, and
  clean-environment acceptance
- **Does not authorize:** publication to GitHub Releases or PyPI

## Invariants

All profiles install the same `optees` package and application version. Extras
may enable delivery surfaces but must not change capability IDs, schemas,
defaults, solver routing, result serialization, or independent validation.

`import optees`, `import optees.cli`, and construction of the local
`OptimizationService` must remain independent of Qt, HTTP, MCP, plotting, and
reporting dependencies. Missing optional dependencies must fail only when the
corresponding surface is requested, with a bounded installation hint.

## Frozen Profiles

| Profile | Dependency ownership | Required behavior |
| --- | --- | --- |
| Core | NumPy, SciPy, statsmodels, OR-Tools, OSQP | All registered mathematical capabilities and `optees-cli` |
| `plot` | Matplotlib | Headless artifact rendering through non-Qt backends |
| `desktop` | PySide6, certifi, Matplotlib, Markdown | GUI, updater TLS roots, interactive plots, and educational Markdown |
| `local-service` | FastAPI, Pydantic, Uvicorn, plus headless artifact/report dependencies | Authenticated REST jobs, artifacts, and reports |
| `mcp` | MCP SDK, Pydantic, plus headless artifact/report dependencies | MCP stdio jobs, artifacts, reports, and explicit downloads |
| `test` | pytest family, HTTPX, and every dependency needed by the authoritative test groups | Repository verification, not an end-user runtime recommendation |
| `dev` | Ruff and build-time developer tools selected by the relevant work unit | Development only |

An `all` convenience extra may compose all end-user runtime profiles, but must
not become the documented default. Repeated dependency declarations across
extras are acceptable when they keep every extra independently installable.

## Dependency Audit

The current composition root eagerly imports every mathematical adapter.
Consequently NumPy, SciPy, statsmodels, OR-Tools, and OSQP remain core until the
capability registry gains a separately reviewed lazy-backend contract. Moving
one of them to an extra today would make capability discovery depend on the
selected installation profile and would violate the invariants above.

PySide6 imports are confined to `optees.main`, `optees.presentation`, and the
Qt-oriented modules under `optees.core`. Matplotlib has two roles: Qt-backed
desktop plots and Agg-backed headless artifacts. FastAPI and Uvicorn belong to
the REST entry point. The MCP adapter uses both the MCP SDK and Pydantic.
Certifi is used by the desktop update adapter. Markdown is used for desktop
educational content and is not needed by mathematical execution.

Import probes on Python 3.12 confirm that these imports load none of PySide6,
FastAPI, Uvicorn, Pydantic, MCP, Matplotlib, or Markdown:

- `optees`;
- `optees.cli`;
- `optees.composition.local_agent`;
- local optimization-service construction and a zero-one Knapsack solve.

This invariant is executable in
`tests/packaging/test_python_distribution_profiles.py`.

## Python And Platform Matrix

The package continues to require Python 3.12 or newer. The first distribution
acceptance matrix is deliberately the already supported native matrix:

| Target | Architecture | Required clean-wheel evidence |
| --- | --- | --- |
| Ubuntu 22.04 | x86-64 | core, each optional profile, combined runtime |
| Windows latest | x86-64 | core, each optional profile, combined runtime |
| macOS 14 | arm64 | core, each optional profile, combined runtime |

The current release workflow demonstrates that the compiled dependencies can
be resolved together on these targets with Python 3.12; it does not yet prove
that a built Optees wheel is complete. `DIST-PY-W` must build and install the
wheel in clean environments on the matrix rather than treating a source-tree
installation as equivalent evidence.

The constraints already frozen in `pyproject.toml` remain authoritative:
SciPy `>=1.16,<1.18`, statsmodels `>=0.14.6,<0.15`, and OSQP
`>=0.6.3,<1`. Unbounded NumPy, OR-Tools, PySide6, and Matplotlib declarations
must not be tightened speculatively. Any new bound requires a reproduced
compatibility failure or an explicit support decision, followed by the full
matrix.

## Build And Publication Decisions

- Build both wheel and source distribution from the canonical version in
  `optees.__version__`.
- Keep the CLI in the core wheel through the existing `optees-cli` entry point.
- Treat PyInstaller companions as native-distribution outputs, not wheel
  contents.
- Add wheel and source archive to GitHub Releases before considering PyPI.
- Require a separate package-name ownership and trusted-publishing review
  before the first PyPI upload.
- Never replace an already published file for the same version.

## Acceptance For `DIST-PY-W`

The implementation gate must prove, from built artifacts rather than the
checkout, that:

1. core metadata contains no PySide6, Qt, FastAPI, MCP, Matplotlib, or Markdown
   dependency;
2. core import, capability discovery, validation, and one independently
   validated solve succeed without importing optional stacks;
3. every extra is independently installable and its advertised entry point or
   service starts;
4. missing extras produce explicit diagnostics rather than import tracebacks;
5. package data, schemas, licenses, and required assets are present;
6. sdist-to-wheel reproduction and the combined runtime profile succeed on the
   supported platform matrix.

## Stop Conditions

Return to this contract if dependency separation changes discovery or solver
semantics, requires duplicate registries, makes an advertised extra incomplete,
or reveals a compiled dependency without a supported Python 3.12 wheel on one
of the declared targets.
