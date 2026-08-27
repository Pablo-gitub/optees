"""Localized, user-facing diagnostics for errors raised by domain services.

Parsers and solver adapters deliberately expose precise English ``ValueError``
messages for tests and API callers. A desktop user should instead receive a
stable explanation in the selected application language; raw parser, operating
system, or third-party solver text is not a reliable localized UI contract.
"""
from __future__ import annotations

from optees.core.string_manager import strings as S


def localized_error_detail(scope: str, error: Exception | str) -> str:
    """Return a localized recovery hint for a presentation error scope."""
    detail = str(error).casefold()

    if scope == "assistant_import":
        return S.t("error_feedback.assistant.generated_model")

    if scope.endswith("_import"):
        return S.t(
            "error_feedback.import.read"
            if _looks_like_file_error(detail)
            else "error_feedback.import.schema"
        )

    if scope == "nlp_validation":
        if _contains(detail, "expression", "function", "variable", "identifier"):
            return S.t("error_feedback.nlp.expression")
        if _contains(detail, "bound", "initial"):
            return S.t("error_feedback.nlp.bounds")
        return S.t("error_feedback.nlp.model")

    if scope.endswith("_export"):
        return S.t("error_feedback.export.write")

    if scope == "qp_validation":
        if _contains(detail, "semi-definite", "concave", "convex", "eigenvalue"):
            return S.t("error_feedback.qp.curvature")
        if _contains(detail, "quadratic matrix", "asymmetric", "symmetr"):
            return S.t("error_feedback.qp.matrix")
        if _contains(detail, "bound"):
            return S.t("error_feedback.qp.bounds")
        if _contains(detail, "constraint"):
            return S.t("error_feedback.qp.constraints")
        if _contains(detail, "tolerance", "iterations", "time_limit", "time limit", "method"):
            return S.t("error_feedback.qp.options")
        return S.t("error_feedback.qp.model")

    if scope == "regression_validation":
        if _contains(detail, "test_fraction", "ridge_alpha", "seed", "method"):
            return S.t("error_feedback.regression.options")
        return S.t("error_feedback.regression.dataset")

    if scope == "classification_validation":
        if _contains(
            detail,
            "test_fraction",
            "seed",
            "learning_rate",
            "max_iterations",
            "l2_alpha",
        ):
            return S.t("error_feedback.classification.options")
        return S.t("error_feedback.classification.dataset")

    if scope == "forecasting_validation":
        if _contains(detail, "two complete seasons", "season length"):
            return S.t("error_feedback.forecasting.seasons")
        if _contains(detail, "holdout leaves insufficient"):
            return S.t("error_feedback.forecasting.holdout")
        if _contains(detail, "rolling-origin"):
            return S.t("error_feedback.forecasting.rolling")
        if _contains(detail, "timestamp", "missing or off-frequency"):
            return S.t("error_feedback.forecasting.timestamps")
        if _contains(detail, "horizon", "iterations", "tolerance"):
            return S.t("error_feedback.forecasting.options")
        return S.t("error_feedback.forecasting.series")

    if scope == "graph_validation":
        if _contains(detail, "weight", "peso"):
            return S.t("error_feedback.graph.weights")
        if _contains(detail, "solver is not configured"):
            return S.t("error_feedback.graph.solver")
        return S.t("error_feedback.graph.topology")

    if scope == "packing_validation":
        if _contains(detail, "rotation", "orientation"):
            return S.t("error_feedback.packing.rotations")
        if _contains(detail, "resource", "capacity", "consumption"):
            return S.t("error_feedback.packing.resources")
        return S.t("error_feedback.packing.model")

    if scope == "update":
        return S.t(
            "error_feedback.update.download"
            if _contains(detail, "asset", "installer", "download", "open update")
            else "error_feedback.update.check"
        )

    return S.t("error_feedback.generic")


def _looks_like_file_error(detail: str) -> bool:
    return _contains(
        detail,
        "cannot read",
        "could not read",
        "invalid json",
        "jsondecode",
        "permission",
        "no such file",
        "is a directory",
    )


def _contains(detail: str, *markers: str) -> bool:
    return any(marker in detail for marker in markers)
