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

    if scope == "regression_validation":
        if _contains(detail, "test_fraction", "ridge_alpha", "seed", "method"):
            return S.t("error_feedback.regression.options")
        return S.t("error_feedback.regression.dataset")

    if scope == "graph_validation":
        if _contains(detail, "weight", "peso"):
            return S.t("error_feedback.graph.weights")
        if _contains(detail, "solver is not configured"):
            return S.t("error_feedback.graph.solver")
        return S.t("error_feedback.graph.topology")

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
