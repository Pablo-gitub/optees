from __future__ import annotations

from typing import Protocol

from optees.domain.entities.assistant import AssistantAnalysis


class ProblemAssistantPort(Protocol):
    """Port for local or future provider-backed modeling assistants."""

    def analyze(self, prompt: str, language: str = "en") -> AssistantAnalysis:
        """Classify a natural-language problem description and draft a model when safe.

        ``language`` is the language the user selected in Settings; it decides the
        language of the explanations, never the prompt itself.
        """
