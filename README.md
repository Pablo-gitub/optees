# Optees

Optees is an open-source, cross-platform desktop application for formulating,
solving, and explaining operations-research models. It is designed for both
students learning the mathematics and practitioners who need an inspectable
optimization workflow.

## Available Today

- Continuous Linear Programming through SciPy/HiGHS, including optimal ranges
  when multiple optima exist.
- Mixed-Integer Linear Programming with continuous, integer, and binary
  variables through OR-Tools.
- 0/1, Bounded, Unbounded, Fractional, and Multi-dimensional Knapsack.
- Continuous Nonlinear Programming with safe scalar expressions, optional box
  bounds, BFGS/Nelder-Mead/L-BFGS-B, and an explicit local-candidate result
  contract.
- Dijkstra shortest paths on directed or undirected graphs with finite,
  non-negative weights.
- Educational linear regression with OLS and Ridge, deterministic train/test
  splits, MAE/MSE/RMSE/R-squared, residuals, and a one-feature fit chart.
- Versioned JSON import for LP, MILP, Knapsack, NLP, shortest-path, and
  regression
  formulations.
- An English/Italian local rule-based Modeling Assistant that recommends a
  solver family and can draft validated LP, MILP, and Knapsack JSON when the
  prompt contains sufficient data.
- Educational examples, mathematical explanations, result summaries, and
  visualizations for the implemented families.

The roadmap intentionally distinguishes shipped functionality from planned
expansion such as classification/clustering, heuristics, broader graph
algorithms, and global/nonlinear optimization methods.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Project roadmap](docs/PROJECT_ROADMAP.md)
- [Algorithms](docs/ALGORITHMS.md)
- [Datasets](docs/DATASETS.md)
- [Testing](docs/TESTING.md)
- [Release procedure](docs/RELEASING.md)
- [Website deployment](docs/WEBSITE_DEPLOYMENT.md)

## Run From Source

Optees requires Python 3.12 or later.

```bash
git clone https://github.com/Pablo-gitub/optees.git
cd optees
conda create -n optees python=3.12
conda activate optees
python -m pip install -e ".[plot]" pytest pytest-qt
python -m optees.main
```

To run the complete test suite from a source checkout:

```bash
PYTHONPATH=src python -m pytest -q
```

## Releases

Official desktop packages are published on the
[GitHub Releases page](https://github.com/Pablo-gitub/optees/releases).
The release workflow builds a macOS Apple Silicon DMG, a Windows x64 ZIP, and a
Linux x86_64 AppImage, each accompanied by `SHA256SUMS`.

Without Apple Developer ID credentials, macOS packages are ad-hoc signed and
Gatekeeper may require the user to explicitly open the application. See
[RELEASING.md](docs/RELEASING.md) for build, verification, signing, and tag
instructions.
