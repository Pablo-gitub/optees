from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


TOKEN = "release-report-smoke-token-" + "x" * 32
LP_PROBLEM = {
    "version": "1",
    "variables": [
        {"name": "x", "label": "Product X", "lb": 0, "ub": 4},
        {"name": "y", "label": "Product Y", "lb": 0, "ub": 4},
    ],
    "objective": {
        "sense": "max",
        "coefficients": [3, 2],
        "offset": 0,
    },
    "constraints": [
        {"coefficients": [1, 1], "relation": "<=", "rhs": 4},
    ],
}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) < 2:
        print(
            "usage: python packaging/smoke_packaged_reporting.py "
            "PORT COMMAND [ARG ...]",
            file=sys.stderr,
        )
        return 2
    try:
        port = int(arguments.pop(0))
    except ValueError:
        print("PORT must be an integer", file=sys.stderr)
        return 2
    command = arguments + ["--port", str(port), "--log-level", "error"]
    return _run_smoke(port, command)


def _run_smoke(port: int, command: list[str]) -> int:
    with tempfile.TemporaryDirectory(prefix="optees-package-smoke-") as temporary:
        environment = dict(os.environ)
        environment["OPTEES_LOCAL_SERVER_TOKEN"] = TOKEN
        environment["MPLCONFIGDIR"] = str(Path(temporary) / "matplotlib")
        environment["XDG_CACHE_HOME"] = str(Path(temporary) / "cache")
        stdout_path = Path(temporary) / "server.stdout.log"
        stderr_path = Path(temporary) / "server.stderr.log"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                env=environment,
                stdout=stdout,
                stderr=stderr,
            )
            try:
                client = _Client(port)
                _wait_for_health(client, process)
                _verify_reporting(client)
                return 0
            except Exception:
                stdout.flush()
                stderr.flush()
                _print_log("stdout", stdout_path)
                _print_log("stderr", stderr_path)
                raise
            finally:
                _terminate(process)


class _Client:
    def __init__(self, port: int) -> None:
        self._base_url = f"http://127.0.0.1:{port}"

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        authenticated: bool = True,
    ) -> tuple[dict[str, object], dict[str, str]]:
        content, headers = self.download(
            method,
            path,
            payload,
            authenticated=authenticated,
        )
        try:
            decoded = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{method} {path} returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise RuntimeError(f"{method} {path} returned a non-object JSON value")
        return decoded, headers

    def download(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        authenticated: bool = True,
    ) -> tuple[bytes, dict[str, str]]:
        data = None
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Bearer {TOKEN}"
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.read(), {
                    name.lower(): value for name, value in response.headers.items()
                }
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"{method} {path} failed with HTTP {exc.code}: {body}"
            ) from exc


def _wait_for_health(client: _Client, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"packaged local service exited with code {process.returncode}"
            )
        try:
            health, _ = client.request("GET", "/health", authenticated=False)
            if health.get("status") == "ok":
                return
        except (OSError, RuntimeError):
            time.sleep(0.25)
    raise RuntimeError("packaged local service did not become healthy")


def _verify_reporting(client: _Client) -> None:
    capabilities, _ = client.request("GET", "/api/v1/capabilities")
    lp = next(
        (
            item
            for item in capabilities.get("capabilities", [])
            if isinstance(item, dict) and item.get("id") == "lp.continuous"
        ),
        None,
    )
    if not isinstance(lp, dict) or lp.get("available") is not True:
        raise RuntimeError(f"packaged LP capability is unavailable: {lp!r}")
    available = {
        item.get("artifact_type")
        for item in lp.get("available_artifacts", [])
        if isinstance(item, dict)
    }
    if not {"solution_table", "feasible_region"} <= available:
        raise RuntimeError(f"packaged LP artifact inventory is incomplete: {available}")

    submitted, _ = client.request(
        "POST",
        "/api/v1/jobs",
        {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
    )
    job_id = _required_identifier(submitted, "job_id")
    job = _poll_object(
        client,
        f"/api/v1/jobs/{job_id}",
        "job_status",
        {"completed", "failed", "cancelled"},
    )
    if job.get("job_status") != "completed":
        raise RuntimeError(f"packaged LP job did not complete: {job!r}")

    result, _ = client.request("GET", f"/api/v1/jobs/{job_id}/result")
    if (
        result.get("mathematical_status") != "optimal"
        or not isinstance(result.get("validation"), dict)
        or result["validation"].get("status") != "verified"
    ):
        raise RuntimeError(f"packaged LP result is not verified optimal: {result!r}")

    client.request(
        "POST",
        f"/api/v1/jobs/{job_id}/artifacts",
        {
            "contract_version": "1",
            "requests": [
                {
                    "artifact_type": "solution_table",
                    "formats": ["markdown"],
                    "options": {"locale": "en"},
                },
                {
                    "artifact_type": "feasible_region",
                    "formats": ["png"],
                    "options": {
                        "locale": "en",
                        "theme": "light",
                        "width": 480,
                        "height": 320,
                    },
                },
            ],
        },
    )
    artifacts = _poll_artifacts(client, job_id)
    by_type = {item["artifact_type"]: item for item in artifacts}
    table = by_type["solution_table"]
    chart = by_type["feasible_region"]
    table_content = _verify_download(client, table)
    chart_content = _verify_download(client, chart)
    if b"| Variable |" not in table_content:
        raise RuntimeError("packaged Markdown table content is invalid")
    if not chart_content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("packaged chart content is not a PNG")

    backends, _ = client.request("GET", "/api/v1/reports/backends")
    diagnostics = backends.get("backends")
    if not isinstance(diagnostics, list) or not diagnostics:
        raise RuntimeError("packaged report backend diagnostics are missing")
    diagnostic = diagnostics[0]
    if (
        not isinstance(diagnostic, dict)
        or diagnostic.get("backend_id") != "pandoc.typst.v1"
        or not isinstance(diagnostic.get("available"), bool)
    ):
        raise RuntimeError(f"unexpected packaged PDF diagnostic: {diagnostic!r}")

    sections = [
        {
            "section_id": "result",
            "heading": "Verified result",
            "blocks": [
                {"type": "job_status", "job_id": job_id},
                {
                    "type": "artifact",
                    "artifact_id": table["artifact_id"],
                    "caption": "Solution table",
                },
                {
                    "type": "artifact",
                    "artifact_id": chart["artifact_id"],
                    "caption": "Feasible region",
                },
            ],
        }
    ]
    markdown = _compose_report(
        client,
        {
            "contract_version": "1",
            "format": "markdown",
            "locale": "en",
            "title": "Packaged reporting smoke",
            "sections": sections,
            "metadata": {"acceptance": "packaged"},
        },
    )
    report_text = markdown.decode("utf-8")
    if "Optees · optees.it" not in report_text or job_id not in report_text:
        raise RuntimeError("packaged Markdown report content is incomplete")

    if diagnostic["available"] is True:
        pdf = _compose_report(
            client,
            {
                "contract_version": "1",
                "format": "pdf",
                "locale": "en",
                "title": "Packaged PDF reporting smoke",
                "sections": sections,
                "metadata": {"acceptance": "packaged"},
            },
        )
        if not pdf.startswith(b"%PDF-"):
            raise RuntimeError("packaged PDF report content is invalid")


def _compose_report(
    client: _Client,
    payload: dict[str, object],
) -> bytes:
    created, _ = client.request(
        "POST",
        "/api/v1/reports",
        payload,
    )
    report_id = _required_identifier(created, "report_id")
    report = _poll_object(
        client,
        f"/api/v1/reports/{report_id}",
        "status",
        {"available", "failed", "cancelled"},
    )
    if report.get("status") != "available":
        raise RuntimeError(f"packaged report did not become available: {report!r}")
    report_content, headers = client.download(
        "GET",
        f"/api/v1/reports/{report_id}/download",
    )
    _verify_hash(report_content, headers, report)
    return report_content


def _poll_artifacts(client: _Client, job_id: str) -> list[dict[str, object]]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        listing, _ = client.request("GET", f"/api/v1/jobs/{job_id}/artifacts")
        batches = listing.get("artifact_batches")
        if isinstance(batches, list) and batches:
            artifacts = batches[0].get("artifacts")
            if isinstance(artifacts, list) and artifacts and all(
                isinstance(item, dict) and item.get("status") in {
                    "available",
                    "failed",
                    "cancelled",
                }
                for item in artifacts
            ):
                if not all(item.get("status") == "available" for item in artifacts):
                    raise RuntimeError(
                        f"packaged artifact generation failed: {artifacts!r}"
                    )
                return artifacts
        time.sleep(0.05)
    raise RuntimeError("packaged artifact generation timed out")


def _poll_object(
    client: _Client,
    path: str,
    status_field: str,
    terminal: set[str],
) -> dict[str, object]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        value, _ = client.request("GET", path)
        if value.get(status_field) in terminal:
            return value
        time.sleep(0.05)
    raise RuntimeError(f"packaged operation timed out while polling {path}")


def _verify_download(
    client: _Client,
    artifact: dict[str, object],
) -> bytes:
    artifact_id = _required_identifier(artifact, "artifact_id")
    content, headers = client.download("GET", f"/api/v1/artifacts/{artifact_id}")
    _verify_hash(content, headers, artifact)
    return content


def _verify_hash(
    content: bytes,
    headers: dict[str, str],
    metadata: dict[str, object],
) -> None:
    expected = metadata.get("sha256")
    actual = hashlib.sha256(content).hexdigest()
    if expected != actual or headers.get("x-content-sha256") != actual:
        raise RuntimeError(
            f"download hash mismatch: metadata={expected!r}, "
            f"header={headers.get('x-content-sha256')!r}, actual={actual!r}"
        )


def _required_identifier(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"response is missing {field}: {payload!r}")
    return value


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _print_log(label: str, path: Path) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    if content:
        print(f"--- packaged server {label} ---", file=sys.stderr)
        print(content, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
