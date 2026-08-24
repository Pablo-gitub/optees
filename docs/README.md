# Optees Documentation

This index organizes the documentation by purpose. A document's directory
describes what it is; roadmap delivery state is tracked separately in the
[roadmap index](roadmaps/README.md), so files do not move whenever their status
changes.

## Architecture And Contracts

- [Architecture overview](architecture/overview.md): dependency boundaries,
  runtime surfaces, and Mermaid diagrams.
- [Forecasting statistical contract](contracts/forecasting-statistical-contract.md):
  frozen statistical terminology and behavior.
- [Result artifacts contract](contracts/result-artifacts-contract.md): frozen
  artifact inventory, lifecycle, limits, and report schema.

## User And Maintainer Guides

- [Development setup](guides/development.md)
- [Testing strategy](guides/testing.md)
- [Release procedure](guides/releasing.md)
- [Agent service configuration](guides/agent-service-configuration.md)
- [Local result artifacts and reports](guides/local-reporting.md)
- [Website deployment](guides/website-deployment.md)
- [Local service and agent integration guides](guides/local-agent/README.md)

## Mathematical Reference

- [Algorithms](reference/algorithms.md): implemented and planned method
  catalogue with honest result semantics.
- [Datasets](reference/datasets.md): scientific, external, analytic, and
  deterministic test-data provenance.

## Product Planning

- [Roadmap index and delivery status](roadmaps/README.md)
- [Authoritative project roadmap](roadmaps/project.md)

## Evidence And Audits

- [Agent benchmark protocol](evidence/agent-benchmarks.md)
- [Documentation truth audit](evidence/documentation-audit.md)
- [Native distribution factual audit](evidence/native-distribution-audit.md)

## Historical Material

[Archive](archive/README.md) contains superseded plans and historical
implementation evidence. Archived documents describe their original context;
they are not current implementation instructions.

For the product overview, installation, screenshots, and available workflows,
return to the [project README](../README.md).
