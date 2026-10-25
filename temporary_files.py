"""Clean only WinCip's isolated copies, never other Windows temporaries."""
from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import shutil
import tempfile
import time


MAX_TEMP_AGE = 3600
SESSION_NAME = re.compile(r'open-[a-z0-9_]{8}\Z')


@dataclass
class CleanupResult:
    removed_sessions: int = 0
    freed_bytes: int = 0
    skipped_sessions: int = 0


def temporary_root():
    # Stable cache location also covers copies opened before the product rename.
    return Path(tempfile.gettempdir()) / 'ArchivoFacil' / 'Opened'


def is_reparse(path):
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def files_are_available(files):
    if os.name != 'nt':
        return True
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    handles = []
    try:
        for file in files:
            # Exclusive probe: a reader, editor or player using the file makes
            # this fail. A locked session is left intact for the next cleanup.
            handle = create(str(file), 0x80010000, 0, None, 3, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                return False
            handles.append(handle)
        return True
    finally:
        for handle in handles:
            close(handle)


def inspect_session(session, root):
    files = []
    newest = session.stat().st_mtime
    total = 0

    def walk_error(error):
        raise error

    for base, dirs, names in os.walk(session, followlinks=False, onerror=walk_error):
        for path in [Path(base), *(Path(base) / name for name in dirs + names)]:
            # Check every directory before os.walk can descend into it. Junctions
            # and symlinks are excluded even if their current target is inside.
            if is_reparse(path) or not path.resolve().is_relative_to(root):
                raise ValueError('La carpeta temporal contiene un enlace o una ruta externa.')
            newest = max(newest, path.stat().st_mtime)
        for name in names:
            path = Path(base) / name
            files.append(path)
            total += path.stat().st_size
    return files, newest, total


def cleanup_temporary_files(*, cache_root=None, min_age_seconds=MAX_TEMP_AGE, now=None, session_names=None):
    result = CleanupResult()
    root = Path(cache_root) if cache_root is not None else temporary_root()
    if not root.exists():
        return result
    if is_reparse(root):
        result.skipped_sessions = 1
        return result
    root = root.resolve(strict=True)
    cutoff = (time.time() if now is None else now) - min_age_seconds
    try:
        candidates = list(root.iterdir())
    except OSError:
        result.skipped_sessions = 1
        return result
    for session in candidates:
        if not SESSION_NAME.fullmatch(session.name):
            continue
        if session_names is not None and session.name not in session_names:
            continue
        try:
            if is_reparse(session) or session.resolve().parent != root or not session.is_dir():
                result.skipped_sessions += 1
                continue
            files, newest, total = inspect_session(session, root)
            if (min_age_seconds > 0 and newest > cutoff) or not files_are_available(files):
                result.skipped_sessions += 1
                continue
            # Final check of the resolved absolute deletion target, immediately
            # before recursive deletion. Never remove the shared cache root.
            if session.resolve().parent != root or is_reparse(session):
                result.skipped_sessions += 1
                continue
            shutil.rmtree(session)
            result.removed_sessions += 1
            result.freed_bytes += total
        except FileNotFoundError:
            # Another instance may already have removed the same session.
            continue
        except (OSError, ValueError):
            result.skipped_sessions += 1
    return result


def session_name_for_file(file, *, cache_root=None):
    root = Path(cache_root) if cache_root is not None else temporary_root()
    try:
        parts = Path(file).resolve().relative_to(root.resolve()).parts
    except (OSError, ValueError):
        return None
    if len(parts) < 3 or not SESSION_NAME.fullmatch(parts[0]) or parts[1] != 'content':
        return None
    return parts[0]


def claim_temporary_file(file):
    """Keep the owning session protected from other instances' startup sweeps."""
    name = session_name_for_file(file)
    if name is None:
        return None
    root = temporary_root().resolve()
    session = root / name
    if is_reparse(session) or session.resolve().parent != root:
        raise ValueError('Ruta temporal no válida.')
    marker = session / '.owner.lock'
    if marker.exists() and is_reparse(marker):
        raise ValueError('Enlace no permitido en la carpeta temporal.')
    return marker.open('a+b')


def hold_archive_source(file):
    """A nested archive must survive until its own window closes."""
    return Path(file).open('rb') if session_name_for_file(file) is not None else None


def pending_sessions(names, *, cache_root=None):
    root = Path(cache_root) if cache_root is not None else temporary_root()
    if not root.exists() or is_reparse(root):
        return []
    root = root.resolve()
    pending = []
    for name in names:
        if not SESSION_NAME.fullmatch(name):
            continue
        folder = root / name
        try:
            if folder.is_dir() and not is_reparse(folder) and folder.resolve().parent == root:
                inspect_session(folder, root)
                pending.append(name)
        except (OSError, ValueError):
            continue
    return pending


def finish_closed_sessions(names, *, cache_root=None, retry_interval=1):
    """Finish deleting copies locked by external viewers after the window closes."""
    pending = pending_sessions(names, cache_root=cache_root)
    while pending:
        cleanup_temporary_files(cache_root=cache_root, min_age_seconds=0, session_names=set(pending))
        pending = pending_sessions(pending, cache_root=cache_root)
        if pending:
            time.sleep(retry_interval)
