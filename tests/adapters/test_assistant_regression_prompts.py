"""Rule-based regression recommendations across equivalent English and Italian prompts.

The assistant deliberately does not infer a dataset from prose: it may recommend
the implemented OLS/Ridge workflow, but a user must still enter or import the
observations before a formulation can be trained.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter


@dataclass(frozen=True)
class RegressionScenario:
    level: int  # 1 = most technical, 5 = most colloquial
    name: str
    prompt_en: str
    prompt_it: str


SCENARIOS: tuple[RegressionScenario, ...] = (
    RegressionScenario(
        1,
        "expert_ols",
        "Fit an ordinary least squares linear regression to historical numerical observations, using floor area and rooms as features and sale price as the continuous target.",
        "Adatta una regressione lineare ai minimi quadrati ordinari a osservazioni numeriche storiche, usando superficie e numero di stanze come feature e prezzo di vendita come target continuo.",
    ),
    RegressionScenario(
        2,
        "technical_ridge",
        "I need a Ridge regression trained on a dataset of past transactions to estimate a continuous price from several numerical features.",
        "Mi serve una regressione Ridge addestrata su un dataset di transazioni passate per stimare un prezzo continuo da diverse feature numeriche.",
    ),
    RegressionScenario(
        3,
        "analyst_house_prices",
        "I have records of previous house sales with size, number of rooms, and final price. I want to predict the price of a new house.",
        "Ho i dati delle vendite precedenti di case con superficie, numero di stanze e prezzo finale. Voglio prevedere il prezzo di una nuova casa.",
    ),
    RegressionScenario(
        4,
        "practitioner_energy_usage",
        "For several past months I recorded outside temperature, working days, and electricity consumption. I need an estimate of next month's consumption.",
        "Per diversi mesi passati ho registrato temperatura esterna, giorni lavorativi e consumo di elettricita'. Mi serve una stima del consumo del prossimo mese.",
    ),
    RegressionScenario(
        5,
        "novice_rent_estimate",
        "I wrote down what similar apartments rented for, how big they were, and where they were. Can the app estimate a fair rent for mine?",
        "Ho annotato quanto costavano in affitto appartamenti simili, quanto erano grandi e dove si trovavano. L'app puo' stimare un affitto equo per il mio?",
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


def _prompt(scenario: RegressionScenario, language: str) -> str:
    return scenario.prompt_en if language == "en" else scenario.prompt_it


@pytest.mark.parametrize(("scenario", "language"), CASES)
def test_assistant_recommends_linear_regression_for_matched_human_prompts(
    assistant: RuleBasedAssistantAdapter,
    scenario: RegressionScenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language), language=language)

    assert analysis.family == "regression"
    assert analysis.variant == "linear_regression"
    assert analysis.implemented
    assert analysis.load_target is None
    assert analysis.confidence >= 0.6
    assert analysis.reasons


@pytest.mark.parametrize(("scenario", "language"), CASES)
def test_assistant_keeps_prose_only_regression_prompts_non_loadable(
    assistant: RuleBasedAssistantAdapter,
    scenario: RegressionScenario,
    language: str,
) -> None:
    analysis = assistant.analyze(_prompt(scenario, language), language=language)

    assert not analysis.is_loadable
    assert analysis.model_json is None
    assert analysis.needs_clarification
    assert analysis.missing_information
