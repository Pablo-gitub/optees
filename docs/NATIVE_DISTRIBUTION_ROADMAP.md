# Native Distribution And Update Roadmap

This document defines how Optees will move from downloadable platform bundles
to explicit, tested installation and update contracts. It covers release CI,
artifact reproducibility, native installation, update handoff, and acceptance
testing. It does not change solver behavior or the local-service API.

Implementation starts from `main` on a dedicated `codex/native-installers`
branch after the local solver platform has been merged. The current artifacts
remain available until their replacements pass the acceptance matrix.
Source-derived baseline evidence and the manual clean-account matrix are kept
in [NATIVE_DISTRIBUTION_AUDIT.md](NATIVE_DISTRIBUTION_AUDIT.md).

## Current Baseline

| Platform | Current artifact | Current behavior | Main limitation |
| --- | --- | --- | --- |
| Windows x64 | ZIP containing a PyInstaller onedir build | Extract and run from any writable location | Portable bundle, not an installed application |
| macOS Apple Silicon | DMG containing `optees.app` and an Applications shortcut | User drags the app to Applications | Smooth first launch requires Developer ID signing and notarization |
| Linux x86_64 | AppImage | Mark executable and run from its current path | Portable file with no guaranteed desktop integration or persistent update location |

The application checks the latest stable GitHub Release, downloads the selected
asset into a temporary version directory, verifies it when a matching checksum
is available, opens it through the operating system, and closes Optees. Opening
an archive or disk image is only an update handoff; it is not proof that the new
version was installed.

## Product Contracts

Optees must use these terms consistently:

- **Portable package:** runs from a user-selected path and is not registered as
  an installed application.
- **Installer:** registers an application location, version, shortcuts, and an
  uninstall path according to platform conventions.
- **Update check:** discovers a newer compatible release.
- **Verified download:** a complete artifact whose expected checksum entry was
  found and matched.
- **Update handoff:** launches a native installer or presents explicit manual
  replacement steps.
- **Installed update:** verified only after the new application version starts
  from its intended installation location.

The UI must not say that an update was installed merely because the operating
system accepted a request to open the downloaded file.

## Target Artifact Matrix

| Platform | Canonical artifact | Optional artifact | Installation target |
| --- | --- | --- | --- |
| Windows x64 | `optees-windows-x64-setup.exe` built with Inno Setup | Portable ZIP | Per-user application directory under Local AppData |
| macOS Apple Silicon | Signed/notarized DMG when credentials are available | Ad-hoc signed contributor DMG | `/Applications/Optees.app` through the normal drag workflow |
| Linux x86_64 | AppImage with accurate runtime and update documentation | Debian package only after a separate decision | User-owned persistent location selected or documented by Optees |

Architectures not present in this matrix must be reported as unsupported; a
same-platform asset must not be selected while silently ignoring architecture.

## Phase 0 - Merge Gate And Factual Audit

- [x] Merge the local solver platform into `main` with a clean full-suite run.
- [x] Create `codex/native-installers` from the updated `main`.
- [ ] Record the exact behavior of every currently published artifact on a
  clean operating-system account.
- [ ] Record where the current updater downloads files and what application the
  operating system opens for ZIP, DMG, and AppImage assets.
- [ ] Confirm whether user configuration and generated data live outside the
  replaceable application directory on every platform.
- [ ] Correct documentation that calls a portable archive an installer or an
  update handoff an installed update.

**Exit criterion:** the current behavior and every known manual step are
documented without relying on assumptions from the build workflow.

## Phase 1 - Continuous Integration And Reproducible Build Inputs

- [x] Add a CI workflow for pull requests and pushes independently from tagged
  release publication.
- [x] Run the fast non-GUI suite on every supported development change and
  define scheduled or merge-gate jobs for GUI, benchmark, and TCP groups.
- [x] Make the release workflow depend on a successful test gate for the exact
  release commit.
- [x] Pin PyInstaller, its hooks, and platform packaging tools to reviewed
  versions.
- [x] Replace the rolling AppImageKit `continuous` download with a pinned
  version and verified checksum.
- [x] Introduce a reviewed build dependency lock or constraints file while
  keeping runtime compatibility policy explicit in `pyproject.toml`.
- [x] Pin third-party GitHub Actions by commit SHA and document the
  update process.
- [ ] Generate `SHA256SUMS` only after every final artifact has passed its
  platform smoke test.

**Exit criterion:** a tagged release cannot be published from an untested
commit or from unreviewed rolling packaging inputs.

## Phase 2 - Platform-Aware Update Orchestration

- [x] Replace generic asset selection with an application-layer update plan
  and continue migrating the download-and-open flow. The plan records
  platform, architecture, artifact kind, staging subdirectory, checksum,
  handoff method, and whether manual action remains.
- [ ] Complete use of the update plan through download and handoff instead of
  passing generic filesystem paths through the presentation layer.
- [ ] Keep operating-system process launching behind a dedicated port instead
  of placing platform behavior in the Qt controller.
- [ ] Represent `downloaded`, `verification_failed`, `installer_launched`,
  `manual_action_required`, and `replacement_scheduled` as distinct states.
- [ ] Use a persistent staging location appropriate to the current user rather
  than relying on the system temporary directory for the only copy.
- [ ] Fail closed when `SHA256SUMS` exists but contains no matching entry for
  the selected artifact.
- [ ] Enforce an expected artifact name, a bounded download size, safe filename
  handling, and cleanup of stale partial downloads.
- [ ] Report download progress and do not close Optees until the native handoff
  is known to have started successfully.
- [ ] Keep update checks disabled for source/development runs.
- [ ] Unit-test platform and architecture selection, verification failure,
  process-launch failure, and every state transition.

**Exit criterion:** the core update flow is deterministic and testable without
starting Qt or performing a real network request.

## Phase 3 - Windows Native Installer

- [ ] Add a versioned Inno Setup script under `packaging/windows/`.
- [ ] Install per user under Local AppData without requiring administrator
  privileges.
- [ ] Register Optees in Windows installed-app management with publisher,
  version, icon, uninstall command, and stable application identity.
- [ ] Add a Start Menu shortcut and make a desktop shortcut opt-in.
- [ ] Preserve user configuration across upgrades and uninstall only files
  owned by the installer.
- [ ] Build `optees-windows-x64-setup.exe` in GitHub Actions and retain the ZIP
  only when explicitly labelled **Portable**.
- [ ] Update release discovery to prefer the setup executable.
- [ ] Launch the visible installer for updates, close the running application
  safely, and verify the new version on the next start.
- [ ] Add Windows version metadata to the executable and installer.
- [ ] Add code signing when a suitable certificate becomes available; until
  then document the SmartScreen limitation without implying trust certification.

**Acceptance tests:** on a clean non-administrator Windows 10/11 account,
install, launch, execute one small solver job, start the local service, update
over the previous version, confirm the version and preserved settings, and
uninstall without leaving application binaries behind.

## Phase 4 - macOS Distribution And Update Handoff

- [ ] Keep the DMG drag-to-Applications workflow as the canonical installation
  contract.
- [ ] Normalize the bundle display name and application filename as `Optees`.
- [ ] Mount the final DMG in CI and verify bundle metadata, resources, signature,
  local-service startup, and one small solver execution from the mounted image.
- [ ] When credentials exist, sign nested binaries, enable hardened runtime,
  notarize, staple, and validate the final distributed artifact.
- [ ] When credentials do not exist, label the artifact as an ad-hoc signed
  contributor build and retain accurate Gatekeeper instructions.
- [ ] Make the updater open the verified DMG and present the remaining
  drag/replace step instead of claiming automatic installation.
- [ ] Test replacement of an existing `/Applications/Optees.app` copy and
  confirm that user settings survive.

**Acceptance tests:** clean-account installation, first launch with quarantine
attributes, manual update over an older version, local-service startup, one
solver job, and removal of the application bundle.

## Phase 5 - Linux Portable Distribution

- [ ] Decide and document that AppImage is a portable contract rather than a
  package-manager installation.
- [ ] Test the final AppImage itself, not only its source PyInstaller directory.
- [ ] Verify normal FUSE execution and the documented extract-and-run fallback
  separately.
- [ ] Add complete desktop metadata, version metadata, icon, and categories.
- [ ] Decide whether Optees manages a persistent per-user AppImage location or
  delegates integration to external desktop tools; do not mix both behaviors.
- [ ] If self-update is retained, embed reviewed AppImage update information,
  publish the matching `.zsync` asset, and use an atomic replacement strategy.
- [ ] Otherwise, present a verified download and explicit manual replacement
  instructions without closing the current application prematurely.
- [ ] Evaluate a Debian package only as an additional distribution channel,
  not as a replacement claimed to support every Linux distribution.

**Acceptance tests:** Ubuntu LTS CI plus manual verification on at least one
non-Debian desktop distribution; launch, desktop integration where promised,
one solver job, local-service startup, update/replacement, and removal.

## Phase 6 - Packaged Runtime Self-Test

- [ ] Add a bounded `--selftest` mode that exercises packaged assets, i18n,
  SciPy LP, OR-Tools MILP, and local-service startup without user data.
- [ ] Run it against the final Windows installer result, mounted macOS bundle,
  and final Linux AppImage.
- [ ] Verify at least one authenticated REST job through completion rather than
  checking capability discovery alone.
- [ ] Keep self-test output machine-readable and free of local secrets.
- [ ] Upload diagnostic logs only on CI failure and never include session tokens.

**Exit criterion:** native library presence and actual solver execution are
verified together in the same artifacts users download.

## Phase 7 - Release Candidate And Documentation

- [ ] Update `README.md`, `docs/ARCHITECTURE.md`, `docs/RELEASING.md`, and the
  landing page with the local solver platform and truthful platform-specific
  installation/update instructions.
- [ ] Publish a release candidate before the stable release.
- [ ] Download every release-candidate artifact from GitHub rather than testing
  only local build outputs.
- [ ] Execute and record the platform acceptance matrix.
- [ ] Promote the stable release only after all mandatory cells pass or are
  explicitly documented as unsupported.
- [ ] Update the local-service packaging acceptance criterion after the tagged
  artifacts have been verified.

## Priority

### P0 - Required Before The Next Stable Release

- Test-gated release workflow.
- Fail-closed checksum verification.
- Final-artifact smoke tests with one real solver execution.
- Windows Inno Setup installer and truthful portable ZIP labelling.
- Accurate macOS and Linux update handoff text.

### P1 - Product Hardening

- Platform-aware update orchestration and persistent staging.
- Progress reporting and post-update version confirmation.
- AppImage integration/update decision.
- Build dependency constraints and reproducibility evidence.

### P2 - Later Distribution Depth

- Windows signing certificate.
- Apple Developer ID signing and notarization.
- Additional CPU architectures.
- Optional Debian package, delta updates, SBOM, and build provenance attestations.

## Explicitly Deferred

- Microsoft Store, MSIX, Mac App Store, Snap, and Flatpak distribution.
- Silent privileged installation or background elevation.
- A custom cross-platform package manager inside Optees.
- Automatic rollback before native installer behavior and persistent user-data
  boundaries have been verified.

## Definition Of Done

This roadmap is complete only when a user can install an older release through
the documented platform path, run a solver and the local service, accept an
update, start the new version from the intended location with settings intact,
and uninstall or remove Optees according to the same documented contract.
