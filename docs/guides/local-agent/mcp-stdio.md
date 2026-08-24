# Optees MCP Stdio Server

The A1.6 MCP adapter lets a compatible local desktop or IDE client launch a
private Optees solver process and call its tools through standard input and
output. It does not open a network port and it does not use the REST API
internally.

## Install

Native releases expose MCP without requiring a separate Python installation:

| Platform | Command |
| --- | --- |
| Windows installer | `%LOCALAPPDATA%\\Programs\\Optees\\optees-mcp.exe` |
| macOS | `/Applications/optees.app/Contents/MacOS/optees-mcp` |
| Ubuntu/Debian `.deb` | `/usr/bin/optees-mcp` |
| Linux AppImage | `/absolute/path/to/optees-linux-x86_64.AppImage --mcp-server` |

`optees-server` is not interchangeable with `optees-mcp`. It exposes the REST
API, requires a session bearer token, and must not be configured as an MCP
stdio process.

For source development or a Python package installation, install Optees with
the optional MCP dependency:

```bash
python -m pip install -e ".[mcp]"
```

The SDK is pinned to the stable MCP Python 1.x line. MCP 2.x is intentionally
excluded until its stable contracts can be reviewed.

## Client Configuration

For an installed Optees package, register this local process in an MCP client:

```json
{
  "mcpServers": {
    "optees": {
      "command": "optees-mcp",
      "args": []
    }
  }
}
```

For the Linux AppImage, use the AppImage as the command and pass the dispatcher
argument separately:

```json
{
  "mcpServers": {
    "optees": {
      "command": "/absolute/path/to/optees-linux-x86_64.AppImage",
      "args": ["--mcp-server"]
    }
  }
}
```

During source development, use the Python interpreter from the Optees
environment and an absolute source path:

```json
{
  "mcpServers": {
    "optees": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "optees.mcp_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/optees/src"
      }
    }
  }
}
```

No URL or bearer token is required. The MCP client launches the process and
owns its stdin/stdout channel. Do not paste the REST authorization token into
this configuration.

For shared agent setup, tested Claude Desktop and Cowork steps, Ollama launch
instructions, future OpenAI GPT validation, and example runs, see the
[agent service configuration guide](../agent-service-configuration.md).

## Tool Workflow

The server exposes these allowlisted tools:

1. `optees_list_capabilities`
2. `optees_get_capability`
3. `optees_validate_problem`
4. `optees_create_job`
5. `optees_get_job_status`
6. `optees_get_job_result`
7. `optees_cancel_job`
8. `optees_validate_batch`
9. `optees_create_batch`
10. `optees_get_batch_status`
11. `optees_get_batch_result`
12. `optees_cancel_batch`
13. `optees_list_result_artifacts`
14. `optees_render_result_artifacts`
15. `optees_get_artifact`
16. `optees_cancel_artifact`
17. `optees_compose_report`
18. `optees_get_report_backends`
19. `optees_get_report_status`
20. `optees_get_report`
21. `optees_cancel_report`

An agent must inspect the complete capability descriptor before validation and
must validate the exact capability and payload before job creation. A changed
payload requires a new validation. Solver mathematical status and independent
validation status are separate claims in every result.

For 1 to 32 independent scenarios, the agent should inspect every distinct
capability, validate the exact versioned batch, create it once, poll its
aggregate status, and retrieve its aggregate result. Each batch item retains
its own job and independent validation report. A changed item invalidates the
batch proof. Batch tools do not orchestrate dependent multi-stage workflows.

After a job completes, artifact access follows a separate, opt-in sequence:

1. call `optees_list_result_artifacts` to inspect supported artifact types,
   formats, options, and existing batches;
2. call `optees_render_result_artifacts` only with advertised combinations;
3. poll `optees_list_result_artifacts` until the requested entry is
   `available`, or cancel it with `optees_cancel_artifact`;
4. call `optees_get_artifact` to inspect media type, size, SHA-256, expiry, and
   the opaque resource URI;
5. read `optees-artifact://{artifact_id}` only when the user actually needs the
   content.

The artifact tools return metadata only. They never include Base64,
binary bytes, internal storage IDs, or filesystem paths. Explicit resource
reads remain bounded by the session artifact limits and verify content
integrity before transfer.

Report composition follows the same metadata-first rule. Inspect
`optees_get_report_backends`, submit a versioned Markdown or PDF request with
`optees_compose_report`, poll `optees_get_report_status`, and retrieve metadata
with `optees_get_report`. Report bytes move only through
`optees-report://{report_id}`. `optees_cancel_report` provides cooperative
cancellation and prevents late publication.

## Security And Scope

The stdio process is private to the launching client, keeps jobs only in
memory, and terminates when the client closes the channel. It cannot make a
cloud-hosted agent reach services on the user's localhost; the MCP client
itself must run locally and support local process servers.

The server discovers every capability registered by the shared composition
root. Automated MCP sequencing covers a complete LP solve plus artifact
discovery, bounded rendering, metadata-only inspection, and explicit resource
transfer. Broader capability and client compatibility still requires the Phase
D matrix. Native release CI launches the packaged companion on Windows, macOS,
and Linux and requires successful capability discovery. A manual clean-machine
Claude test remains part of release-candidate acceptance.
