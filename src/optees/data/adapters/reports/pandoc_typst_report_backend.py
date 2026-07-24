from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from time import monotonic, sleep

from optees.application.contracts.report_backend import (
    RenderedReport,
    ReportBackendCancelledError,
    ReportBackendDiagnostic,
    ReportBackendRequest,
    ReportBackendUnavailableError,
    ReportCancellation,
    ReportProgressCallback,
)


_MAX_PDF_BYTES = 64 * 1024 * 1024
_TIMEOUT_SECONDS = 120


class PandocTypstReportBackend:
    """Optional Pandoc+Typst adapter with a fixed, non-user-configurable command."""

    backend_id = "pandoc.typst.v1"

    def __init__(
        self,
        *,
        pandoc_executable: str = "pandoc",
        typst_executable: str = "typst",
        template_path: Path,
    ) -> None:
        self._pandoc_name = pandoc_executable
        self._typst_name = typst_executable
        self._template_path = Path(template_path)

    def diagnostic(self) -> ReportBackendDiagnostic:
        pandoc = shutil.which(self._pandoc_name)
        typst = shutil.which(self._typst_name)
        if pandoc is None:
            return ReportBackendDiagnostic(
                self.backend_id,
                False,
                "typst",
                reason="Pandoc was not found on PATH.",
            )
        if typst is None:
            return ReportBackendDiagnostic(
                self.backend_id,
                False,
                "typst",
                reason="Typst was not found on PATH.",
                pandoc_version=_version(pandoc),
            )
        if not self._template_path.is_file():
            return ReportBackendDiagnostic(
                self.backend_id,
                False,
                "typst",
                reason="The bundled Optees Typst template is unavailable.",
                pandoc_version=_version(pandoc),
                engine_version=_version(typst),
            )
        return ReportBackendDiagnostic(
            self.backend_id,
            True,
            "typst",
            pandoc_version=_version(pandoc),
            engine_version=_version(typst),
        )

    def render(
        self,
        request: ReportBackendRequest,
        *,
        cancellation: ReportCancellation,
        progress: ReportProgressCallback,
    ) -> RenderedReport:
        diagnostic = self.diagnostic()
        if not diagnostic.available:
            raise ReportBackendUnavailableError(
                diagnostic.reason or "The PDF backend is unavailable."
            )
        pandoc = shutil.which(self._pandoc_name)
        typst = shutil.which(self._typst_name)
        assert pandoc is not None and typst is not None
        if cancellation.is_set():
            raise ReportBackendCancelledError("PDF rendering was cancelled.")

        progress(65, "preparing_pdf")
        with tempfile.TemporaryDirectory(prefix="optees-report-pdf-") as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            markdown_path = root / "report.md"
            output_path = root / "report.pdf"
            markdown = request.markdown.decode("utf-8")
            for index, asset in enumerate(request.assets):
                file_name = f"asset-{index:03d}{asset.suffix}"
                path = root / file_name
                path.write_bytes(asset.content)
                path.chmod(0o600)
                markdown = markdown.replace(
                    f"optees-report-asset://{asset.asset_id}",
                    file_name,
                )
                markdown = markdown.replace(
                    f"optees-artifact://{asset.asset_id}",
                    file_name,
                )
            markdown_path.write_text(markdown, encoding="utf-8")
            markdown_path.chmod(0o600)

            command = [
                pandoc,
                str(markdown_path),
                "--from=gfm",
                "--to=pdf",
                f"--pdf-engine={typst}",
                f"--template={self._template_path}",
                f"--resource-path={root}",
                "--standalone",
                "--fail-if-warnings",
                "--output",
                str(output_path),
            ]
            environment = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(root),
                "TMPDIR": str(root),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
            }
            for name in ("SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC"):
                if name in os.environ:
                    environment[name] = os.environ[name]
            process = subprocess.Popen(
                command,
                cwd=root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=os.name != "nt",
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if os.name == "nt"
                    else 0
                ),
            )
            deadline = monotonic() + _TIMEOUT_SECONDS
            progress(75, "rendering_pdf")
            while process.poll() is None:
                if cancellation.is_set():
                    _terminate(process)
                    raise ReportBackendCancelledError("PDF rendering was cancelled.")
                if monotonic() >= deadline:
                    _terminate(process)
                    raise RuntimeError("PDF rendering exceeded the configured timeout.")
                sleep(0.05)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                del stdout, stderr
                raise RuntimeError("Pandoc+Typst could not render the report.")
            if not output_path.is_file():
                raise RuntimeError("Pandoc+Typst did not produce a PDF.")
            content = output_path.read_bytes()
            if len(content) > _MAX_PDF_BYTES:
                raise RuntimeError("The rendered PDF exceeds the configured size limit.")
            progress(90, "verifying_pdf")
            return RenderedReport("application/pdf", content, self.backend_id)


def _version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first_line = completed.stdout.splitlines()
    return first_line[0][:120] if first_line else None


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, 15)
        process.wait(timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        if process.poll() is None:
            if os.name == "nt":
                process.kill()
            else:
                try:
                    os.killpg(process.pid, 9)
                except OSError:
                    process.kill()
            process.wait()
