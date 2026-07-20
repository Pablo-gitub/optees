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
[agent service configuration guide](../AGENTS_SERVICE_CONFIG.md).

## Tool Workflow

The server exposes these allowlisted tools:

1. `optees_list_capabilities`
2. `optees_get_capability`
3. `optees_validate_problem`
4. `optees_create_job`
5. `optees_get_job_status`
6. `optees_get_job_result`
7. `optees_cancel_job`

An agent must inspect the complete capability descriptor before validation and
must validate the exact capability and payload before job creation. A changed
payload requires a new validation. Solver mathematical status and independent
validation status are separate claims in every result.

## Security And Scope

The stdio process is private to the launching client, keeps jobs only in
memory, and terminates when the client closes the channel. It cannot make a
cloud-hosted agent reach services on the user's localhost; the MCP client
itself must run locally and support local process servers.

The server discovers every capability registered by the shared composition
root. Automated MCP sequencing and one complete LP execution provide the first
vertical regression path; broader capability and client compatibility still
requires the Phase D matrix. Native release CI launches the packaged companion
on Windows, macOS, and Linux and requires successful capability discovery. A
manual clean-machine Claude test remains part of release-candidate acceptance.
