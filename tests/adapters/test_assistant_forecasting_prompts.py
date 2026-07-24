"""Matched English and Italian forecasting recommendations."""

from __future__ import annotations

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter


SCENARIOS = (
    (
        "Forecast the next 6 monthly periods from this chronological sales time series.",
        "Prevedi i prossimi 6 periodi mensili da questa serie temporale cronologica delle vendite.",
    ),
    (
        "Our weekly order history has trend and seasonality. Estimate the future periods.",
        "Il nostro storico settimanale degli ordini ha trend e stagionalita'. Stima i periodi futuri.",
    ),
    (
        "Use Holt-Winters on dated demand observations and produce a forecast horizon.",
        "Usa Holt-Winters sulle osservazioni datate della domanda e produci un orizzonte di previsione.",
    ),
    (
        "I wrote down daily shop revenue by date. What might the next days look like?",
        "Ho annotato l'incasso giornaliero del negozio per data. Come potrebbero essere i prossimi giorni?",
    ),
)


@pytest.mark.parametrize(
    ("prompt", "language"),
    [
        pytest.param(pair[index], language, id=f"{number}-{language}")
        for number, pair in enumerate(SCENARIOS, start=1)
        for index, language in enumerate(("en", "it"))
    ],
)
def test_assistant_recognizes_forecasting_without_inventing_history(
    prompt: str,
    language: str,
) -> None:
    analysis = RuleBasedAssistantAdapter().analyze(prompt, language=language)

    assert analysis.family == "forecasting"
    assert analysis.variant == "univariate_time_series"
    assert analysis.implemented
    assert analysis.model_json is None
    assert analysis.load_target is None
    assert analysis.needs_clarification
    assert analysis.reasons
    assert analysis.missing_information
