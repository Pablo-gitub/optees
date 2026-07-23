from __future__ import annotations

import pytest

from optees.application.services.categorical_presentation import (
    bounded_categories,
)


def test_category_window_is_deterministic_and_reports_truncation():
    visible, window = bounded_categories(list(range(100)))

    assert visible == list(range(40))
    assert window.total == 100
    assert window.displayed == 40
    assert window.truncated is True


def test_category_window_preserves_small_results_and_rejects_unsafe_limits():
    visible, window = bounded_categories(["a", "b"], limit=10)

    assert visible == ["a", "b"]
    assert window.truncated is False
    with pytest.raises(ValueError, match="between 1 and 200"):
        bounded_categories(["a"], limit=201)
