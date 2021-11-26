import logging
import subprocess
import wmi
import os
import time

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPaintEvent, QCloseEvent
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QGroupBox, QHBoxLayout, QTextEdit, QProgressBar, \
    QMessageBox, QAbstractButton
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from Automator.misc.cmd import silent_run_as_admin


class RestartDialog(QMessageBox):
    """
    Displays a "Restart required" dialog with the options to restart now / later
    """
    def __init__(self, text: str = 'A restart is required to complete the scans', title_text: str = 'Restart required'):
        super(RestartDialog, self).__init__(
            QMessageBox.Icon.Information,
            title_text,
            text
        )
        self.addButton('Restart now', QMessageBox.ButtonRole.AcceptRole)
        self.addButton('Restart later', QMessageBox.ButtonRole.RejectRole)
        self.buttonClicked.connect(self.on_restart)

    def on_restart(self, button: QAbstractButton):
        if self.buttonRole(button) == QMessageBox.ButtonRole.AcceptRole:
            subprocess.Popen(['shutdown', '/r', '/t', '0'])


class ProcessWatcher(QObject):
    """
    Spawns a process as admin and sends signals if new stdout/stderr data is available or the process is closed
    """
    processFinished = pyqtSignal()
    newData = pyqtSignal(str)

    def __init__(self, process: str, encoding: str, skip_last_line: bool = True, *args, **kwargs):
        super(ProcessWatcher, self).__init__(*args, **kwargs)
        self.process = process
        self.encoding = encoding
        self.skip_last_line = skip_last_line
        self.lines_to_skip = 0
        process_name = process.split(' ')[0]
        # This is only used to check if the process is still running, so it's easier to append the '.exe' here
        self.process_name = process_name + '.exe'
        self.cmd_proc = None
        self.logger = logging.getLogger('ProcessWatcher ' + self.process_name)
        self.filename = process_name + str(round(time.time())) + '.log'
        self.observer = Observer()

    def _setup_events(self) -> PatternMatchingEventHandler:
        self.logger.debug('Setting up events...')
        self.logger.debug('File name is {}'.format(self.filename))
        event_handler = PatternMatchingEventHandler(patterns=[self.filename])
        self.observer = Observer()
        self.observer.schedule(event_handler, os.path.expandvars('%TEMP%'), recursive=False)
        event_handler.on_modified = lambda e: self._file_modified()
        return event_handler

    def _file_modified(self):
        log_file = os.path.join(os.path.expandvars('%TEMP%'), self.filename)
        with open(log_file, encoding=self.encoding) as f:
            lines = f.readlines()
        if self.skip_last_line:
            lines.pop(-1)
        self.logger.debug('File was modified. Got {} new lines'.format(len(lines[self.lines_to_skip:])))
        for line in lines[self.lines_to_skip:]:
            line = line.replace('\n', '')
            if line:
                # noinspection PyUnresolvedReferences
                self.newData.emit(line)
        self.lines_to_skip = len(lines)
        potential_sfc_proc = wmi.WMI().Win32_Process(name=self.process_name)
        if not potential_sfc_proc:
            self._finish()

    def _finish(self):
        self.observer.stop()
        self.observer = None
        log_file = os.path.join(os.path.expandvars('%TEMP%'), self.filename)
        os.remove(log_file)
        self.cmd_proc.terminate()
        os.remove(log_file[:-4] + '.bat')
        # noinspection PyUnresolvedReferences
        self.processFinished.emit()

    def start(self):
        self.logger.debug('Starting process...')
        self._setup_events()
        # Display the UAC prompt
        log_file = os.path.join(os.path.expandvars('%TEMP%'), self.filename)
        proc_or_false = silent_run_as_admin(self.process + ' 1>{} 2>&1'.format(log_file))
        if not proc_or_false:
            raise RuntimeError('User has not accepted the UAC prompt')
        # Wait for the program to start
        while True:
            try:
                wmi.WMI().Win32_Process(name=self.process_name)
            # AttributeError is normal if the process doesn't exist yet
            except AttributeError:
                pass
            else:
                break
        self.observer.start()
        # For... reasons, Windows doesn't check if a file has changed unless it's actually read out.
        # So here we construct a small batch file to read out the file continuously
        bat_name = self.filename[:-4] + '.bat'
        with open(os.path.join(os.path.expandvars('%TEMP%'), bat_name), 'w') as f:
            f.write('''
            @echo off\n
            :start\n
            timeout /nobreak /t 2 >nul\n
            type "{}" 1>nul 2>&1\n
            goto start\n
            '''.format(log_file))
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        self.cmd_proc = subprocess.Popen(
            ['cmd', '/c', os.path.join(os.path.expandvars('%TEMP%'), bat_name)],
            startupinfo=startupinfo
        )

    def cancel(self):
        potential_sfc_proc = wmi.WMI().Win32_Process(name=self.process_name)
        if not potential_sfc_proc:
            raise RuntimeError('Process could not be found')
        # Once we end the process, the file will be written to one last time. This will then run _file_modified(),
        # which in turn will then run _finished (again), and that will then fail because the process isn't running
        # anymore. With this, we don't get the last bit of % / messages, but I doubt that's gonna matter when the user
        # cancels it anyways
        self.observer.unschedule_all()
        # Send the terminate signal to the process
        # FIXME: This will target the first process that is found. With something like SFC this is fine, but if we
        #        only run CMD for example, we will end other processes not "belonging" to us
        potential_sfc_proc[0].Terminate()
        # Wait for it to close
        while True:
            potential_sfc_proc = wmi.WMI().Win32_Process(name=self.process_name)
            if not potential_sfc_proc:
                break
        self._finish()

    def has_finished(self) -> bool:
        return not wmi.WMI().Win32_Process(name=self.process_name)


class RescueCommandsWindow(QDialog):
    def __init__(self, *args, **kwargs):
        super(RescueCommandsWindow, self).__init__(*args, **kwargs)
        self.layout = QVBoxLayout()

        self.logger = logging.getLogger('Rescuecommands')
        self.sfc_watcher: ProcessWatcher
        self.dism_watcher: ProcessWatcher

        group_box = QGroupBox(self)
        self.button_layout = QHBoxLayout()
        button_data = [
            ('Start SFC scan', self.sfc_start),
            ('Start DISM scan', self.dism_start),
            ('Start CHKDSK scan', self.chkdsk_start)
        ]
        for button_text, callback in button_data:
            button = QPushButton(button_text, self)
            button.setMaximumWidth(150)
            button.setAutoDefault(False)
            if callback:
                button.clicked.connect(callback)
            self.button_layout.addWidget(button)
        group_box.setLayout(self.button_layout)
        self.layout.addWidget(group_box)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar_value = 0
        # Start with a value of 0 since the empty space looks weird otherwise
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        self.text_area = QTextEdit(self)
        self.text_area.setPlaceholderText('Click a button to start testing')
        self.text_area.setReadOnly(True)
        self.layout.addWidget(self.text_area)

        self.setWindowTitle('SFC / DISM / CHKDSK scans')
        self.setMinimumSize(500, 300)
        self.setLayout(self.layout)

    def paintEvent(self, a0: QPaintEvent) -> None:
        self.progress_bar.setValue(self.progress_bar_value)

    def closeEvent(self, a0: QCloseEvent) -> None:
        if hasattr(self, 'sfc_watcher'):
            if not self.sfc_watcher.has_finished():
                self.sfc_watcher.cancel()
        if hasattr(self, 'dism_watcher'):
            if not self.dism_watcher.has_finished():
                self.dism_watcher.cancel()

    def _for_each_button(self, enable=False, ignore_button=-1, ignore_button_text=None, click_connect=None):
        for i in range(self.button_layout.count()):
            button_widget = self.button_layout.itemAt(i).widget()
            # In case any function has to do special things with the buttons
            if i == ignore_button:
                if click_connect:
                    button_widget.disconnect()
                    button_widget.clicked.connect(click_connect)
                # If a text was supplied, set the buttons text to that
                if ignore_button_text:
                    button_widget.setText(ignore_button_text)
            else:
                button_widget.setEnabled(enable)

    def _setup_scan(self, scan_name: str):
        self.progress_bar_value = 0
        self.text_area.clear()
        self.text_area.append('Starting {} scan...\n'.format(scan_name))
        self.logger.info('Starting {} scan'.format(scan_name))

    def _cancel_scan(self, scan_name: str):
        self.text_area.append('{} scan cancelled'.format(scan_name))
        self.logger.info('{} scan cancelled'.format(scan_name))

    def _check_scan(self, scan_name: str):
        if self.progress_bar_value != self.progress_bar.maximum():
            self.logger.warning('{} scan did not finish successfully!'.format(scan_name))
            self.text_area.append('{} scan did not finish successfully!'.format(scan_name))
        else:
            self.logger.info('{} scan finished'.format(scan_name))
            self.text_area.append('\n{} scan finished'.format(scan_name))

    def sfc_start(self):
        self._setup_scan('SFC')

        # noinspection PyAttributeOutsideInit
        self.sfc_watcher = ProcessWatcher('sfc /scannow', 'utf_16_le')
        # noinspection PyUnresolvedReferences
        self.sfc_watcher.processFinished.connect(self.sfc_done)
        # noinspection PyUnresolvedReferences
        self.sfc_watcher.newData.connect(self.sfc_update)
        try:
            self.sfc_watcher.start()
        except RuntimeError:
            self.logger.info('SFC scan aborted')
            return

        self._for_each_button(
            ignore_button=0, ignore_button_text='Cancel SFC scan', click_connect=self.sfc_cancel
        )

    def sfc_cancel(self):
        self.sfc_watcher.cancel()
        self._cancel_scan('SFC')

    def sfc_update(self, line: str):
        # If the line has a % in it, update the progress bar and don't display it in the main log
        percent_index = line.find('%')
        if percent_index != -1:
            percent_part = next(x for x in line.split(' ') if '%' in x)
            percent = int(percent_part.replace('%', ''))
            if percent > self.progress_bar_value:
                self.progress_bar_value = percent
        else:
            self.text_area.append(line)

        self.update()

    def sfc_done(self):
        self._for_each_button(
            enable=True, ignore_button=0, ignore_button_text='Start SFC scan', click_connect=self.sfc_start
        )
        self._check_scan('SFC')

    def dism_start(self):
        self._setup_scan('DISM')
        # noinspection PyAttributeOutsideInit
        self.dism_watcher = ProcessWatcher('DISM /Online /Cleanup-Image /RestoreHealth', 'utf_8')
        # noinspection PyUnresolvedReferences
        self.dism_watcher.processFinished.connect(self.dism_done)
        # noinspection PyUnresolvedReferences
        self.dism_watcher.newData.connect(self.dism_update)
        try:
            self.dism_watcher.start()
        except RuntimeError:
            self.logger.info('DISM scan aborted')
            return

        self._for_each_button(
            ignore_button=1, ignore_button_text='Cancel DISM scan', click_connect=self.dism_cancel
        )

    def dism_cancel(self):
        self.dism_watcher.cancel()
        self._cancel_scan('DISM')

    def dism_update(self, line: str):
        percent_index = line.find('%')
        if percent_index != -1:
            percent = line[percent_index-5:percent_index-2]
            percent = percent.replace('=', '').replace(' ', '')
            percent = int(percent)
            if percent > self.progress_bar_value:
                self.progress_bar_value = percent
        else:
            self.text_area.append(line)

        self.update()

    def dism_done(self):
        self._for_each_button(
            enable=True, ignore_button=1, ignore_button_text='Start DISM scan', click_connect=self.dism_start
        )

        self._check_scan('DISM')

    def chkdsk_start(self):
        self._setup_scan('CHKDSK')

        with open(os.path.join(os.path.expandvars('%TEMP%'), 'chkdsk_temp.bat'), 'w') as f:
            f.write("""
            @echo off\n
            cd "%TEMP%"\n
            chkdsk C: /r /x < chkdsk_y.txt\n
            echo 1 >done.txt
            """)

        with open(os.path.join(os.path.expandvars('%TEMP%'), 'chkdsk_y.txt'), 'w') as f:
            f.write('Y\n')

        if os.path.exists(os.path.join(os.path.expandvars('%TEMP%'), 'done.txt')):
            os.remove(os.path.join(os.path.expandvars('%TEMP%'), 'done.txt'))

        # noinspection PyAttributeOutsideInit
        self.chkdsk_watcher = ProcessWatcher(
            'cmd /c %TEMP%\\chkdsk_temp.bat', 'utf-8', skip_last_line=False
        )
        # noinspection PyUnresolvedReferences
        self.chkdsk_watcher.processFinished.connect(self.chkdsk_done)
        # noinspection PyUnresolvedReferences
        self.chkdsk_watcher.newData.connect(self.text_area.append)
        self.chkdsk_watcher.start()

        self._for_each_button()

        while True:
            if os.path.exists(os.path.join(os.path.expandvars('%TEMP%'), 'done.txt')):
                break
        time.sleep(0.5)
        # noinspection PyProtectedMember
        self.chkdsk_watcher._finish()

    def chkdsk_done(self):
        self.logger.info('CHKDSK scan done')

        # Remove all temporary files created
        temp_path = os.path.expandvars('%TEMP%')
        for filename in ['chkdsk_temp.bat', 'chkdsk_y.txt', 'done.txt']:
            os.remove(os.path.join(temp_path, filename))

        # Re-enable buttons
        self._for_each_button(enable=True)

        RestartDialog('To run the CHKDSK scan, you will have to restart your computer').exec()
