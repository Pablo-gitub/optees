import json
import subprocess
import sys
import textwrap


def test_string_manager_loads_i18n_from_pyinstaller_meipass(tmp_path):
    meipass = tmp_path / "bundle"
    locales = meipass / "assets" / "i18n"
    locales.mkdir(parents=True)
    (locales / "en.json").write_text(
        json.dumps({"app": {"title": "Bundled Optees"}}),
        encoding="utf-8",
    )

    script = textwrap.dedent(
        f"""
        import sys
        sys.frozen = True
        sys._MEIPASS = {str(meipass)!r}
        from optees.core.string_manager import strings
        assert strings.t("app.title") == "Bundled Optees"
        """
    )

    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        cwd=str(tmp_path),
    )
