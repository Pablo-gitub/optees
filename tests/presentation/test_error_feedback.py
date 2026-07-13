from __future__ import annotations

import pytest

from optees.core.string_manager import strings as S
from optees.presentation.error_feedback import localized_error_detail


@pytest.mark.parametrize(
    ("scope", "raw_error", "key"),
    [
        ("lp_import", "Invalid JSON: unexpected token", "error_feedback.import.read"),
        ("milp_import", "variables[0] must be an object", "error_feedback.import.schema"),
        ("knapsack_import", "cannot read knapsack JSON file", "error_feedback.import.read"),
        ("nlp_import", "unsupported NLP JSON version: '2'", "error_feedback.import.schema"),
        ("regression_import", "dataset must contain rows", "error_feedback.import.schema"),
        ("graph_import", "could not read graph JSON", "error_feedback.import.read"),
        ("nlp_validation", "invalid objective expression at line 1", "error_feedback.nlp.expression"),
        ("nlp_validation", "initial value must lie within bounds", "error_feedback.nlp.bounds"),
        ("regression_validation", "ridge_alpha must be positive", "error_feedback.regression.options"),
        ("regression_validation", "Regression data must contain at least four aligned rows", "error_feedback.regression.dataset"),
        ("classification_import", "unsupported Classification JSON version: '2'", "error_feedback.import.schema"),
        ("classification_validation", "Classification random_seed must be a non-negative integer", "error_feedback.classification.options"),
        ("classification_validation", "Classification data must contain exactly two non-empty labels", "error_feedback.classification.dataset"),
        ("graph_validation", "Dijkstra edge weights must be finite non-negative numbers", "error_feedback.graph.weights"),
        ("graph_validation", "Dijkstra source and destination must be declared vertices", "error_feedback.graph.topology"),
        ("graph_validation", "solver is not configured", "error_feedback.graph.solver"),
        ("assistant_import", "problem_type must be 'knapsack'", "error_feedback.assistant.generated_model"),
        ("update", "GitHub release request failed with HTTP 503", "error_feedback.update.check"),
        ("update", "No compatible update asset is available.", "error_feedback.update.download"),
    ],
)
@pytest.mark.parametrize("language", ("en", "it"))
def test_user_facing_error_feedback_is_localized_and_hides_raw_exception_text(
    scope: str,
    raw_error: str,
    key: str,
    language: str,
) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        message = localized_error_detail(scope, raw_error)

        assert message == S.t(key)
        assert raw_error not in message
        assert not message.startswith("error_feedback.")
    finally:
        S.set_language(previous)
