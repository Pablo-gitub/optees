# Development Setup

This guide creates the same Optees Python 3.12 development environment on
macOS, Windows, and Linux after cloning the repository. The environment name is
only a local convenience; packaged Optees applications do not depend on Conda.

## Common Conda Setup

Install a current Conda-compatible distribution such as Miniforge, Miniconda,
or Anaconda. Then clone Optees and create the checked-in environment:

```bash
git clone https://github.com/Pablo-gitub/optees.git
cd optees
conda env create --file environment.yml
conda activate optees
python -m optees.main
```

These commands are the canonical setup on macOS, Windows, and Linux. Run them
from Terminal on macOS/Linux or from Anaconda Prompt/PowerShell on Windows.
`environment.yml` installs the desktop, plotting, local REST service, MCP,
testing, and development dependencies in editable mode.

When `environment.yml` changes, synchronize an existing checkout with:

```bash
conda env update --name optees --file environment.yml --prune
conda activate optees
```

Verify the environment:

```bash
python -c "import optees; print(optees.__version__)"
python -m ruff check src tests
python -m pytest -q -m "not benchmark"
```

See [TESTING.md](TESTING.md) for the authoritative test groups and commands.

## Platform Prerequisites

### macOS

Install Git and the Command Line Tools if they are not already available:

```bash
xcode-select --install
```

Apple Silicon is the packaged macOS target, but source development is not tied
to the packaged release architecture.

### Windows 10/11

Install Git for Windows and a Conda-compatible distribution. Use a normal
Anaconda Prompt or PowerShell session; administrator privileges are not
required for the source environment.

If PowerShell has not been initialized for Conda, run this once from Anaconda
Prompt and then restart PowerShell:

```powershell
conda init powershell
```

### Ubuntu 24.04

Install Git, build tools, and the system libraries used by Qt:

```bash
sudo apt update
sudo apt install -y \
  git build-essential libdbus-1-3 libegl1 libfontconfig1 libgl1 \
  libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
  libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
  libxcb-shape0 libxcb-xfixes0
```

Other Linux distributions require equivalent packages from their native
package manager.

## Standard Python Virtual Environment

Conda is optional. With Python 3.12 available, clone the repository and create
a virtual environment:

```bash
git clone https://github.com/Pablo-gitub/optees.git
cd optees
python3.12 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Or activate it from PowerShell on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then use the same installation and launch commands on every platform:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[plot,local-service,mcp,test,dev]"
python -m optees.main
```

The checked-in Conda environment remains the preferred reproducible workflow
because it also pins the Python minor version.

## Linux Graphics Diagnostics

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
the native `.deb` package and portable AppImage separately.
