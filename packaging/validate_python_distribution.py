from __future__ import annotations

import argparse
import email.parser
import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


OPTIONAL_CORE_DEPENDENCIES = {
    "certifi",
    "fastapi",
    "markdown",
    "matplotlib",
    "mcp",
    "pydantic",
    "pyside6",
    "uvicorn",
}
REQUIRED_EXTRAS = {"all", "desktop", "dev", "local-service", "mcp", "plot", "test"}
REQUIRED_ENTRY_POINTS = {
    "optees",
    "optees-cli",
    "optees-mcp",
    "optees-ollama-chat",
    "optees-server",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate built Optees Python distributions.")
    parser.add_argument("artifact_directory", type=Path)
    parser.add_argument(
        "--rebuild-sdist",
        action="store_true",
        help="Build a second wheel from the sdist and compare its payload.",
    )
    args = parser.parse_args(argv)

    wheel = _exactly_one(args.artifact_directory, "optees-*.whl")
    source = _exactly_one(args.artifact_directory, "optees-*.tar.gz")
    version = _validate_wheel(wheel)
    _validate_sdist(source, version)
    if args.rebuild_sdist:
        _rebuild_and_compare(source, wheel)
    print(json.dumps({"ok": True, "version": version, "wheel": wheel.name, "sdist": source.name}))
    return 0


def _exactly_one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {pattern} in {directory}, found {len(matches)}.")
    return matches[0]


def _validate_wheel(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        _reject_unsafe_or_generated(names, archive_name=path.name)
        metadata_name = _exact_member(names, ".dist-info/METADATA")
        entry_points_name = _exact_member(names, ".dist-info/entry_points.txt")
        metadata = email.parser.BytesParser().parsebytes(archive.read(metadata_name))
        version = metadata.get("Version", "")
        if not version or path.name != f"optees-{version}-py3-none-any.whl":
            raise ValueError("Wheel filename and METADATA version do not agree.")

        extras = set(metadata.get_all("Provides-Extra", []))
        if not REQUIRED_EXTRAS <= extras:
            raise ValueError(f"Wheel is missing extras: {sorted(REQUIRED_EXTRAS - extras)}")
        for requirement in metadata.get_all("Requires-Dist", []):
            if (
                ";" not in requirement
                and _requirement_name(requirement) in OPTIONAL_CORE_DEPENDENCIES
            ):
                raise ValueError(f"Optional dependency leaked into core metadata: {requirement}")

        entry_points = archive.read(entry_points_name).decode("utf-8")
        missing_entries = {
            entry for entry in REQUIRED_ENTRY_POINTS if f"{entry} =" not in entry_points
        }
        if missing_entries:
            raise ValueError(f"Wheel is missing entry points: {sorted(missing_entries)}")
        required_files = {
            "optees/assets/i18n/en.json",
            "optees/assets/i18n/it.json",
            "optees/assets/reports/optees.typst",
        }
        if not required_files <= set(names):
            raise ValueError(
                f"Wheel is missing package data: {sorted(required_files - set(names))}"
            )
        if not any(name.endswith(".dist-info/licenses/LICENSE") for name in names):
            raise ValueError("Wheel does not contain LICENSE.")
        return version


def _validate_sdist(path: Path, version: str) -> None:
    expected_root = f"optees-{version}"
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        _reject_unsafe_or_generated(names, archive_name=path.name)
        required = {
            f"{expected_root}/LICENSE",
            f"{expected_root}/pyproject.toml",
            f"{expected_root}/src/optees/__init__.py",
            f"{expected_root}/src/optees/assets/i18n/en.json",
            f"{expected_root}/src/optees/assets/i18n/it.json",
        }
        if not required <= set(names):
            raise ValueError(f"Sdist is missing files: {sorted(required - set(names))}")


def _rebuild_and_compare(source: Path, original_wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="optees-sdist-rebuild-") as temporary:
        root = Path(temporary)
        with tarfile.open(source, "r:gz") as archive:
            archive.extractall(root, filter="data")
        source_root = next(path for path in root.iterdir() if path.is_dir())
        output = root / "wheel"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--outdir",
                str(output),
            ],
            cwd=source_root,
            check=True,
        )
        rebuilt = _exactly_one(output, "optees-*.whl")
        if _wheel_payload(original_wheel) != _wheel_payload(rebuilt):
            raise ValueError("Wheel rebuilt from the sdist has a different payload.")


def _wheel_payload(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {
            _normalized_wheel_member(name): archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/RECORD")
        }


def _normalized_wheel_member(name: str) -> str:
    if ".dist-info/" not in name:
        return name
    return ".dist-info/" + name.split(".dist-info/", 1)[1]


def _reject_unsafe_or_generated(names: list[str], *, archive_name: str) -> None:
    for name in names:
        path = PurePosixPath(name)
        lowered = name.lower()
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe archive member in {archive_name}: {name}")
        if "__pycache__" in path.parts or lowered.endswith((".pyc", ".pyo")):
            raise ValueError(f"Generated Python cache in {archive_name}: {name}")
        if any(part in {".git", ".env"} for part in path.parts):
            raise ValueError(f"Development or secret path in {archive_name}: {name}")


def _exact_member(names: list[str], suffix: str) -> str:
    matches = [name for name in names if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one archive member ending in {suffix}.")
    return matches[0]


def _requirement_name(requirement: str) -> str:
    return requirement.split("[", 1)[0].split(" ", 1)[0].split("<", 1)[0].split(">", 1)[0].lower()


if __name__ == "__main__":
    raise SystemExit(main())
