# Agent Service Configuration

This is the common setup guide for connecting local software agents to Optees.
All integrations use the same versioned capability contracts, but they do not
share the same transport or authentication requirements.

| Client | Transport | REST token | Current status |
| --- | --- | --- | --- |
| Claude Desktop / Cowork | MCP stdio | No | Tested locally on macOS |
| Ollama D0 harness | Authenticated loopback REST | Yes | Experimental source/Python-package workflow |
| OpenAI GPT client | To be selected and verified | To be determined | Planned compatibility test |

General rules:

- Keep network services bound to `127.0.0.1`.
- Never place a REST bearer token in an MCP stdio configuration.
- Require capability discovery, descriptor inspection, exact payload
  validation, execution, and result retrieval in that order.
- Treat mathematical status and independent validation status as separate
  claims.
- Do not assume that a hosted chat can reach localhost or launch a local MCP
  process.

## Claude Desktop And Cowork

Claude Desktop can launch Optees as a private local MCP server. Claude calls
the same versioned capabilities used by the desktop application, CLI, and
local REST API, but the MCP connection uses standard input and output: it does
not require a port, URL, or bearer token.

This integration has been tested with Claude Desktop Cowork in local mode on
macOS. Cloud-hosted sessions that cannot launch local processes cannot use this
configuration.

### 1. Select The Installed MCP Command

Native Optees packages include a dedicated MCP stdio entry point. Do not use
`optees-server` in Claude's MCP configuration: that executable is the
authenticated REST service and requires a session token.

Use the command matching the installation:

| Installation | Claude `command` | Claude `args` |
| --- | --- | --- |
| Windows installer | `%LOCALAPPDATA%\\Programs\\Optees\\optees-mcp.exe` | `[]` |
| Windows portable ZIP | Absolute extracted path to `optees-mcp.exe` | `[]` |
| macOS DMG installation | `/Applications/optees.app/Contents/MacOS/optees-mcp` | `[]` |
| Ubuntu/Debian `.deb` | `/usr/bin/optees-mcp` | `[]` |
| Linux AppImage | Absolute path to the AppImage | `["--mcp-server"]` |

These paths apply to native releases that include the packaged MCP companion.
Older releases may require the source/Python installation below.

### 2. Install From Source Or Python Package

From an Optees source checkout:

```bash
python -m pip install -e ".[mcp]"
```

For a Python package installation, ensure that `optees-mcp` is available in the
environment that Claude Desktop will launch.

### 3. Open Claude's Configuration

In Claude Desktop:

1. Open **Settings**.
2. Select **Developer**.
3. Select **Edit Config**.
4. Open `claude_desktop_config.json` in the editor offered by Claude.

On macOS this file is normally located at:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

### 4. Add The Optees Server

`mcpServers` must be a top-level property, alongside existing properties such
as `preferences`. Do not place it inside `preferences`.

For an installed Optees command, add:

```json
{
  "mcpServers": {
    "optees": {
      "command": "/absolute/path/to/optees-mcp",
      "args": []
    }
  }
}
```

Use `command -v optees-mcp` in a terminal to find the absolute command path.
An absolute path is more reliable than depending on the graphical
application's `PATH`.

For a Linux AppImage, keep the AppImage in a stable user-owned location and
configure its MCP dispatcher explicitly:

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

During source development, point Claude at the Python interpreter from the
Optees environment and at the absolute repository source directory:

```json
{
  "mcpServers": {
    "optees": {
      "command": "/absolute/path/to/optees-environment/bin/python",
      "args": ["-m", "optees.mcp_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/optees/src"
      }
    }
  }
}
```

If the file already contains settings, preserve them and insert `mcpServers`
at the root. For example:

```json
{
  "coworkUserFilesPath": "/Users/example/Claude",
  "mcpServers": {
    "optees": {
      "command": "/absolute/path/to/optees-environment/bin/python",
      "args": ["-m", "optees.mcp_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/optees/src"
      }
    }
  },
  "preferences": {
    "sidebarMode": "chat"
  }
}
```

The final file must remain valid JSON. In particular, keep commas between
top-level properties and use JSON booleans such as `true`, not Markdown text.

### 5. Restart And Verify

Fully quit Claude Desktop, reopen it, and start a new local chat or Cowork
session. Then send this exact discovery prompt:

```text
Use the Optees tools to list all available solver capabilities.
Do not answer from your own knowledge: call optees_list_capabilities.
```

The wording may vary, but a successful answer should report these 13
capabilities:

```text
Graph
- graph.shortest_path.dijkstra - Dijkstra shortest path

Knapsack
- knapsack.zero_one - 0/1 Knapsack
- knapsack.bounded - Bounded Knapsack
- knapsack.unbounded - Unbounded Knapsack
- knapsack.fractional - Fractional Knapsack
- knapsack.multi_dimensional - Multi-dimensional Knapsack

Linear and nonlinear programming
- lp.continuous - Continuous linear programming
- milp.linear - Mixed-integer linear programming
- nlp.continuous_local - Continuous local nonlinear optimization

Machine learning (educational)
- ml.regression.linear - Linear regression
- ml.classification.binary_logistic - Binary logistic classification
- ml.forecasting.univariate - Univariate time-series forecasting

Packing
- packing.single_container_3d - Orthogonal single-container 3D packing
```

All currently use problem and result schema version `1`.

The Claude connector directory may show only Anthropic and partner
connectors. A local MCP process does not need to appear in that directory to
work; the explicit tool call above is the relevant verification.

### 5. Expected Tool Workflow

For a solver task, Claude should:

1. call `optees_list_capabilities`;
2. inspect the chosen descriptor with `optees_get_capability`;
3. formulate the exact versioned problem;
4. call `optees_validate_problem` before execution;
5. create and monitor the job;
6. retrieve the result;
7. report mathematical status separately from independent validation status.

Changing the payload after validation requires a new validation call.

### Tested Manufacturing Examples

The first exploratory Cowork study uses a fully synthetic manufacturing
workbook and two tasks:

- [Single-solver prompt](../../benchmarks/agents/scenarios/manufacturing-planning-001/prompt-single-solver.md)
  asks Claude to formulate and solve one production-planning MILP.
- [Orchestration prompt](../../benchmarks/agents/scenarios/manufacturing-planning-001/prompt-orchestration.md)
  asks Claude to run two regressions and feed their demand forecasts into a
  production-planning MILP.
- [Synthetic input workbook](../../benchmarks/agents/scenarios/manufacturing-planning-001/data/fictional_company_input.xlsx)
  is the only workbook shared with the evaluated agent.
- [Private ground truth](../../benchmarks/agents/scenarios/manufacturing-planning-001/reference/fictional_company_ground_truth.xlsx)
  is retained for review and must not be exposed to the agent during a run.

Claude generated the following management reports:

- [Direct production plan - DOCX](../../benchmarks/agents/studies/claude-cowork-manufacturing-2026-07-18/outputs/Northstar_Production_Plan_Report.docx)
- [Direct production plan - PDF](../../benchmarks/agents/studies/claude-cowork-manufacturing-2026-07-18/outputs/Northstar_Production_Plan_Report.pdf)
- [Forecast-driven production plan - DOCX](../../benchmarks/agents/studies/claude-cowork-manufacturing-2026-07-18/outputs/Northstar_Forecast_Production_Plan_Report.docx)
- [Forecast-driven production plan - PDF](../../benchmarks/agents/studies/claude-cowork-manufacturing-2026-07-18/outputs/Northstar_Forecast_Production_Plan_Report.pdf)

Both numerical results match the reviewed Optees reference. This run is
documented as exploratory rather than a publishable provider comparison because
the exact Claude model identifier and repeated controlled trials were not
recorded. Future studies will add more scenarios, agents, repetitions, and
unaided controls.

### Claude Troubleshooting

- Confirm that `mcpServers` is at the JSON root and that the file parses.
- Use absolute paths for both Python and `PYTHONPATH`.
- Confirm that the selected interpreter can run
  `python -m optees.mcp_server` and has the `mcp` extra installed.
- For a native installation, confirm that the configured `optees-mcp`
  companion exists and is executable. On Linux, confirm that the AppImage is
  executable and that `--mcp-server` is present in `args`.
- Fully quit Claude instead of closing only the current window.
- Do not paste the REST API bearer token into the MCP configuration. The MCP
  process uses its private stdio channel and needs no network credential.
- If the error mentions `OPTEES_LOCAL_SERVER_TOKEN`, Claude is launching
  `optees-server` by mistake. Replace it with the MCP command above.

## Ollama Local Harness

The standard Ollama chat application does not know about Optees tools. The D0
harness connects a tool-capable local model to the authenticated Optees REST
service and enforces descriptor inspection and exact-payload validation.

From a source checkout:

```bash
cd /absolute/path/to/optees
PYTHONPATH=src python -m optees.ollama_chat --model qwen3.5:9b
```

From a Python package installed with `pip`:

```bash
optees-ollama-chat --model qwen3.5:9b
```

Before launching the harness, start the local solver service in Optees
Settings and copy either the authorization value or the complete connection
configuration. Input is hidden in the terminal. The native PyInstaller
artifacts do not currently expose this chat command; a packaged Local Agent
desktop module is planned.

When the harness runs from source or an installed Python package, it also
exposes `optees_download_artifact` and `optees_download_report`. Files are
written only to the export directory authorized in Optees Settings; the model
may choose a safe filename but cannot choose an arbitrary filesystem path.

When a request contains several independent models, agents should use
`optees_validate_batch`, `optees_create_batch`, `optees_get_batch_status`, and
`optees_get_batch_result`. The batch accepts at most 32 items and preserves the
individual result and validation report for each one. It must not be used for
dependent stages such as forecasting followed by production optimization,
because those require explicit orchestration between results and inputs.

The reviewed D0 prompt, model compatibility results, transcript policy, and
security behavior are documented in
[Ollama D0 local agent harness](../archive/local-agent/ollama-d0-harness.md).

## Result Artifacts And Reports

Agents should inspect advertised artifact types after a completed job and
request only evidence needed by the user. Metadata calls do not transfer
binary content. Markdown reports are always local and dependency-free; PDF
requires the optional Pandoc+Typst backend.

Before requesting PDF, call `optees_get_report_backends`. Compose with
`optees_compose_report` and poll `optees_get_report_status`. Agents may read
bytes through the returned `optees-report://` resource, or use
`optees_download_report` after explicit user intent to save the file in the
directory authorized in Optees Settings. The corresponding artifact operation
is `optees_download_artifact`. These tools accept an optional safe filename,
not a filesystem path, and verify SHA-256 before writing. Packing OBJ+MTL
artifacts can request `isometric`, `front`, `side`, or `top` views. For long
operations, inspect progress and use `optees_cancel_artifact` or
`optees_cancel_report` when the user cancels the task.

The full request example, REST equivalents, runtime diagnostics, and security
limits are documented in
[Local Result Artifacts And Reports](local-reporting.md).

## OpenAI GPT Clients

OpenAI GPT integration is planned but not yet certified. Before publishing a
configuration, Optees must select a supported local client or MCP surface and
record the exact client, model, transport, authentication boundary, and
localhost limitations.

The first acceptance check will use this prompt:

```text
Use the Optees tools to list all available solver capabilities.
Do not answer from your own knowledge: call optees_list_capabilities.
```

A successful response must be based on the returned 13 capability descriptors,
not on model memory. No speculative JSON configuration should be copied into
this guide before that workflow succeeds from a clean setup.

## Shared Technical References

- [MCP stdio server](local-agent/mcp-stdio.md)
- [Authenticated local REST API](local-agent/local-rest-api.md)
- [Desktop server controls](local-agent/server-process-and-desktop.md)
- [Ollama D0 harness](../archive/local-agent/ollama-d0-harness.md)
- [Agent benchmark protocol](../evidence/agent-benchmarks.md)
