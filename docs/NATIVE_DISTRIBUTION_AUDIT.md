# Native Distribution Factual Audit

This audit records the behavior that can be established from the current
source, release workflow, and package contracts. Clean-account observations
remain explicitly separate: source inspection cannot prove how a particular
desktop shell, Gatekeeper, SmartScreen, or Linux association handles a file.

## Current Release Artifacts

| Platform | Published artifact | Contract established by the build |
| --- | --- | --- |
| Windows x64 | `optees-windows-x64.zip` | Portable PyInstaller onedir archive; no registration, fixed install location, shortcut, or uninstaller |
| macOS arm64 | `optees-macos-arm64.dmg` | Disk image containing `optees.app` and an `/Applications` shortcut; replacement remains a drag operation |
| Linux x86_64 | `optees-linux-x86_64.AppImage` | Portable executable created from the PyInstaller onedir build; no package-manager installation |

The release workflow smoke-tests the PyInstaller directory before creating the
final ZIP, DMG, or AppImage. It currently verifies service health and capability
discovery, not a completed solver job against the final downloadable artifact.

## Current Update Handoff

1. `CheckForUpdatesUseCase` selects one exact asset name for the detected
   platform and architecture.
2. `UpdateController` stages the download under the operating-system temporary
   directory at `optees-updates/<version>/`.
3. `GitHubUpdateProvider` writes `<asset>.part`, optionally verifies SHA-256,
   then atomically renames the partial file to the final staged name.
4. `QDesktopServices` asks the operating system to open the downloaded file.
5. Optees exits 500 ms after the open request is accepted.

Typical staging roots are `%TEMP%\\optees-updates\\<version>` on Windows and
the platform temporary directory followed by `optees-updates/<version>` on
macOS and Linux. This is not a persistent installed-application directory.

The open request is only an update handoff:

- a Windows ZIP still needs extraction and replacement by the user;
- a macOS DMG still needs mounting and a drag/replace operation;
- an AppImage still needs placement in a persistent user-selected location and
  may depend on desktop file associations when opened indirectly.

The exact application opened and the visible prompts must be recorded in the
clean-account acceptance matrix for each operating system.

## Verification Behavior

- Final release artifacts receive entries in `SHA256SUMS`.
- A checksum mismatch deletes the partial download and fails the update.
- If `SHA256SUMS` is absent, the current implementation accepts an unverified
  download.
- If `SHA256SUMS` exists but has no entry for the selected asset, the current
  implementation also accepts the download. This fail-open path is a P0 defect.
- Download size is not currently bounded against release metadata.

## User Data And Configuration

The language preference uses Qt `QSettings("optees", "optees")`, which stores
configuration in the operating system's user settings location rather than in
the replaceable PyInstaller directory. The local-service bearer token is
generated per process session and is not persisted. Optees does not currently
own a persistent project-data directory; imported problem files remain
user-owned.

Clean-account tests must still confirm the concrete settings path and survival
across replacement and uninstall on each supported platform.

## Manual Acceptance Record

| Check | Windows 10/11 | macOS 14+ arm64 | Ubuntu LTS | Other Linux desktop |
| --- | --- | --- | --- | --- |
| Downloaded artifact starts | Pending | Pending | Pending | Pending |
| Visible first-launch security behavior recorded | Pending | Pending | Pending | Pending |
| Update file location recorded | Pending | Pending | Pending | Pending |
| Application opened by update handoff recorded | Pending | Pending | Pending | Pending |
| Existing version replacement completed | Pending | Pending | Pending | Pending |
| Settings survive replacement | Pending | Pending | Pending | Pending |
| Solver job succeeds from final artifact | Pending | Pending | Pending | Pending |
| Local authenticated service succeeds | Pending | Pending | Pending | Pending |
| Removal behavior recorded | Pending | Pending | Pending | Pending |

## Confirmed P0 Gaps

1. The release workflow is tag-only and has no independent CI gate for the
   exact release commit.
2. Python and packaging tools are installed from rolling compatible versions.
3. AppImageKit is obtained from an unpinned continuous release.
4. Windows has a portable ZIP, not a native installer.
5. Checksum lookup fails open when an entry is missing.
6. Smoke tests do not execute a real solver job from each final artifact.
7. The UI closes after an operating-system open request, before installation or
   replacement can be confirmed.
