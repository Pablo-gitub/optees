from __future__ import annotations

import pytest

from optees import mcp_entrypoint


def test_missing_mcp_extra_returns_bounded_installation_hint(monkeypatch, capsys):
    monkeypatch.setattr(mcp_entrypoint.importlib.util, "find_spec", lambda name: None)

    with pytest.raises(SystemExit) as raised:
        mcp_entrypoint.main()

    assert raised.value.code == 2
    assert capsys.readouterr().err == (
        "The optional MCP dependency is missing. Install optees[mcp].\n"
    )
