from __future__ import annotations

from optees.domain.entities.update import AppRelease
from optees.main import main


def test_update_probe_uses_github_provider_without_starting_qt(monkeypatch, capsys):
    def fake_latest_release(_self):
        return AppRelease(
            tag_name="v0.9.0",
            version="0.9.0",
            html_url="https://example.test/release",
        )

    monkeypatch.setattr(
        "optees.data.adapters.github.update_provider_adapter."
        "GitHubUpdateProvider.get_latest_release",
        fake_latest_release,
    )

    assert main(["--update-probe"]) == 0
    assert capsys.readouterr().out.strip() == "GitHub update endpoint reachable: v0.9.0"
