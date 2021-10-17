import ctypes
import os
from sys import argv, exit
from logging import basicConfig, INFO

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from AutomatorGUI.gui.main import MainWindow


def main():
    basicConfig(
        level=INFO,
        format='[%(asctime)s] [%(name)s/%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    app = QApplication(argv)
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), '24hs.png')))
    app_id = '24hs.automator'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    window = MainWindow()
    window.show()
    exit(app.exec())


if __name__ == '__main__':
    main()
