"""Binary-classification recommendations across matched English and Italian prose.

The rule-based assistant recommends the available formulation but deliberately
does not draft a dataset from free text: observations and labels must be
entered or imported explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter


@dataclass(frozen=True)
class ClassificationScenario:
    level: int  # 1 = most technical, 5 = most colloquial
    name: str
    prompt_en: str
    prompt_it: str


SCENARIOS: tuple[ClassificationScenario, ...] = (
    ClassificationScenario(
        1,
        "expert_logistic",
        "Train a binary logistic regression classifier on numeric features with a yes/no target label.",
        "Addestra un classificatore di regressione logistica binaria su feature numeriche con una classe target si/no.",
    ),
    ClassificationScenario(
        2,
        "technical_binary_labels",
        "I need binary classification of historical records using income and debt features to predict approved or rejected.",
        "Mi serve una classificazione binaria di record storici usando reddito e debito per prevedere approvata o rifiutata.",
    ),
    ClassificationScenario(
        3,
        "analyst_churn",
        "I have past customer observations with contract length and support calls. I want to predict whether a customer will renew or churn.",
        "Ho osservazioni passate dei clienti con durata contratto e chiamate al supporto. Voglio prevedere se un cliente rinnovera' oppure abbandonera'.",
    ),
    ClassificationScenario(
        4,
        "practitioner_spam",
        "From previous messages described by numeric measurements, I need to classify a new message as spam or not spam.",
        "Da messaggi precedenti descritti da misure numeriche, devo classificare un nuovo messaggio come spam oppure non spam.",
    ),
    ClassificationScenario(
        5,
        "novice_approval",
        "I wrote down scores and debt for old applications and whether they were accepted. Can the app tell me if a new application is likely to be approved?",
        "Ho annotato punteggi e debiti di vecchie domande e se erano accettate. L'app puo' dirmi se una nuova domanda probabilmente verra' approvata?",
    ),
)


CASES = [
    pytest.param(scenario, language, id=f"L{scenario.level}-{scenario.name}-{language}")
    for scenario in SCENARIOS
    for language in ("en", "it")
]


@pytest.fixture()
def assistant() -> RuleBasedAssistantAdapter:
    return RuleBasedAssistantAdapter()


def _prompt(scenario: ClassificationScenario, language: str) -> str:
    return scenario.prompt_en if language == "en" else scenario.prompt_it


@pytest.mark.parametrize(("scenario", "language"), CASES)
def test_assistant_recommends_binary_classification_for_matched_human_prompts(
    assistant: RuleBasedAssistantAdapter,
    scenario: ClassificationScenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language), language=language)

    assert analysis.family == "classification"
    assert analysis.variant == "binary_logistic_regression"
    assert analysis.implemented
    assert analysis.load_target is None
    assert analysis.confidence >= 0.6
    assert analysis.reasons


@pytest.mark.parametrize(("scenario", "language"), CASES)
def test_assistant_keeps_prose_only_classification_prompts_non_loadable(
    assistant: RuleBasedAssistantAdapter,
    scenario: ClassificationScenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language), language=language)

    assert not analysis.is_loadable
    assert analysis.model_json is None
    assert analysis.needs_clarification
    assert analysis.missing_information
