"""Owned operation folders with bounded retries for Windows deletion races."""
from contextlib import contextmanager
import errno
from pathlib import Path
import sys
import tempfile
import time
import shutil


def remove_tree_ignoring_missing_children(path):
    def onerror(operation, missing_path, error_info):
        error = error_info[1]
        if isinstance(error, FileNotFoundError):
            return
        raise error
    shutil.rmtree(path, onerror=onerror)


def cleanup_owned_directory(path, *, owned, cleanup=None):
    owned = Path(owned)
    parent = owned.parent
    active_error = sys.exc_info()[1]
    for delay in (.05, .1, .2, .4, .8, 0):
        try:
            target = Path(path)
            if target.exists() and (target.is_symlink() or target.resolve() != owned
                                    or target.resolve().parent != parent
                                    or getattr(target.lstat(), 'st_file_attributes', 0) & 0x400):
                raise ValueError('La carpeta de trabajo fue sustituida; no se ha eliminado.')
            if cleanup is not None:
                cleanup()
            elif target.exists():
                shutil.rmtree(target)
            return
        except OSError as error:
            transient = (getattr(error, 'winerror', None) in (32, 33, 145)
                         or error.errno in (errno.ENOTEMPTY, errno.EBUSY))
            if not transient or not delay:
                if active_error is not None:
                    active_error.add_note(f'No se pudo limpiar la carpeta de trabajo {owned}: {error}')
                    return
                raise
            time.sleep(delay)


@contextmanager
def archive_workspace(*, prefix='.wincip-', dir=None):
    workspace = tempfile.TemporaryDirectory(prefix=prefix, dir=dir)
    owned = Path(workspace.name).resolve(strict=True)
    # Cleanup is explicit below. A finalizer must not later remove a path that
    # was refused because another process replaced the allocated directory.
    workspace._finalizer.detach()
    try:
        yield workspace.name
    finally:
        cleanup_owned_directory(workspace.name, owned=owned,
                                cleanup=lambda: remove_tree_ignoring_missing_children(workspace.name))
