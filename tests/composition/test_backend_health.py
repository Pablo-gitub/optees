from __future__ import annotations

from types import SimpleNamespace

from optees.composition import backend_health


def test_import_probe_requires_real_import_and_declared_attributes(monkeypatch):
    monkeypatch.setattr(
        backend_health,
        "import_module",
        lambda _name: SimpleNamespace(required=True),
    )

    assert backend_health.import_is_usable("example", "required") is True
    assert backend_health.import_is_usable("example", "missing") is False


def test_import_probe_reports_import_failure_as_unavailable(monkeypatch):
    def fail(_name):
        raise ImportError("compiled extension is missing")

    monkeypatch.setattr(backend_health, "import_module", fail)

    assert backend_health.import_is_usable("example") is False


def test_highs_probe_executes_a_trivial_problem(monkeypatch):
    calls: list[dict[str, object]] = []

    def linprog(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return SimpleNamespace(success=True, status=0)

    monkeypatch.setattr(
        backend_health,
        "import_module",
        lambda _name: SimpleNamespace(linprog=linprog),
    )

    assert backend_health.scipy_highs_is_usable() is True
    assert calls[0]["kwargs"]["method"] == "highs"


def test_highs_probe_rejects_a_backend_that_imports_but_cannot_solve(monkeypatch):
    def linprog(*_args, **_kwargs):
        raise ImportError("HiGHS runtime module is missing")

    monkeypatch.setattr(
        backend_health,
        "import_module",
        lambda _name: SimpleNamespace(linprog=linprog),
    )

    assert backend_health.scipy_highs_is_usable() is False
