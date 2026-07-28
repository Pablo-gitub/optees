from __future__ import annotations

from optees.domain.entities.update import AppRelease
from optees.main import main


def test_update_probe_uses_ci_token_without_starting_qt(monkeypatch, capsys):
    captured = {}

    def fake_init(self, **kwargs):
        captured.update(kwargs)

    def fake_latest_release(_self):
        return AppRelease(
            tag_name="v0.9.0",
            version="0.9.0",
            html_url="https://example.test/release",
        )

    monkeypatch.setenv("GITHUB_TOKEN", "release-probe-token")
    monkeypatch.setattr(
        "optees.data.adapters.github.update_provider_adapter."
        "GitHubUpdateProvider.__init__",
        fake_init,
    )
    monkeypatch.setattr(
        "optees.data.adapters.github.update_provider_adapter."
        "GitHubUpdateProvider.get_latest_release",
        fake_latest_release,
    )

    assert main(["--update-probe"]) == 0
    assert captured == {"api_token": "release-probe-token"}
    assert capsys.readouterr().out.strip() == "GitHub update endpoint reachable: v0.9.0"
