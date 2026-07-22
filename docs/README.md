# Optees Documentation

This index separates product usage, mathematical references, integration, and
project maintenance. Statements about native installation remain subject to
the packaged-artifact acceptance matrix.

## Use Optees

- [Project README](../README.md): product overview, screenshots, installation,
  source setup, and available workflows.
- [Algorithms](ALGORITHMS.md): concise implemented and planned method
  catalogue.
- [Datasets and formats](DATASETS.md): scientific, external, analytic, and
  deterministic test-data provenance.
- [Testing](TESTING.md): local feedback, markers, focused suites, and full
  regression commands.

## Integrate Local Agents And Applications

- [Agent service configuration](AGENTS_SERVICE_CONFIG.md): common setup,
  Claude Desktop/Cowork, Ollama, and planned OpenAI GPT compatibility.
- [Local server and desktop controls](local-agent/server-process-and-desktop.md):
  authenticated loopback service lifecycle.
- [Local REST API](local-agent/local-rest-api.md): HTTP endpoints, jobs,
  authentication, and security boundaries.
- [MCP stdio](local-agent/mcp-stdio.md): private local MCP process and
  allowlisted tools.
- [Headless CLI](local-agent/headless-cli.md): machine-readable discovery,
  validation, and execution.
- [Ollama D0 harness](local-agent/ollama-d0-harness.md): experimental local LLM
  compatibility workflow.
- [Pre-service capability inventory](local-agent/pre-service-capability-inventory.md):
  historical baseline retained for refactoring evidence.

## Understand And Extend The Architecture

- [Architecture](ARCHITECTURE.md): dependency boundaries and Mermaid diagrams.
- [Local job service](local-agent/job-service.md): application-owned execution
  lifecycle.
- [Result artifact and report contracts](RESULT_ARTIFACTS_CONTRACT.md): frozen
  post-solve artifact inventory, lifecycle, limits, and report schema.
- [Result artifacts and local reporting roadmap](RESULT_ARTIFACTS_REPORTING_ROADMAP.md):
  phased implementation of headless exports and report composition.
- [Local agent service roadmap](LOCAL_AGENT_SERVICE_ROADMAP.md): contracts,
  implementation history, independent validation, and future agent work.
- [Algorithms](ALGORITHMS.md): supported mathematical behavior and honest
  result semantics.

## Benchmarks And Evidence

- [Agent benchmark protocol](AGENT_BENCHMARKS.md): paired unaided and
  Optees-assisted experimental design.
- [Datasets and formats](DATASETS.md): solver benchmark sources and scope.
- [Documentation truth audit](DOCUMENTATION_AUDIT.md): current documentation
  discrepancies and verification status.

## Product And Family Roadmaps

- [Project roadmap](PROJECT_ROADMAP.md)
- [Documentation, website, release, and demonstration roadmap](DOCUMENTATION_WEBSITE_RELEASE_ROADMAP.md)
- [Native distribution roadmap](NATIVE_DISTRIBUTION_ROADMAP.md)
- [Native distribution factual audit](NATIVE_DISTRIBUTION_AUDIT.md): current
  artifact behavior, updater limitations, and clean-account acceptance matrix.
- [Packing and loading roadmap](PACKING_LOADING_ROADMAP.md)
- [Result artifacts and local reporting roadmap](RESULT_ARTIFACTS_REPORTING_ROADMAP.md)
- [MILP roadmap](MILP_ROADMAP.md)
- [MILP feature plan](MILP_FEATURE_PLAN.md)
- [NLP feature plan](NLP_FEATURE_PLAN.md)
- [Graph feature plan](GRAPH_FEATURE_PLAN.md)

## Release And Website Maintenance

- [Release procedure](RELEASING.md)
- [Native distribution roadmap](NATIVE_DISTRIBUTION_ROADMAP.md)
- [Native distribution factual audit](NATIVE_DISTRIBUTION_AUDIT.md)
- [Website deployment](WEBSITE_DEPLOYMENT.md)
