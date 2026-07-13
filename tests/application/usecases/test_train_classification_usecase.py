from __future__ import annotations

from _utils.fakes import FakeSolver
from optees.application.usecases.train_classification_usecase import TrainClassificationUseCase
from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.models.classification.binary_classification_model import BinaryClassificationModel
from optees.domain.value_objects.classification.classification_status import ClassificationStatus


def test_usecase_maps_binary_dataset_to_solver_contract() -> None:
    model = BinaryClassificationModel(
        ClassificationDataset.from_rows(
            feature_names=("x",),
            target_name="class",
            rows=(((0,), "no"), ((1,), "no"), ((2,), "no"), ((4,), "yes"), ((5,), "yes"), ((6,), "yes")),
        )
    )
    fake = FakeSolver({"status": "Trained", "negative_label": "no", "positive_label": "yes"})

    solution = TrainClassificationUseCase(fake).execute(model)

    assert solution.status is ClassificationStatus.TRAINED
    assert fake.last_problem["feature_names"] == ["x"]
    assert fake.last_problem["target_values"] == ["no", "no", "no", "yes", "yes", "yes"]
    assert fake.last_problem["method"] == "LogisticRegression"
