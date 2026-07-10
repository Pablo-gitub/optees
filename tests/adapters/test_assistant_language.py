"""The assistant must answer in the language the user picked in Settings.

Guessing the language from the prompt is unreliable (colloquial Italian carries
none of the usual markers) and conceptually wrong: if the UI is Italian, the
assistant must answer in Italian even when the problem is written in English.
"""
from __future__ import annotations

import pytest

from optees.application.usecases.analyze_problem_description_usecase import (
    AnalyzeProblemDescriptionUseCase,
)
from optees.data.adapters.assistant import RuleBasedAssistantAdapter


# Colloquial wording: a heuristic detector reads both of these as English.
_IT_PROMPT = "Riempio una scatola con lo stesso tipo di pezzo e posso metterne quanti ne voglio."
_EN_PROMPT = "I keep filling a box with the same kind of piece and I can put in as many as I want."

_MISSING = {
    "it": ("capacita'", "oggetti con valore e peso"),
    "en": ("capacity", "items with value and weight"),
}
_REASON_PREFIX = {"it": "Il testo", "en": "The prompt"}


@pytest.fixture()
def assistant() -> RuleBasedAssistantAdapter:
    return RuleBasedAssistantAdapter()


@pytest.mark.parametrize("language", ["it", "en"])
@pytest.mark.parametrize(
    "prompt",
    [_IT_PROMPT, _EN_PROMPT],
    ids=["italian-prompt", "english-prompt"],
)
def test_assistant_answers_in_the_requested_language_whatever_the_prompt_language(
    assistant: RuleBasedAssistantAdapter,
    prompt: str,
    language: str,
) -> None:
    analysis = assistant.analyze(prompt, language=language)

    assert analysis.language == language
    assert analysis.missing_information == _MISSING[language]
    assert analysis.reasons[0].startswith(_REASON_PREFIX[language])


def test_empty_prompt_is_reported_in_the_requested_language(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze("", language="it")

    assert analysis.language == "it"
    assert analysis.missing_information == ("descrizione del problema",)


def test_language_defaults_to_english(assistant: RuleBasedAssistantAdapter) -> None:
    analysis = assistant.analyze(_IT_PROMPT)

    assert analysis.language == "en"
    assert analysis.missing_information == _MISSING["en"]


def test_unsupported_language_falls_back_to_english(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze(_IT_PROMPT, language="fr")

    assert analysis.language == "en"
    assert analysis.missing_information == _MISSING["en"]


def test_usecase_forwards_the_requested_language(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    usecase = AnalyzeProblemDescriptionUseCase(assistant)

    analysis = usecase.execute(_EN_PROMPT, language="it")

    assert analysis.language == "it"
    assert analysis.missing_information == _MISSING["it"]
