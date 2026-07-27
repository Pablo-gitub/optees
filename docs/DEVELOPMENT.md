# Development Setup

This guide creates a reproducible Optees source environment after cloning the
repository. The environment name is only a local convenience; Optees does not
depend on Conda at runtime.

## Ubuntu 24.04

Install Git, build tools, and the system libraries used by Qt:

```bash
sudo apt update
sudo apt install -y \
  git build-essential libegl1 libgl1 libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xfixes0
```

Clone the repository and create the checked-in Conda environment:

```bash
git clone git@github.com:Pablo-gitub/optees.git
cd optees
conda env create --file environment.yml
conda activate optees
python -m optees.main
```

When `environment.yml` changes, synchronize an existing environment with:

```bash
conda env update --name optees --file environment.yml --prune
```

Run focused checks before the complete suite:

```bash
python -m ruff check src tests
python -m pytest -q -m "not benchmark"
```

See [TESTING.md](TESTING.md) for the authoritative test groups and commands.

## Standard Python Virtual Environment

Conda is optional. With Python 3.12 available:

```bash
git clone https://github.com/Pablo-gitub/optees.git
cd optees
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[plot,local-service,mcp,test,dev]"
python -m optees.main
```

## Ubuntu Graphics Diagnostics

First confirm that the source environment starts normally. If Qt fails before
the window appears, capture the complete terminal output:

```bash
QT_DEBUG_PLUGINS=1 python -m optees.main 2>&1 | tee optees-qt.log
```

To distinguish a GPU/driver problem from an application problem, retry with
software rendering:

```bash
QT_OPENGL=software LIBGL_ALWAYS_SOFTWARE=1 \
  python -m optees.main 2>&1 | tee optees-qt-software.log
```

Do not make software rendering the permanent default unless the normal OpenGL
path has been reproduced and diagnosed. The release acceptance matrix tests
both the native `.deb` package and the portable AppImage separately.
