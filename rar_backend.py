"""Optional writer adapter for the user's installed RAR console encoder."""
import os
from pathlib import Path
import subprocess
import tempfile


def rar_encoder():
    configured = os.environ.get('WINCIP_RAR')
    candidates = [Path(configured)] if configured else []
    for variable in ('ProgramFiles', 'ProgramFiles(x86)'):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / 'WinRAR' / 'Rar.exe')
    if os.name == 'nt':
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths\WinRAR.exe') as key:
                    candidates.append(Path(winreg.QueryValueEx(key, '')[0]).parent / 'Rar.exe')
            except OSError:
                pass
    return next((path.absolute() for path in candidates if path.is_file()), None)


def create_rar(content, destination, level, cancel, progress, *, password=None, hide_names=True, volume_mb=0):
    from archive_core import ArchiveError, checkpoint
    encoder = rar_encoder()
    if encoder is None:
        raise ArchiveError('Para crear o modificar RAR necesitas Rar.exe de una instalación de WinRAR. ZIP, 7Z y TAR funcionan con el motor incluido.')
    content, destination = Path(content), Path(destination)
    listing = destination.parent / 'rar-input.txt'
    listing.write_text('\n'.join('.\\' + path.name for path in content.iterdir()), encoding='utf-8')
    args = [str(encoder), 'a', '-cfg-', '-idq', '-scfl', '-r', '-y',
            '-m' + str({0: 0, 1: 1, 6: 3, 9: 5}[level])]
    if password:
        args.append(('-hp' if hide_names else '-p') + password)
    if volume_mb:
        args.append('-v' + str(volume_mb) + 'm')
    args += ['--', str(destination), '@' + str(listing)]
    progress(0, 0, 'Comprimiendo con el codificador RAR instalado…')
    checkpoint(cancel)
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(args, cwd=content, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while True:
                checkpoint(cancel)
                try:
                    process.wait(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    pass
            if process.returncode:
                raise ArchiveError('El codificador RAR no pudo completar la operación (código ' + str(process.returncode) + '). El original se ha conservado.')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    listing.unlink()
