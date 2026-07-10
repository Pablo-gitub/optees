from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AssistantAnalysis:
    """Result produced by the local modeling assistant.

    The assistant is intentionally conservative: it may recommend a model
    family even when it cannot safely draft a JSON model. A draft is considered
    loadable only after it passes the same importer used by the GUI.
    """

    family: str
    variant: str
    confidence: float
    implemented: bool
    load_target: str | None = None
    reasons: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    model_json: Mapping[str, Any] | None = None
    validation_errors: tuple[str, ...] = ()
    language: str = "en"

    @property
    def is_loadable(self) -> bool:
        return (
            self.implemented
            and self.load_target is not None
            and self.model_json is not None
            and not self.validation_errors
        )

    @property
    def needs_clarification(self) -> bool:
        return bool(self.missing_information)
