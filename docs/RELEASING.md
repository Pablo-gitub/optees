# Releasing Optees

This document closes the loop between the source version, packaged application,
GitHub Release, and in-app update checker.

## Release Invariants

For a release `vX.Y.Z`:

1. `src/optees/__init__.py` must contain `__version__ = "X.Y.Z"`.
2. The Git tag `vX.Y.Z` must point to the commit containing that version.
3. `optees.spec` imports the same version for the macOS bundle metadata; do not
   insert a version string into the spec file.
4. The GitHub Release must include the platform artifacts and `SHA256SUMS`.

The in-app updater compares the installed `__version__` with the latest GitHub
Release tag, selects a platform-specific artifact, and verifies the download
against `SHA256SUMS` when that asset is present.

## Pre-Release Verification

Run this from the project root in the `optees` environment:

```bash
PYTHONPATH=src python -m pytest -q
python -m PyInstaller optees.spec --noconfirm --clean
```

On macOS, verify the bundle version and the required runtime assets:

```bash
plutil -p dist/optees.app/Contents/Info.plist
test -f dist/optees.app/Contents/Resources/assets/i18n/en.json
test -f dist/optees.app/Contents/Resources/assets/i18n/it.json
test -f dist/optees.app/Contents/Resources/assets/icons/assistant.png
```

`CFBundleVersion` and `CFBundleShortVersionString` must equal the version in
`src/optees/__init__.py`. The command also verifies that PyInstaller bundles
the JSON locales and the Modeling Assistant icon.

For a local smoke launch without opening a visible desktop window, use a
short-lived offscreen process only as an additional diagnostic. The normal
manual acceptance test remains launching the generated `.app` on macOS.

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
| Windows x64 | `optees-windows-x64.zip` |
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
the operating system, and then closes Optees. Platform installation remains an
operating-system workflow: dragging the app from a DMG on macOS, extracting the
Windows archive, or replacing/running the AppImage on Linux. It does not
silently overwrite a running installation.
