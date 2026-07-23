# Optees Architecture

Optees has two public roles built on the same application core:

1. a PySide6 desktop workbench for learning, formulating, solving, and
   visualizing mathematical problems;
2. a local solver platform that exposes versioned capabilities to scripts and
   AI agents through a CLI, authenticated loopback REST API, or MCP stdio.

The architecture keeps mathematical execution independent from presentation
and transport concerns. A solver added to the shared capability registry can
therefore be reused by every supported interface without duplicating its
contract or execution logic.

## Design Principles

- **Dependency direction:** presentation, transports, and infrastructure depend
  on application and domain abstractions, not the reverse.
- **Versioned public contracts:** capability descriptors, problem schemas,
  result schemas, execution envelopes, and validation reports are explicit
  JSON contracts.
- **Validate before execution:** clients can validate the exact payload before
  creating a job. The MCP facade additionally enforces discovery and
  validation as protocol steps.
- **Separate statuses:** job lifecycle, mathematical status, termination reason,
  and independent validation status describe different facts.
- **Local-first security:** REST binds to loopback and requires a per-session
  bearer token; MCP communicates over a private stdio subprocess.
- **Honest guarantees:** independent post-solve validation is reported only
  when a validator is registered. It is currently implemented for LP and MILP.

## System Context

```mermaid
flowchart LR
    User["Desktop user"] --> GUI["PySide6 desktop workbench"]
    Script["Local script or CI task"] --> CLI["Headless CLI"]
    LocalAgent["Local AI agent"] --> MCP["MCP stdio server"]
    LocalAgent --> REST["Authenticated loopback REST API"]
    Ollama["Optional Ollama tool harness"] --> REST

    GUI --> Core["Application services and use cases"]
    CLI --> Core
    MCP --> Jobs["Local job service"]
    REST --> Jobs
    Jobs --> Core

    Core --> Registry["Versioned capability registry"]
    Core --> Adapters["Solver adapters"]
    Adapters --> Engines["SciPy, NumPy, OR-Tools, and internal algorithms"]
```

All components shown above execute on the user's computer. Optees does not
host a remote solver service and does not make a cloud agent able to reach
`127.0.0.1`. A remote or sandboxed agent needs an explicitly supported bridge.

## Runtime Surfaces

| Surface | Process boundary | Contract | Primary use |
| --- | --- | --- | --- |
| Desktop GUI | In process | Application use cases and DTOs | Interactive education and visualization |
| `optees-cli` | One local process per command | JSON on stdin/stdout | Scripts, tests, and shell automation |
| `optees-server` | Local HTTP subprocess | REST JSON v1 plus OpenAPI | Long-lived local integrations and tool harnesses |
| `optees-mcp` | Agent-owned stdio subprocess | MCP tools | Native local agent integration |
| `optees-ollama-chat` | Local harness plus REST server | Ollama tools mapped to REST | Experimental local-LLM evaluation |

Python entry points are defined in `pyproject.toml`. Native PyInstaller
artifacts package a dedicated MCP stdio companion on Windows, macOS, and Linux;
release CI initializes it and calls capability discovery on every platform.
The Windows bundle also includes the console-subsystem `optees-server.exe`
REST companion. The GUI launches it without a visible console, while packaging
smoke tests capture deterministic startup diagnostics independently from the
windowed `optees.exe` bootloader.

## Dependency Model

```mermaid
flowchart TB
    subgraph Delivery["Delivery and presentation"]
        GUI["presentation: PySide6 views and controllers"]
        CLI["cli: JSON command interface"]
        HTTP["interfaces.http: FastAPI adapter"]
        MCP["interfaces.mcp: MCP stdio adapter"]
    end

    subgraph Application["Application"]
        Contracts["contracts: descriptors, envelopes, errors, validation"]
        Services["services: registry, optimization, jobs, process manager"]
        UseCases["usecases: solver-specific orchestration"]
        Ports["ports: solver interfaces"]
        Codecs["codecs: public JSON to domain and result JSON"]
        Validators["validation: independent result checks"]
    end

    subgraph Domain["Domain"]
        Models["models and value objects"]
        Results["solution entities"]
    end

    subgraph Infrastructure["Infrastructure"]
        Adapters["data.adapters: concrete solver implementations"]
        Engines["external numerical engines and internal algorithms"]
    end

    GUI --> UseCases
    GUI --> Services
    CLI --> Services
    HTTP --> Services
    MCP --> Services
    Services --> Contracts
    Services --> Codecs
    Services --> Validators
    Services --> UseCases
    UseCases --> Ports
    UseCases --> Models
    UseCases --> Results
    Codecs --> Models
    Codecs --> Results
    Validators --> Models
    Validators --> Results
    Adapters -. "implement" .-> Ports
    Adapters --> Engines
    Adapters --> Models
    Adapters --> Results
```

The composition root in `src/optees/composition/local_agent.py` is allowed to
know both application abstractions and concrete adapters. It constructs the
production registry and is the only place where all public capabilities are
wired together.

## Post-Solve Artifacts And Reports

Result artifacts and reports are separate, opt-in workflows layered on a
completed solver job. They use the retained validated problem payload and its
execution envelope; they do not alter the result contract or rerun the solver.

```mermaid
flowchart TB
    Job["Completed local job"] --> Problem["Versioned problem payload"]
    Job --> Result["Execution envelope and validation"]
    Problem --> Prepare["Capability artifact preparer"]
    Result --> Prepare
    Prepare --> Renderer["Headless renderer port"]
    Renderer --> ArtifactStore["Bounded session artifact store"]
    ArtifactStore --> RESTDownload["Authenticated REST download"]
    ArtifactStore --> MCPResource["MCP resource or retrieval tool"]
    ArtifactStore --> Composer["Report composer"]
    Composer --> ReportStore["Markdown or optional PDF"]
```

The rendering worker is bounded and independent from the mathematical job
worker, so an expensive chart or document cannot delay solver execution.
Application contracts and lifecycle rules are defined in
`RESULT_ARTIFACTS_CONTRACT.md`; delivery status is tracked in
`RESULT_ARTIFACTS_REPORTING_ROADMAP.md`. Infrastructure renderers must remain
headless and must not import PySide6 or Qt-specific Matplotlib backends.

`ArtifactStoragePort` keeps artifact lifecycle semantics outside HTTP and MCP.
Its local filesystem adapter creates one private temporary directory per
process session and returns only opaque `artifact-*` identifiers. Writes are
atomic, files are readable only by the current user, and every read verifies
the retained byte count and SHA-256 digest. The adapter enforces the frozen
per-file, total-byte, item-count, and lifetime limits. Capacity pressure removes
expired entries first and then the oldest unpinned entries; report composition
can pin inputs so active work is never evicted. Closing the session removes the
entire isolated directory. Neither the application contract nor a future
transport response exposes its absolute path.

`ArtifactGenerationService` owns the asynchronous artifact lifecycle. It reads
an immutable problem/result pair through `ArtifactSourcePort`, validates the
entire batch against registered headless renderers, records public manifest
IDs, delegates bytes to `ArtifactStoragePort`, and maps public IDs to private
storage IDs. The authenticated HTTP adapter only translates DTOs and returns
already verified bytes; it does not select renderers, inspect job repositories,
or access filesystem paths.

```mermaid
sequenceDiagram
    participant Client as "REST client"
    participant API as "Authenticated local API"
    participant Artifacts as "ArtifactGenerationService"
    participant Jobs as "ArtifactSourcePort"
    participant Renderer as "Bounded renderer worker"
    participant Store as "ArtifactStoragePort"

    Client->>API: "POST job artifacts"
    API->>Artifacts: "submit(versioned request)"
    Artifacts->>Jobs: "artifact_source(job_id)"
    Artifacts-->>API: "queued manifest"
    API-->>Client: "202 Accepted"
    Artifacts->>Renderer: "render(context)"
    Renderer-->>Artifacts: "media type + bytes"
    Artifacts->>Store: "store(bytes, TTL)"
    Client->>API: "GET job artifacts"
    API-->>Client: "current manifest"
    Client->>API: "GET artifact_id"
    API->>Artifacts: "download(public ID)"
    Artifacts->>Store: "get(private ID)"
    Store-->>Artifacts: "SHA-256 verified bytes"
    API-->>Client: "private, no-store response"
```

## Source Ownership

```text
src/optees/
  application/
    codecs/          public problem/result serialization
    contracts/       versioned transport-neutral contracts
    dtos/            application data transfer objects
    ports/           solver interfaces implemented by adapters
    services/        registry, synchronous solve, jobs, server process
    usecases/        solver-specific application orchestration
    validation/      independent solution validators
  composition/       production dependency wiring
  core/              version, strings, settings, and shared app services
  data/adapters/     numerical, algorithm, and local filesystem adapters
  domain/
    entities/        solver results
    models/          problem models
    value_objects/   validated domain values
  interfaces/
    agents/          local agent harness support
    http/            authenticated REST adapter
    mcp/             MCP stdio adapter
  presentation/      PySide6 controllers and views
  utility/           format importers and focused numerical helpers
```

## Capability Core

Each `RegisteredCapability` combines one public descriptor with the functions
needed to parse, execute, serialize, and optionally validate or cancel that
capability. This avoids a central solver-specific conditional in the service.

```mermaid
classDiagram
    class CapabilityDescriptor {
        +str capability_id
        +str problem_schema_version
        +str result_schema_version
        +dict problem_schema
        +dict result_schema
        +bool available
        +tuple backend_ids
        +to_dict()
    }

    class RegisteredCapability {
        +CapabilityDescriptor descriptor
        +Callable parse_problem
        +Callable execute
        +Callable serialize_result
        +Callable validate_result
        +Callable cancel_execution
    }

    class CapabilityRegistry {
        +register(capability)
        +get(capability_id)
        +list_descriptors()
    }

    class OptimizationService {
        +list_capabilities()
        +validate(capability_id, payload)
        +solve(capability_id, payload)
    }

    class LocalJobService {
        +validate(capability_id, payload)
        +submit(capability_id, payload)
        +validate_batch(batch)
        +submit_batch(batch)
        +batch_status(batch_id)
        +batch_result(batch_id)
        +cancel_batch(batch_id)
        +status(job_id)
        +result(job_id)
        +cancel(job_id)
    }

    class InMemoryJobRepository {
        +add(record)
        +add_many(records)
        +get(job_id)
        +replace(job_id, changes)
        +list()
    }

    class ResultCodec {
        <<protocol role>>
        +serialize(result)
    }

    class IndependentValidator {
        <<optional protocol role>>
        +validate(problem, result)
    }

    CapabilityRegistry "1" o-- "many" RegisteredCapability
    RegisteredCapability --> CapabilityDescriptor
    RegisteredCapability --> ResultCodec
    RegisteredCapability --> IndependentValidator
    OptimizationService --> CapabilityRegistry
    LocalJobService --> OptimizationService
    LocalJobService --> InMemoryJobRepository
```

The diagram shows architectural roles, not Python inheritance. Codecs and
validators are supplied as callables on the registration object.

## Capability Inventory

The production composition currently registers 12 capability IDs:

- `lp.continuous`
- `milp.linear`
- `knapsack.zero_one`
- `knapsack.bounded`
- `knapsack.unbounded`
- `knapsack.fractional`
- `knapsack.multi_dimensional`
- `nlp.continuous_local`
- `graph.shortest_path.dijkstra`
- `ml.regression.linear`
- `ml.classification.binary_logistic`
- `packing.single_container_3d`

The runtime descriptor is authoritative for availability, accepted schema,
backend choices, defaults, limits, and cancellation support. Clients should
discover it instead of hardcoding this list.

## Discovery And Execution

The asynchronous service deliberately separates payload validation from job
creation and result retrieval.

```mermaid
sequenceDiagram
    actor Client
    participant Transport as REST or MCP adapter
    participant Jobs as LocalJobService
    participant Service as OptimizationService
    participant Registry as CapabilityRegistry
    participant Worker as Single worker executor
    participant Solver as Registered capability
    participant Validator as Optional independent validator

    Client->>Transport: List capabilities
    Transport->>Jobs: list_capabilities()
    Jobs->>Service: list_capabilities()
    Service->>Registry: list_descriptors()
    Registry-->>Client: Versioned descriptors

    Client->>Transport: Inspect selected capability
    Transport-->>Client: Problem and result schemas
    Client->>Transport: Validate exact problem payload
    Transport->>Jobs: validate(capability_id, problem)
    Jobs->>Service: validate(...)
    Service->>Solver: parse_problem(problem)
    Solver-->>Client: Valid or structured errors

    Client->>Transport: Create job with identical payload
    Transport->>Jobs: submit(...)
    Jobs-->>Client: Queued job snapshot
    Jobs->>Worker: Execute job
    Worker->>Service: solve(...)
    Service->>Solver: parse, execute, serialize
    opt Validator registered
        Service->>Validator: validate(problem, result)
        Validator-->>Service: Verification report
    end
    Service-->>Worker: Execution envelope

    loop Until terminal
        Client->>Transport: Get job status
        Transport-->>Client: Job snapshot
    end
    Client->>Transport: Get result
    Transport-->>Client: Envelope or structured error
```

REST accepts validation and submission as separate calls but does not retain a
per-client proof that they are identical. The stateful MCP facade does retain
that proof and rejects job creation until the same capability and normalized
payload have passed validation.

### Bounded Batch Execution

Independent repeated scenarios can be submitted through the versioned batch
contract instead of manually coordinating three calls per problem. A batch:

- contains between 1 and 32 items with unique client-defined identifiers;
- may mix capabilities, provided every descriptor has first been inspected by
  an MCP client;
- validates every item before submission and creates no jobs if any item is
  invalid, unavailable, or cannot fit in the bounded repository;
- retains one ordinary job, execution envelope, mathematical status, and
  independent validation report per item;
- adds only aggregate lifecycle, mathematical-status, and validation-status
  counts.

The MVP remains deliberately single-worker. Batch fan-out is logical and
bounded: it removes agent-side coordination without running numerical backends
concurrently or weakening their individual validation. It is appropriate for
independent regressions, scenarios, or parameter sweeps. It is not workflow
orchestration and must not be used when one result is an input to a later job.

## Status Semantics

Transport lifecycle must not be inferred from mathematical outcome, or vice
versa.

```mermaid
stateDiagram-v2
    [*] --> queued: submit
    queued --> running: worker starts
    queued --> cancelled: cancel before start
    running --> cancelled: accepted cancellation
    running --> completed: envelope produced
    running --> failed: technical failure
    completed --> [*]
    cancelled --> [*]
    failed --> [*]
```

An execution envelope separately reports:

- **job status:** `completed`, `cancelled`, or `failed` at terminal time;
- **mathematical status:** `optimal`, `feasible`, `infeasible`, `unbounded`, or
  `not_solved`;
- **termination reason:** completion, time/iteration limit, cancellation,
  dependency failure, or internal error;
- **solution validation:** `verified`, `partial`, `failed`, or `not_available`.

For example, a technically completed job may be mathematically infeasible. A
feasible solution may terminate at a time limit. A solver-reported optimum may
still have independent validation marked `not_available`.

## Runtime Boundaries

### Desktop Direct Invocation

```mermaid
flowchart LR
    View["PySide6 view"] --> Controller["Presentation controller"]
    Controller --> UseCase["Application use case"]
    UseCase --> Port["Solver port"]
    Adapter["Concrete solver adapter"] -. "implements" .-> Port
    Adapter --> Engine["Numerical engine"]
    UseCase --> View
```

Interactive views use focused use cases and DTOs directly. They do not make an
HTTP round trip to the local server.

### Authenticated Loopback REST

```mermaid
flowchart LR
    Client["Local client or tool harness"] -->|"Bearer token + JSON"| API["FastAPI on 127.0.0.1"]
    API --> Guard["Media type, body size, and request ID guards"]
    Guard --> Jobs["LocalJobService"]
    Jobs --> Worker["Bounded in-memory queue and one worker"]
    Worker --> Core["OptimizationService"]
```

The desktop starts this server as a subprocess from Settings. A fresh token is
generated for each server session and is copied only through an explicit user
action. The unprotected `/health` endpoint exposes no solver data; API v1 and
its OpenAPI document require authentication.

### MCP Stdio

```mermaid
flowchart LR
    Agent["MCP-compatible local agent"] <-->|"private stdio"| Server["optees-mcp subprocess"]
    Server --> Facade["Discovery and validation state machine"]
    Facade --> Jobs["LocalJobService"]
    Jobs --> Core["OptimizationService"]
```

MCP needs neither a TCP port nor a bearer token because the client launches
and owns the private subprocess. It exposes tools to list and inspect
capabilities, validate a problem, create a job, inspect status, retrieve a
result, and cancel a job.

## Independent Solution Validation

Independent validation recomputes selected mathematical properties from the
problem and returned candidate rather than trusting only the solver status.
The validation contract records checks, measurements, violations, tolerances,
and limitations.

Current production registrations provide independent validators for:

- `lp.continuous`: candidate vector, bounds, linear constraints, and objective
  consistency;
- `milp.linear`: the corresponding checks plus integrality where applicable.
- `ml.regression.linear`: finite public parameters, complete prediction rows,
  prediction and residual arithmetic, train/test split accounting, and
  recomputed metrics.

Other capabilities explicitly return `not_available` until a dedicated
validator is implemented. Passing these checks verifies the recorded
properties; it is not, by itself, a second proof of global optimality.

Capability availability is also a runtime property. The production composition
imports the concrete optional backend API, and continuous LP additionally runs
a trivial HiGHS health problem before advertising itself as available. Native
release smoke tests execute that same LP through the packaged MCP companion so
missing compiled modules are detected before publication.

## Composed Agent Workflows

Optees capabilities are intentionally atomic. An external agent may compose
them, but it remains responsible for translating outputs into the next
versioned input, declaring assumptions, and requesting confirmation when the
business meaning changes.

```mermaid
flowchart LR
    Data["Historical demand data"] --> Agent["External agent or workflow engine"]
    Agent --> Forecast["ml.regression.linear"]
    Forecast -->|"forecast + declared assumptions"| Agent
    Agent --> Plan["milp.linear"]
    Plan -->|"production quantities"| Agent
    Agent --> Pack["packing.single_container_3d"]
    Pack --> Report["Validated atomic results and final report"]

    Confirm["User confirmation at semantic boundaries"] -.-> Agent
```

Each capability validates only its own contract and result. Optees does not
currently certify the semantic correctness of the complete composed workflow.

## Extending The Platform

To add a public solver capability:

1. define or reuse domain problem and result types;
2. define an application solver port and use case;
3. implement the concrete adapter;
4. add strict public problem and result codecs;
5. create a `CapabilityDescriptor` with versioned schemas and honest limits;
6. optionally implement independent result validation and cancellation;
7. register the assembled `RegisteredCapability` in the composition root;
8. test contracts, service execution, transports, and relevant GUI flows;
9. update the algorithm and agent-integration documentation.

No REST or MCP route should need solver-specific branching when this extension
path is followed.

## Mermaid Convention

Architecture, state, sequence, and data-flow diagrams are Mermaid fenced
blocks in Markdown. GitHub renders them natively and their source remains
reviewable.

- Keep Mermaid source authoritative; do not commit duplicate images by
  default.
- Use quoted labels when punctuation or parentheses are present.
- Do not send internal schemas to online rendering services.
- Export SVG, PNG, or PDF only for a release artifact or offline document.
