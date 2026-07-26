# Local Result Artifacts And Reports

Optees can generate result artifacts after a completed solver job and compose
them into deterministic Markdown or optional PDF reports. These workflows are
opt-in: requesting neither artifacts nor reports leaves solver execution
unchanged.

## Availability

Markdown composition is always available and has no external document-runtime
dependency. PDF composition uses the optional `pandoc.typst.v1` backend and
requires both `pandoc` and `typst` executables on `PATH`.

Clients must inspect availability instead of assuming that PDF is installed:

- REST: `GET /api/v1/reports/backends`;
- MCP: `optees_get_report_backends`.

An unavailable backend returns a structured `report_backend_unavailable`
diagnostic before a report is queued. The first PDF release keeps Pandoc and
Typst optional while installer size, licenses, and native packaging are
evaluated. Optees bundles only its fixed Typst template.

## Report Request

The version 1 request supports `markdown`, `job_status`, and `artifact` blocks.
The output format is `markdown` or `pdf`. A Packing OBJ+MTL artifact can request
one or more bounded static views:

```json
{
  "contract_version": "1",
  "format": "pdf",
  "locale": "en",
  "title": "Validated loading report",
  "sections": [
    {
      "section_id": "result",
      "heading": "Result",
      "blocks": [
        {"type": "job_status", "job_id": "job-..."},
        {
          "type": "artifact",
          "artifact_id": "artifact-...",
          "caption": "Container loading",
          "views": ["isometric", "top"]
        }
      ]
    }
  ]
}
```

Allowed camera names are `isometric`, `front`, `side`, and `top`. XLSX table
artifacts are converted from their first worksheet into bounded report tables.
OBJ+MTL archives are parsed with bounded geometry and archive limits before
the selected PNG views are rendered. Conversion never accepts arbitrary local
paths, remote URLs, templates, filters, or command-line options.

## Lifecycle

Artifact and report manifests expose `progress_percent` and `progress_stage`.
Cancellation is available through:

- `POST /api/v1/artifacts/{artifact_id}/cancel`;
- `POST /api/v1/reports/{report_id}/cancel`;
- `optees_cancel_artifact`;
- `optees_cancel_report`.

Cancellation is cooperative. It immediately makes the public operation
terminal and prevents a late renderer result from being published. The
Pandoc+Typst adapter also terminates its isolated process group.

Artifact bytes remain available through authenticated REST downloads or
explicit MCP resources. With explicit user intent, MCP can also call
`optees_download_artifact` or `optees_download_report` to save verified bytes
inside the export directory selected in Optees Settings. These tools accept a
safe filename, never an arbitrary destination path. Reports follow the same
rule. Metadata tools never
return binary content or absolute temporary paths.

## Native Acceptance

Before a stable release advertises PDF reporting, perform the installed
artifact smoke procedure in [Releasing Optees](RELEASING.md) on macOS,
Windows, and Linux. Source tests and a mocked PDF executable verify contracts
and failure behavior; they do not replace a real Typst render from each native
release candidate.

The real Pandoc+Typst path has been exercised successfully from a macOS source
environment, including composition initiated by a local Qwen agent. This does
not close the packaging gate: the installed macOS, Windows, and Linux release
candidates must each pass the same procedure with the executables and templates
available in their actual distribution environment.
