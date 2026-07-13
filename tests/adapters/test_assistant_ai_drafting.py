"""Safe local drafting of explicitly structured AI datasets.

The assistant may recognize regression and classification from normal prose,
but it drafts a trainable dataset only when the user provides named columns and
unambiguous pipe-separated rows. Every draft is checked again by the canonical
JSON importer.
"""

from __future__ import annotations

import pytest

from optees.data.adapters.assistant import RuleBasedAssistantAdapter
from optees.utility.classification_json_io import classification_model_from_dict
from optees.utility.regression_json_io import regression_model_from_dict


@pytest.fixture()
def assistant() -> RuleBasedAssistantAdapter:
    return RuleBasedAssistantAdapter()


@pytest.mark.parametrize(
    ("language", "prompt", "feature_names", "target_name", "first_target"),
    [
        (
            "en",
            "Fit linear regression. Features: floor_area, rooms; target: price; "
            "rows: 50 | 2 | 120; 60 | 2 | 140; 70 | 3 | 170; 80 | 3 | 200",
            ("floor_area", "rooms"),
            "price",
            120.0,
        ),
        (
            "it",
            "Adatta una regressione lineare. Caratteristiche: superficie, stanze; "
            "bersaglio: prezzo; righe: 50,5 | 2 | 120,5; 60 | 2 | 140; "
            "70 | 3 | 170; 80 | 3 | 200",
            ("superficie", "stanze"),
            "prezzo",
            120.5,
        ),
    ],
)
def test_assistant_drafts_valid_regression_dataset_in_both_languages(
    assistant: RuleBasedAssistantAdapter,
    language: str,
    prompt: str,
    feature_names: tuple[str, ...],
    target_name: str,
    first_target: float,
) -> None:
    analysis = assistant.analyze(prompt, language=language)

    assert analysis.family == "regression"
    assert analysis.load_target == "regression"
    assert analysis.is_loadable
    assert analysis.model_json is not None
    model = regression_model_from_dict(dict(analysis.model_json))
    assert model.dataset.feature_names == feature_names
    assert model.dataset.target_name == target_name
    assert model.dataset.target_values[0] == first_target


@pytest.mark.parametrize(
    ("language", "prompt", "labels"),
    [
        (
            "en",
            "Train binary classification for approvals. Features: income, debt; "
            "target: decision; rows: 30 | 8 | rejected; 32 | 7 | rejected; "
            "35 | 8 | rejected; 70 | 2 | approved; 75 | 3 | approved; 80 | 2 | approved",
            ("approved", "rejected"),
        ),
        (
            "it",
            "Addestra una classificazione binaria per le richieste. "
            "Caratteristiche: reddito, debito; bersaglio: decisione; "
            "righe: 30 | 8 | rifiutato; 32 | 7 | rifiutato; 35 | 8 | rifiutato; "
            "70 | 2 | approvato; 75 | 3 | approvato; 80 | 2 | approvato",
            ("approvato", "rifiutato"),
        ),
    ],
)
def test_assistant_drafts_valid_binary_classification_dataset_in_both_languages(
    assistant: RuleBasedAssistantAdapter,
    language: str,
    prompt: str,
    labels: tuple[str, str],
) -> None:
    analysis = assistant.analyze(prompt, language=language)

    assert analysis.family == "classification"
    assert analysis.load_target == "classification"
    assert analysis.is_loadable
    assert analysis.model_json is not None
    model = classification_model_from_dict(dict(analysis.model_json))
    assert model.dataset.labels == labels
    assert model.dataset.row_count == 6


@pytest.mark.parametrize(
    ("language", "prompt", "expected"),
    [
        (
            "en",
            "Fit linear regression. Features: area, rooms; target: price; "
            "rows: 50, 2, 120; 60, 2, 140; 70, 3, 170; 80, 3, 200",
            "explicit dataset table",
        ),
        (
            "it",
            "Addestra una classificazione binaria. Caratteristiche: reddito, debito; "
            "bersaglio: decisione; righe: 30, 8, rifiutato; 70, 2, approvato",
            "tabella dati esplicita",
        ),
    ],
)
def test_assistant_never_guesses_ambiguous_comma_separated_rows(
    assistant: RuleBasedAssistantAdapter,
    language: str,
    prompt: str,
    expected: str,
) -> None:
    analysis = assistant.analyze(prompt, language=language)

    assert not analysis.is_loadable
    assert analysis.load_target is None
    assert analysis.model_json is None
    assert any(expected in detail for detail in analysis.missing_information)


def test_assistant_keeps_importer_rejections_non_loadable(
    assistant: RuleBasedAssistantAdapter,
) -> None:
    analysis = assistant.analyze(
        "Train binary classification. Features: income; target: decision; "
        "rows: 30 | rejected; 70 | approved",
        language="en",
    )

    assert analysis.family == "classification"
    assert not analysis.is_loadable
    assert analysis.load_target is None
    assert analysis.model_json is None
    assert analysis.validation_errors
