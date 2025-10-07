# src/optees/main.py
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from optees.core.theme import is_dark_mode
from optees.core.assets import asset
from optees.presentation.main_window import MainWindow
import sys

def main():
    app = QApplication(sys.argv)
    variant = "dark" if is_dark_mode() else "light"
    app.setWindowIcon(QIcon(str(asset(f"logo/{variant}/appicon_256.png"))))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
