"""PTY adapters; imports of platform-specific packages stay lazy."""
import os
from pathlib import Path
import platform
import select
import shutil

from django.conf import settings


def configuration():
    windows = platform.system() == 'Windows'
    executable = settings.TERMINAL_SHELL or (
        (shutil.which('pwsh') or shutil.which('powershell.exe') or os.environ.get('COMSPEC', 'cmd.exe'))
        if windows else (shutil.which('bash') or '/bin/sh')
    )
    shell = Path(executable).stem.lower()
    args = (['-NoLogo', '-NoProfile', '-NoExit', '-Command',
             'if (Get-Module -ListAvailable PSReadLine) { Import-Module PSReadLine; Set-PSReadLineOption -HistorySaveStyle SaveNothing }']
            if shell in ('powershell', 'pwsh') else ([] if windows else ['-i']))
    cwd = Path(settings.TERMINAL_WORKDIR).resolve()
    if not cwd.is_dir():
        raise ValueError('终端初始目录不存在，请联系管理员检查配置。')
    return {'platform': platform.system(), 'shell': executable, 'cwd': str(cwd), 'args': args}


class Console:
    def __init__(self, rows=24, cols=80):
        config = configuration()
        env = dict(os.environ, TERM='xterm-256color', HISTFILE=os.devnull)
        argv = [config['shell'], *config['args']]
        if config['platform'] == 'Windows':
            from winpty import PtyProcess
        else:
            from ptyprocess import PtyProcessUnicode as PtyProcess
        self.process = PtyProcess.spawn(argv, cwd=config['cwd'], env=env, dimensions=(rows, cols))
        self.closed = False

    def read(self):
        if self.closed:
            raise EOFError()
        # Windows pywinpty exposes a socket; POSIX exposes a PTY file descriptor.
        descriptor = getattr(self.process, 'fileobj', None) if os.name == 'nt' else self.process.fd
        if not select.select([descriptor], [], [], 0.2)[0]:
            if not self.process.isalive():
                raise EOFError()
            return ''
        return self.process.read(4096)

    def write(self, data):
        return self.process.write(data)

    def resize(self, rows, cols):
        self.process.setwinsize(rows, cols)

    def close(self):
        if self.closed:
            return
        self.closed = True
        # Reap processes started by this terminal as well as its shell.
        import psutil
        try:
            children = psutil.Process(self.process.pid).children(recursive=True)
        except psutil.Error:
            children = []
        for child in children:
            try:
                child.terminate()
            except psutil.Error:
                pass
        try:
            self.process.close(force=True)
        finally:
            _, alive = psutil.wait_procs(children, timeout=1)
            for child in alive:
                try:
                    child.kill()
                except psutil.Error:
                    pass
