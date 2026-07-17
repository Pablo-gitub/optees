# src/optees/main.py
import sys
import logging
import os


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "--local-server":
        from optees.local_server import main as server_main

        return server_main(arguments[1:])

    logging.basicConfig(level=os.getenv("OPTEES_LOG", "WARNING").upper())
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from optees.core.assets import asset
    from optees.core.theme import is_dark_mode, theme
    from optees.presentation.main_window import MainWindow

    app = QApplication([sys.argv[0], *arguments])
    theme.install_global_theme(app)
    variant = "dark" if is_dark_mode() else "light"
    app.setWindowIcon(QIcon(str(asset(f"logo/{variant}/appicon_256.png"))))
    win = MainWindow()
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
