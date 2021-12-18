from logging import getLogger

from PyQt6.QtWidgets import QMessageBox, QWidget
from packaging import version
from requests import get
from webbrowser import open

from Automator import __version__


def run_update_check(parent: QWidget):
    logger = getLogger('UpdateCheck')
    latest_release_data = get(
        'https://api.github.com/repos/24HourSupport/Automator/releases/latest'
    ).json()
    latest_version = latest_release_data['tag_name']
    logger.debug(f'Latest version is {latest_version}')
    if version.parse(latest_version) <= version.parse(__version__):
        logger.info('No updates found')
        return
    logger.warning('We\'re not up to date, displaying update dialog')
    update_msg = QMessageBox(
        QMessageBox.Icon.Warning,
        'Update available',
        'An updated version of the Automator was found\n'
        'The download link will now be opened',
        QMessageBox.StandardButton.Ok,
        parent
    )
    update_msg.exec()
    open(
        'https://github.com/24HourSupport/Automator/releases/latest/download/24HS-Automator.exe',
        2
    )
    exit(0)
