# Releasing Optees

This document closes the loop between the source version, packaged application,
GitHub Release, and in-app update checker.

Every version tag is tested before packaging. The release workflow runs the
authoritative complete suite against the exact tagged commit; Windows, macOS,
and Linux builds cannot start unless that gate succeeds. Pull requests and
pushes to `main` also use the independent CI workflow documented in
`docs/TESTING.md`.

The current procedure describes the artifacts that exist today. Remaining
native-installer, updater, and packaged-acceptance hardening is tracked in
`docs/NATIVE_DISTRIBUTION_ROADMAP.md`; do not describe those planned
capabilities as already released.

## Reproducible Packaging Inputs

Runtime compatibility remains declared in `pyproject.toml`. Native-release
tools are intentionally separate and exactly pinned in
`packaging/requirements-build.txt`; changing those versions requires review and
new artifact verification on Windows, macOS, and Linux.

The Linux workflow downloads `appimagetool` 1.9.1 from the official
`AppImage/appimagetool` release and checks its published SHA-256 digest before
executing it. Do not replace this with a `continuous` or latest-release URL.

Every third-party GitHub Action is referenced by an immutable commit SHA, with
the corresponding major tag retained as an inline comment. Dependabot checks
these references weekly. Review proposed updates against the upstream release
notes and require CI to pass; packaging-related action updates also require a
new release-candidate artifact check before a stable tag is published.

## Release Invariants

For a stable release `vX.Y.Z` or candidate `vX.Y.Z-rc.N`:

1. `src/optees/__init__.py` must contain the PEP 440 equivalent: `X.Y.Z` for a
   stable release or `X.Y.ZrcN` for a candidate.
2. The corresponding Git tag must point to the commit containing that version.
   CI rejects mismatched stable and RC spellings before packaging.
3. `optees.spec` derives native numeric metadata from the same version; do not
   insert a version string into the spec file.
4. The GitHub Release must include the platform artifacts and `SHA256SUMS`.

The in-app updater compares the installed `__version__` with the latest GitHub
Release tag, selects a platform-specific artifact, and verifies the download
against `SHA256SUMS` when that asset is present.

## Pre-Release Verification

Run this from the project root in the `optees` environment:

```bash
PYTHONPATH=src python -m pytest -q
python -m pip install --requirement packaging/requirements-build.txt
python -m PyInstaller optees.spec --noconfirm --clean
```

On macOS, verify the bundle version and the required runtime assets:

```bash
plutil -p dist/optees.app/Contents/Info.plist
test -f dist/optees.app/Contents/Resources/assets/i18n/en.json
test -f dist/optees.app/Contents/Resources/assets/i18n/it.json
test -f dist/optees.app/Contents/Resources/assets/icons/assistant.png
```

`CFBundleVersion` and `CFBundleShortVersionString` must equal the numeric base
version in `src/optees/__init__.py`; candidate identity remains available in
`CFBundleGetInfoString` and in the application. The command also verifies that
PyInstaller bundles the JSON locales and the Modeling Assistant icon.

For a local smoke launch without opening a visible desktop window, use a
short-lived offscreen process only as an additional diagnostic. The normal
manual acceptance test remains launching the generated `.app` on macOS.

### Windows OR-Tools integrity

The Windows OR-Tools wheel keeps its native dependency closure in
`ortools/.libs`. `optees.spec` deliberately copies every file from that
directory and removes same-named DLLs that PyInstaller may have discovered
elsewhere on the runner. This prevents a package that either misses
`ortools.dll` or combines it with unrelated Abseil/Protobuf builds.

The release workflow compares the SHA-256 hash of every bundled OR-Tools DLL
with the installed wheel before creating the native installer and portable
ZIP. A missing or different file fails the platform build. This integrity
check verifies bundle provenance; a future packaged `--selftest` command
should additionally execute a tiny MILP to verify runtime loading end to end.

## Publish A Release

After the version-bump commit and all checks succeed:

```bash
git push origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

Pushing the tag starts `.github/workflows/release.yml`. The workflow builds:

| Platform | Artifact |
| --- | --- |
| macOS 14+ Apple Silicon | `optees-macos-arm64.dmg` |
| Windows x64 | `optees-windows-x64-setup.exe` |
| Windows x64, portable | `optees-windows-x64-portable.zip` |
| Linux x86_64 | `optees-linux-x86_64.AppImage` |

The release job then creates `SHA256SUMS` and attaches it with the artifacts.
Check the completed GitHub Action and download the macOS DMG for a manual
install/update test before announcing the release.

## Signing And Update Handoff

When the Apple Developer ID and notarization secrets are configured, the macOS
workflow signs, notarizes, staples, and verifies the `.app`. Without them, it
ad-hoc signs the bundle; Gatekeeper may require right-clicking the application
and choosing **Open**.

The updater downloads and checksum-verifies the release artifact, opens it with
the operating system, and then closes Optees. On Windows, the preferred artifact
is the visible per-user Inno Setup installer; the ZIP remains an explicitly
portable fallback. On macOS and Linux, installation remains an operating-system
workflow: dragging the app from a DMG or replacing/running the AppImage. Optees
does not silently overwrite a running installation.
