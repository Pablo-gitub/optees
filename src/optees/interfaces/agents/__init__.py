"""Experimental local-agent interfaces over stable Optees contracts."""

from optees.interfaces.agents.ollama_harness import (
    AgentRun,
    OllamaAgentHarness,
    OllamaClient,
    OpteesToolFacade,
    UrllibJsonTransport,
)

__all__ = [
    "AgentRun",
    "OllamaAgentHarness",
    "OllamaClient",
    "OpteesToolFacade",
    "UrllibJsonTransport",
]
