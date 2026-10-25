import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import threading
import unittest
from unittest.mock import patch

from workspaces import archive_workspace


class WorkspaceTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Windows pending-delete regression')
    def test_windows_locked_file_is_retried_until_handle_closes(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = [wintypes.HANDLE]
        close.restype = wintypes.BOOL
        timer = None
        handle = None
        try:
            with archive_workspace(prefix='wincip-pending-delete-') as name:
                folder = Path(name)
                document = folder / 'pending.txt'
                document.write_bytes(b'temporary content')
                handle = create(str(document), 0x80000000, 3, None, 3, 0x80, None)
                self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
                with self.assertRaises(OSError):
                    document.unlink()
                timer = threading.Timer(.12, lambda: close(handle))
                timer.start()
            timer.join()
            handle = None
            self.assertFalse(folder.exists())
        finally:
            if timer is not None:
                timer.join()
            elif handle is not None:
                close(handle)

    def test_directory_not_empty_race_is_retried(self):
        real_rmdir = os.rmdir
        injected = []
        def race(path, *args, **kwargs):
            if Path(path) == folder and not injected:
                (folder / 'late-file').write_bytes(b'arrived during cleanup')
                try:
                    return real_rmdir(path, *args, **kwargs)
                except OSError as error:
                    injected.append(error)
                    raise
            return real_rmdir(path, *args, **kwargs)
        with archive_workspace() as name:
            folder = Path(name)
            (folder / 'initial-file').touch()
            # Keep the patch active during the context manager's cleanup.
            patcher = patch('os.rmdir', side_effect=race)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher.stop()
        self.assertEqual(len(injected), 1)
        if os.name == 'nt':
            self.assertEqual(injected[0].winerror, 145)
        self.assertFalse(folder.exists())

    def test_unrelated_cleanup_failure_is_not_silenced_or_retried(self):
        real_cleanup = shutil.rmtree
        captured = []
        def fail(path, **kwargs):
            captured.append(path)
            raise PermissionError('unrelated permission failure')
        try:
            with patch('workspaces.shutil.rmtree', fail), patch('workspaces.time.sleep') as pause:
                with self.assertRaises(PermissionError):
                    with archive_workspace() as name:
                        (Path(name) / 'file').write_bytes(b'data')
                pause.assert_not_called()
            self.assertEqual(len(captured), 1)
        finally:
            for path in captured:
                real_cleanup(path)

    def test_operation_error_survives_cleanup_error(self):
        captured = []
        real_cleanup = shutil.rmtree
        def fail(workspace, **kwargs):
            captured.append(workspace)
            raise PermissionError('cleanup')
        try:
            with patch('workspaces.shutil.rmtree', fail):
                with self.assertRaisesRegex(ValueError, 'original error') as error:
                    with archive_workspace():
                        raise ValueError('original error')
            self.assertTrue(error.exception.__notes__)
        finally:
            for path in captured:
                real_cleanup(path)


if __name__ == '__main__':
    unittest.main()
