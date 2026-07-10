from __future__ import annotations

from optees.application.ports.problem_assistant_port import ProblemAssistantPort
from optees.domain.entities.assistant import AssistantAnalysis


class AnalyzeProblemDescriptionUseCase:
    def __init__(self, assistant: ProblemAssistantPort) -> None:
        self._assistant = assistant

    def execute(self, prompt: str, language: str = "en") -> AssistantAnalysis:
        return self._assistant.analyze(prompt, language=language)
