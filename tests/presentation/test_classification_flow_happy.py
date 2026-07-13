from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QPushButton

from _utils.fakes import FakeSolver
from optees.application.usecases.train_classification_usecase import TrainClassificationUseCase
from optees.core.string_manager import strings as S
from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
    ClassificationOptions,
)
from optees.domain.value_objects.classification.classification_status import ClassificationStatus


def _model() -> BinaryClassificationModel:
    return BinaryClassificationModel(
        ClassificationDataset.from_rows(
            feature_names=("score", "debt"),
            target_name="approved",
            rows=[
                ((38, 0.78), "no"), ((44, 0.70), "no"), ((51, 0.64), "no"), ((57, 0.55), "no"),
                ((68, 0.42), "yes"), ((74, 0.35), "yes"), ((81, 0.28), "yes"), ((88, 0.19), "yes"),
            ],
        ),
        ClassificationOptions(test_fraction=0.25, random_seed=17),
    )


def _trained_response() -> dict[str, object]:
    rows = _model().dataset.feature_rows
    labels = _model().dataset.target_values
    return {
        "status": "Trained",
        "negative_label": "no",
        "positive_label": "yes",
        "intercept": 0.2,
        "coefficients": {"score": 1.2, "debt": -0.8},
        "train_metrics": {"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
        "test_metrics": {"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0},
        "train_confusion": {"true_negative": 3, "false_positive": 0, "false_negative": 0, "true_positive": 3},
        "test_confusion": {"true_negative": 1, "false_positive": 0, "false_negative": 0, "true_positive": 1},
        "predictions": [
            {
                "row_index": index,
                "actual": label,
                "predicted": label,
                "probability_positive": 0.9 if label == "yes" else 0.1,
                "partition": "test" if index in {1, 5} else "train",
            }
            for index, (features, label) in enumerate(zip(rows, labels, strict=True))
        ],
        "extras": {
            "method": "LogisticRegression",
            "train_count": 6,
            "test_count": 2,
            "random_seed": 17,
            "iterations": 101,
            "converged": True,
            "feature_means": {"score": 64.0, "debt": 0.5},
            "feature_scales": {"score": 16.0, "debt": 0.2},
        },
    }


def test_home_card_opens_classification_page(window, qtbot) -> None:
    assert window.home_page.card_classification.parentWidget() is window.home_page.cat_ml

    qtbot.mouseClick(window.home_page.card_classification, Qt.LeftButton)

    assert window.stack.currentWidget() is window.classification_page


def test_classification_form_trains_and_navigates_to_solution(window, qtbot) -> None:
    fake = FakeSolver(_trained_response())
    window.classification_page.set_model(_model())
    window.classification_page.set_solve_usecase(TrainClassificationUseCase(fake))
    window.goto("classification")

    with qtbot.waitSignal(window.classification_page.solve_completed, timeout=1000) as blocker:
        qtbot.mouseClick(window.classification_page.btn_train, Qt.LeftButton)

    solution = blocker.args[0]
    assert solution.status is ClassificationStatus.TRAINED
    assert fake.last_problem == {
        "feature_names": ["score", "debt"],
        "target_name": "approved",
        "feature_rows": [[38.0, 0.78], [44.0, 0.7], [51.0, 0.64], [57.0, 0.55], [68.0, 0.42], [74.0, 0.35], [81.0, 0.28], [88.0, 0.19]],
        "target_values": ["no", "no", "no", "no", "yes", "yes", "yes", "yes"],
        "method": "LogisticRegression",
        "test_fraction": 0.25,
        "random_seed": 17,
        "learning_rate": 0.1,
        "max_iterations": 2000,
        "l2_alpha": 0.0,
    }
    assert window.stack.currentWidget() is window.classification_solution_page
    assert window.classification_solution_page.coefficient_table.rowCount() == 3
    assert window.classification_solution_page.metrics_table.rowCount() == 2
    assert window.classification_solution_page.confusion_table.rowCount() == 4
    assert window.classification_solution_page.predictions_table.rowCount() == 8
    assert window.classification_solution_page.coefficient_table.item(0, 1).textAlignment() == int(Qt.AlignCenter)
    assert window.classification_solution_page.boundary_plot.visualization_state == "ready"


def test_classification_json_import_populates_dataset_and_options(window, qtbot, monkeypatch, tmp_path) -> None:
    data = {
        "version": "1",
        "problem_type": "binary_classification",
        "dataset": {
            "feature_names": ["score", "debt"],
            "target_name": "approved",
            "rows": [
                {"features": [38, 0.78], "target": "no"}, {"features": [44, 0.70], "target": "no"},
                {"features": [51, 0.64], "target": "no"}, {"features": [68, 0.42], "target": "yes"},
                {"features": [74, 0.35], "target": "yes"}, {"features": [81, 0.28], "target": "yes"},
            ],
        },
        "training_options": {"test_fraction": 0.5, "random_seed": 11, "learning_rate": 0.05, "max_iterations": 300, "l2_alpha": 0.3},
    }
    path = tmp_path / "classification.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "optees.presentation.views.classification_view.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(path), ""),
    )
    window.goto("classification")

    qtbot.mouseClick(window.classification_page.btn_import_json, Qt.LeftButton)

    assert window.classification_page.findChild(QLineEdit, "classificationFeatureNames").text() == "score, debt"
    assert window.classification_page.findChild(QLineEdit, "classificationTargetName").text() == "approved"
    assert window.classification_page.data_table.columnCount() == 3
    assert window.classification_page.data_table.rowCount() == 6
    assert window.classification_page.data_table.item(0, 0).text() == "38"
    assert window.classification_page.data_table.item(0, 2).text() == "no"
    assert window.classification_page.findChild(QLineEdit, "classificationRandomSeed").text() == "11"


def test_classification_pages_controls_and_translations(window, qtbot) -> None:
    window.goto("classification")
    page = window.classification_page

    assert page.findChild(QPushButton, "classificationImportJsonButton").text()
    assert page.findChild(QPushButton, "classificationTrainButton").text()
    assert page.btn_json_info.property("variant") == "info"
    assert page.btn_json_info.text() == "i"

    qtbot.mouseClick(page.btn_example, Qt.LeftButton)
    assert window.stack.currentWidget() is window.classification_example_page
    window.goto("classification")
    qtbot.mouseClick(page.btn_problem, Qt.LeftButton)
    assert window.stack.currentWidget() is window.classification_problem_page

    previous = S.current_language()
    try:
        for language in ("en", "it"):
            S.set_language(language)
            assert page.btn_train.text() == S.t("classification.actions.train")
            assert page.btn_import_json.text() == S.t("classification.import.button")
            assert "classification." not in page.title.text()
    finally:
        S.set_language(previous)
