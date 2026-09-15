from __future__ import annotations

from optees import main


def test_desktop_entrypoint_reports_missing_optional_extra(monkeypatch, capsys):
    monkeypatch.setattr(main.importlib.util, "find_spec", lambda name: None)

    assert main.main([]) == 2
    assert capsys.readouterr().err == (
        "The optional desktop dependency is missing. Install optees[desktop].\n"
    )
