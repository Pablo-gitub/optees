"""Visualization coverage for the scenario comparison chart.

The widget must render what the application returned and nothing else, so these
tests feed it result payloads verbatim and assert that ordering, ties, negative
values and no-candidate states survive untouched.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from optees.core.string_manager import strings as S
from optees.presentation.views.scenario_comparison_widget import (
    BINDING_MARKER,
    ScenarioComparisonWidget,
    binding_ids,
)


def _result(orientation, guaranteed, values):
    return {
        "orientation": orientation,
        "guaranteed_value": guaranteed,
        "variables": [{"name": "x1", "value": 1.0}],
        "scenario_values": [
            {"scenario_id": sid, "value": value, "is_binding": binding}
            for sid, value, binding in values
        ],
        "binding_scenario_ids": [sid for sid, _v, binding in values if binding],
    }


@pytest.fixture
def widget(qtbot):
    view = ScenarioComparisonWidget()
    qtbot.addWidget(view)
    return view


def test_empty_widget_reports_no_candidate(widget) -> None:
    assert widget.visualization_state == "no_candidate"
    assert widget.status_label.text() == S.t("scenario.solution.comparison.no_candidate")


def test_no_candidate_result_is_named_not_drawn_as_zero(widget) -> None:
    widget.set_result(
        {
            "orientation": "minimize_maximum_loss",
            "guaranteed_value": None,
            "variables": [],
            "scenario_values": [],
            "binding_scenario_ids": [],
        }
    )

    assert widget.visualization_state == "no_candidate"
    assert widget.plotted_scenario_ids == ()
    assert widget.status_label.text() == S.t("scenario.solution.comparison.no_candidate")


@pytest.mark.parametrize("invalid_value", ["not-a-number", float("nan"), float("inf"), True])
def test_invalid_scenario_value_is_not_fabricated_as_zero(widget, invalid_value) -> None:
    widget.set_result(
        _result(
            "minimize_maximum_loss",
            1.0,
            [("s1", invalid_value, True)],
        )
    )

    assert widget.visualization_state == "invalid_result"
    assert widget.status_label.text() == S.t("scenario.solution.comparison.invalid_result")


def test_non_boolean_binding_flag_is_not_interpreted(widget) -> None:
    result = _result("minimize_maximum_loss", 1.0, [("s1", 1.0, True)])
    result["scenario_values"][0]["is_binding"] = "false"
    widget.set_result(result)

    assert widget.visualization_state == "invalid_result"


def test_declared_scenario_order_is_preserved(widget) -> None:
    widget.set_result(
        _result(
            "minimize_maximum_loss",
            10.857142857142858,
            [
                ("s1", 10.857142857142858, True),
                ("s2", 10.857142857142858, True),
                ("s3", 6.0, False),
            ],
        )
    )

    assert widget.visualization_state == "ready"
    assert widget.plotted_scenario_ids == ("s1", "s2", "s3")


def test_multiple_binding_ties_are_all_marked(widget) -> None:
    widget.set_result(
        _result(
            "minimize_maximum_loss",
            10.857142857142858,
            [
                ("s1", 10.857142857142858, True),
                ("s2", 10.857142857142858, True),
                ("s3", 6.0, False),
            ],
        )
    )
    axis = widget._figure.axes[0]
    labels = [label.get_text() for label in axis.get_yticklabels()]

    # Tick labels follow declared order; the reversed positions place s1 on top.
    assert labels == [f"{BINDING_MARKER} s1", f"{BINDING_MARKER} s2", "s3"]
    assert list(axis.get_yticks()) == [2, 1, 0]
    assert sum(1 for label in labels if BINDING_MARKER in label) == 2


def test_binding_is_distinguishable_without_colour(widget) -> None:
    widget.set_result(
        _result(
            "minimize_maximum_loss",
            5.0,
            [("s1", 5.0, True), ("s2", 1.0, False)],
        )
    )
    axis = widget._figure.axes[0]
    hatches = [patch.get_hatch() for patch in axis.patches]
    widths = [patch.get_linewidth() for patch in axis.patches]

    # Exactly one bar carries a hatch and the heavier outline.
    assert sum(1 for hatch in hatches if hatch) == 1
    assert max(widths) > min(widths)
    assert BINDING_MARKER in widget.status_label.text()


def test_negative_values_and_a_negative_guarantee_are_kept(widget) -> None:
    widget.set_result(
        _result(
            "maximize_minimum_reward",
            -22 / 13,
            [("sA", -22 / 13, True), ("sB", -22 / 13, True), ("sC", 1.0, False)],
        )
    )
    axis = widget._figure.axes[0]

    assert widget.visualization_state == "ready"
    assert widget.plotted_scenario_ids == ("sA", "sB", "sC")
    # The window spans the negative values and the positive one.
    assert axis.get_xlim()[0] < -1.6
    assert axis.get_xlim()[1] > 1.0
    assert axis.get_xlabel() == S.t("scenario.solution.comparison.axis.reward")


def test_orientation_selects_its_own_axis_label(widget) -> None:
    widget.set_result(_result("minimize_maximum_loss", 3.0, [("s1", 3.0, True)]))
    assert widget._figure.axes[0].get_xlabel() == S.t("scenario.solution.comparison.axis.loss")

    widget.set_result(_result("maximize_minimum_reward", 3.0, [("s1", 3.0, True)]))
    assert widget._figure.axes[0].get_xlabel() == S.t("scenario.solution.comparison.axis.reward")


def test_accessible_description_names_the_binding_scenarios(widget) -> None:
    widget.set_result(
        _result("minimize_maximum_loss", 5.0, [("s1", 5.0, True), ("s2", 1.0, False)])
    )

    description = widget.accessibleDescription()
    assert "s1" in description
    assert description == S.t(
        "scenario.solution.comparison.accessible_description",
        count=2,
        guarantee="5",
        binding="s1",
    )


def test_theme_and_resize_refresh_do_not_change_the_data(widget, qtbot) -> None:
    payload = _result(
        "minimize_maximum_loss",
        10.857142857142858,
        [("s1", 10.857142857142858, True), ("s2", 6.0, False)],
    )
    widget.set_result(payload)
    before = widget.plotted_scenario_ids

    widget.refresh_theme()
    widget.resize(420, 260)
    qtbot.wait(20)
    widget.refresh_strings()

    assert widget.visualization_state == "ready"
    assert widget.plotted_scenario_ids == before
    # The rendered payload is still exactly what was handed in.
    assert widget._guaranteed_value == pytest.approx(10.857142857142858)


@pytest.mark.parametrize("language", ["en", "it"])
def test_widget_text_follows_the_selected_language(widget, language: str) -> None:
    previous = S.current_language()
    try:
        S.set_language(language)
        widget.set_result(None)
        assert widget.status_label.text() == S.t("scenario.solution.comparison.no_candidate")
        assert "scenario." not in widget.status_label.text()
    finally:
        S.set_language(previous)


def test_binding_helper_reports_published_ids_in_order() -> None:
    values = [
        {"scenario_id": "s1", "value": 1.0, "is_binding": True},
        {"scenario_id": "s2", "value": 0.0, "is_binding": False},
        {"scenario_id": "s3", "value": 1.0, "is_binding": True},
    ]

    assert binding_ids(values) == ("s1", "s3")
