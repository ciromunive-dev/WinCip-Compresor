"""Register capabilities; Windows' own UI selects protected user defaults."""
import ctypes
from branding import APP_NAME
from ctypes import wintypes
import os
from pathlib import Path
import sys
import winreg
import subprocess

SHELL_CLSID = "{D4E07230-5AF0-4E95-A8A0-80D732CC1791}"

EXTENSIONS = ('.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tbz2', '.txz')
PROGID = 'WinCip.Archive'
LEGACY_PROGID = 'ArchivoFacil.Archive'
FTA_OPEN_IS_SAFE = 0x00010000


def association_status(executable=None):
    """Query the effective Shell handler, including protected user choices."""
    executable = Path(executable or (sys.executable if getattr(sys, 'frozen', False)
                                    else Path(__file__).with_name('WinCip.exe'))).resolve()
    query = ctypes.windll.shlwapi.AssocQueryStringW
    query.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR,
                      wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    query.restype = ctypes.c_long
    status = {}
    for extension in EXTENSIONS:
        length = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(length.value)
        result = query(0, 2, extension, 'open', buffer, ctypes.byref(length))
        target = Path(buffer.value).resolve() if result == 0 and buffer.value else None
        status[extension] = target == executable
    return status


def set_value(path, name, value):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def register_archive_opening(path):
    # The archive open verb only lists content. Register that behavior with the
    # Shell so downloaded archives do not get an executable-style opening prompt.
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
        try:
            flags, kind = winreg.QueryValueEx(key, 'EditFlags')
            if kind == winreg.REG_BINARY:
                flags = int.from_bytes(flags, 'little')
        except FileNotFoundError:
            flags = 0
        winreg.SetValueEx(key, 'EditFlags', 0, winreg.REG_DWORD, int(flags) | FTA_OPEN_IS_SAFE)


def register(executable=None, *, set_fallback_defaults=False):
    executable = Path(executable or (sys.executable if getattr(sys, 'frozen', False) else Path(__file__).with_name('WinCip.exe'))).resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)
    command = f'"{executable}" "%1"'
    classes = r'Software\Classes'
    # Keep the previous IDs as aliases for existing Windows user associations.
    for progid in (PROGID, LEGACY_PROGID):
        base = classes + '\\' + progid
        set_value(base, '', 'Archivo comprimido de ' + APP_NAME)
        set_value(base, 'FriendlyTypeName', 'Archivo comprimido de ' + APP_NAME)
        register_archive_opening(base)
        set_value(base + r'\DefaultIcon', '', f'"{executable}",0')
        set_value(base + r'\shell\open\command', '', command)
    for filename in ('WinCip.exe', 'ArchivoFacil.exe'):
        application = classes + '\\Applications\\' + filename
        set_value(application, 'FriendlyAppName', APP_NAME)
        register_archive_opening(application)
        set_value(application + r'\shell\open\command', '', command)
        for extension in EXTENSIONS:
            set_value(application + r'\SupportedTypes', extension, '')
    capabilities = r'Software\WinCip\Capabilities'
    set_value(capabilities, 'ApplicationName', APP_NAME)
    set_value(capabilities, 'ApplicationDescription', 'Abre y extrae ZIP, RAR, 7Z y TAR. Crea ZIP, 7Z, TAR y TAR.GZ.')
    set_value(capabilities, 'ApplicationIcon', f'"{executable}",0')
    for extension in EXTENSIONS:
        if set_fallback_defaults:
            # Explicit setup only. Do not overwrite protected Windows UserChoice.
            set_value(classes + '\\' + extension, '', PROGID)
        set_value(capabilities + r'\FileAssociations', extension, PROGID)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, classes + '\\' + extension + r'\OpenWithProgids') as key:
            winreg.SetValueEx(key, PROGID, 0, winreg.REG_NONE, b'')
    set_value(r'Software\RegisteredApplications', 'WinCip', capabilities)
    register_context_menu(executable)
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\RegisteredApplications',
                        0, winreg.KEY_SET_VALUE) as key:
        try:
            winreg.DeleteValue(key, 'ArchivoFácil')
        except FileNotFoundError:
            pass
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def delete_owned_key(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                except OSError as exc:
                    if exc.winerror == 259:
                        break
                    raise
                delete_owned_key(path + '\\' + child)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        pass


def register_context_menu(executable):
    classes = r'Software\Classes'
    for scope in ('*', 'Directory'):
        delete_owned_key(classes + '\\' + scope + r'\shell\WinCip.Compress')
    for scope in [classes + '\\' + p for p in (PROGID, LEGACY_PROGID)] + [classes + '\\SystemFileAssociations\\' + ext for ext in EXTENSIONS]:
        for verb in ('Here', 'Folder'):
            delete_owned_key(scope + r'\shell\WinCip.' + verb)
    library = Path(executable).with_name('WinCipShell-3.2.dll')
    if not library.is_file():
        library = Path(executable).with_name('WinCipShell.dll')
    if not library.is_file():
        # A copied EXE can still expose a grouped classic menu without the DLL.
        for scope in ('*', 'Directory'):
            base = classes + '\\' + scope + r'\shell\WinCip'
            delete_owned_key(base)
            set_value(base, 'MUIVerb', APP_NAME)
            set_value(base, 'Icon', f'"{executable}",0')
            set_value(base, 'SubCommands', '')
            for key, title, switch in [('Open','Abrir con ' + APP_NAME,''), ('Extract','Extraer archivos…','--extract'), ('Folder','Extraer en carpeta','--extract-folder'), ('Here','Extraer aquí','--extract-here'), ('Compress','Añadir a un comprimido…','--compress')]:
                child = base + '\\shell\\' + key
                set_value(child, '', title)
                set_value(child + r'\command', '', f'"{executable}" {switch} "%1"')
        return
    server = classes + '\\CLSID\\' + SHELL_CLSID + r'\InprocServer32'
    set_value(server, '', str(library))
    set_value(server, 'ThreadingModel', 'Apartment')
    for scope in ('*', 'Directory'):
        base = classes + '\\' + scope + r'\shell\WinCip'
        delete_owned_key(base)
        set_value(base, 'MUIVerb', APP_NAME)
        set_value(base, 'Icon', f'"{executable}",0')
        set_value(base, 'ExplorerCommandHandler', SHELL_CLSID)


def install_modern_menu(executable=None):
    if sys.getwindowsversion().build < 22000:
        raise RuntimeError('El menú moderno del Explorador requiere Windows 11.')
    executable = Path(executable or Path(__file__).with_name('WinCip.exe')).resolve()
    script = executable.parent / 'shell_extension' / 'Install.ps1'
    if not script.is_file():
        raise FileNotFoundError('Falta shell_extension/Install.ps1 junto a WinCip.exe.')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(script), '-AppDirectory', str(executable.parent)],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace') or 'No se pudo registrar el menú de Windows 11.')


def open_defaults():
    register()
    build = sys.getwindowsversion().build
    windows_11 = build >= 22000
    executable = Path(sys.executable if getattr(sys, 'frozen', False) else Path(__file__).with_name('WinCip.exe'))
    if windows_11 and any(
            executable.with_name(name).is_file() for name in ('WinCipShell-3.2.dll','WinCipShell.dll')):
        try:
            install_modern_menu(executable)
        except (OSError, RuntimeError):
            # Classic integration and file defaults remain available without a package.
            pass
    settings = 'ms-settings:defaultapps?registeredAppUser=WinCip' if windows_11 else 'ms-settings:defaultapps'
    os.startfile(settings)


def unregister(executable):
    """Remove only records that still point at this installation."""
    executable = Path(executable).resolve()
    command = f'"{executable}" "%1"'
    def read(path, name=''):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                return winreg.QueryValueEx(key, name)[0]
        except FileNotFoundError:
            return None
    def remove_value(path, name):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass
    classes = r'Software\Classes'
    owned_progid = read(classes + '\\' + PROGID + r'\shell\open\command') == command
    for progid in (PROGID, LEGACY_PROGID):
        base = classes + '\\' + progid
        if read(base + r'\shell\open\command') == command:
            delete_owned_key(base)
    if owned_progid:
        for extension in EXTENSIONS:
            remove_value(classes + '\\' + extension + r'\OpenWithProgids', PROGID)
            if read(classes + '\\' + extension) == PROGID:
                remove_value(classes + '\\' + extension, '')
    for filename in ('WinCip.exe', 'ArchivoFacil.exe'):
        base = classes + '\\Applications\\' + filename
        if read(base + r'\shell\open\command') == command:
            delete_owned_key(base)
    capabilities = r'Software\WinCip\Capabilities'
    if read(capabilities, 'ApplicationIcon') == f'"{executable}",0':
        delete_owned_key(capabilities)
        remove_value(r'Software\RegisteredApplications', 'WinCip')
    for scope in ('*', 'Directory'):
        base = classes + '\\' + scope + r'\shell\WinCip'
        if read(base, 'Icon') == f'"{executable}",0':
            delete_owned_key(base)
    server = classes + '\\CLSID\\' + SHELL_CLSID
    library = read(server + r'\InprocServer32')
    if library and Path(library).resolve().parent == executable.parent:
        delete_owned_key(server)
    # A development package at another location belongs to that other installation.
    location = str(executable.parent / 'shell_extension').replace("'", "''")
    script = "$p=Get-AppxPackage -Name 'WinCip.ShellExtension'; if ($p -and $p.InstallLocation -eq '" + location + "') { $p | Remove-AppxPackage }"
    result = subprocess.run([str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'),
                    '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True,
                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
    if result.returncode:
        raise RuntimeError('Windows no pudo retirar el paquete del Explorador. Cierra las ventanas del Explorador que lo utilizan y vuelve a intentarlo.')
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


if __name__ == '__main__':
    register(set_fallback_defaults=True)
