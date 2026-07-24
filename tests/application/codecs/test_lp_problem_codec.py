from __future__ import annotations

import pytest

from optees.application.codecs.lp_problem_codec import lp_model_from_public_dict


def test_lp_problem_codec_decodes_versioned_public_payload() -> None:
    model = lp_model_from_public_dict(
        {
            "version": "1",
            "variables": [{"name": "x", "lb": 0, "ub": 4}],
            "objective": {
                "sense": "max",
                "coefficients": [3],
                "offset": 0,
            },
            "constraints": [],
        }
    )

    assert model.variables[0].name == "x"
    assert model.objective.coefs == (3.0,)


def test_lp_problem_codec_reports_missing_public_fields() -> None:
    with pytest.raises(
        ValueError,
        match=r"lp\.continuous is missing required fields: objective, constraints",
    ):
        lp_model_from_public_dict(
            {
                "version": "1",
                "variables": [{"name": "x", "lb": 0, "ub": None}],
            }
        )
