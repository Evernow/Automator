import logging
from subprocess import list2cmdline
from typing import Union

from win32con import SW_SHOWNORMAL
# noinspection PyUnresolvedReferences
from win32com.shell.shell import ShellExecuteEx
# noinspection PyUnresolvedReferences
from win32com.shell.shellcon import SEE_MASK_NOCLOSEPROCESS


def silent_run_as_admin(command: str) -> Union[dict, bool]:
    logger = logging.getLogger('UACHelper')
    params = list2cmdline([
        '/c', 'start', '/min', 'cmd', '/c', command
    ])
    logger.debug('Trying to run command as admin: \'cmd {}\''.format(params))
    # noinspection PyBroadException
    try:
        admin_proc = ShellExecuteEx(
            nShow=SW_SHOWNORMAL,
            fMask=SEE_MASK_NOCLOSEPROCESS,
            lpVerb='runas',
            lpFile='cmd',
            lpParameters=params
        )
    except BaseException:
        logger.error('UAC prompt was not accepted')
        return False
    logger.debug('Command started successfully')
    return admin_proc
