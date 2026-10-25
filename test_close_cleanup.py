from pathlib import Path
import io
import os
import time
import threading
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
import zipfile

from app import App
from archive_core import prepare_file_to_open, list_archive
from temporary_files import cleanup_temporary_files


class CloseCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        environment = patch.dict(os.environ, {'WINCIP_SETTINGS': str(self.base / 'settings.json')})
        environment.start()
        self.addCleanup(environment.stop)
        self.cache = self.base / 'Opened'
        self.root_patch = patch('temporary_files.temporary_root', return_value=self.cache)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.app_root_patch = patch('app.temporary_root', return_value=self.cache)
        self.app_root_patch.start()
        self.addCleanup(self.app_root_patch.stop)
        self.archive = self.base / 'source.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.writestr('note.txt', b'original')
        self.app = App()
        self.app.withdraw()
        self.addCleanup(self.destroy_app)
        self.app.loaded(self.archive, list_archive(self.archive))

    def destroy_app(self):
        try:
            self.app.update_idletasks()
            for job in self.app.tk.call('after', 'info'):
                self.app.after_cancel(job)
            self.app.release_temporary_files()
            self.app.release_source()
            self.app.destroy()
        except tk.TclError:
            pass

    def open_copy(self):
        result = prepare_file_to_open(self.archive, 'note.txt', cache_root=self.cache)
        with patch('app.os.startfile'):
            self.app.open_prepared(result)
        return result

    def test_closing_window_deletes_its_fresh_copy(self):
        result = self.open_copy()
        self.app.close()
        self.assertFalse(result.exists())
        self.assertEqual(list(self.cache.iterdir()), [])
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(archive.read('note.txt'), b'original')

    def test_close_archive_menu_deletes_copy_immediately(self):
        result = self.open_copy()
        self.app.clear()
        self.assertFalse(result.exists())
        self.assertIsNone(self.app.archive)

    def test_switching_archive_deletes_previous_copy(self):
        result = self.open_copy()
        other = self.base / 'other.zip'
        with zipfile.ZipFile(other, 'w') as archive:
            archive.writestr('other.txt', b'other')
        self.app.loaded(other, list_archive(other))
        self.assertFalse(result.exists())
        self.assertEqual(self.app.archive, other)

    def test_another_windows_copy_survives_close(self):
        foreign = prepare_file_to_open(self.archive, 'note.txt', cache_root=self.cache)
        own = self.open_copy()
        self.app.close()
        self.assertFalse(own.exists())
        self.assertEqual(foreign.read_bytes(), b'original')

    def test_locked_copy_gets_cleanup_helper_on_close(self):
        result = self.open_copy()
        name = next(iter(self.app._temporary_sessions))
        with result.open('rb'), patch('app.subprocess.Popen') as helper:
            self.app.close()
            helper.assert_called_once()
            command = helper.call_args.args[0]
            self.assertEqual(command[-2:], ['--cleanup-temporaries', name])
            self.assertTrue(result.exists())

    def test_startup_sweep_preserves_an_active_windows_old_copy(self):
        result = self.open_copy()
        session = result.parent.parent
        old = time.time() - 7200
        for path in [*session.rglob('*'), session]:
            os.utime(path, (old, old))
        self.app.clean_temporary_files()
        self.app._cleanup_thread.join(timeout=2)
        self.assertEqual(result.read_bytes(), b'original')
        self.app.close()
        self.assertFalse(result.exists())

    def test_nested_archive_survives_parent_close_and_is_later_removed(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, 'w') as archive:
            archive.writestr('inner.txt', b'nested')
        outer = self.base / 'outer.zip'
        with zipfile.ZipFile(outer, 'w') as archive:
            archive.writestr('inside.zip', inner.getvalue())
        self.app.loaded(outer, list_archive(outer))
        nested = prepare_file_to_open(outer, 'inside.zip', cache_root=self.cache)
        with patch('app.os.startfile'):
            self.app.open_prepared(nested)
        with patch.object(tk, '_default_root', None):
            child = App()
            child.withdraw()
        try:
            child.loaded(nested, list_archive(nested))
            with patch('app.subprocess.Popen', side_effect=OSError('helper unavailable')):
                self.app.close()
            output = prepare_file_to_open(child.archive, 'inner.txt', cache_root=self.cache)
            self.assertEqual(output.read_bytes(), b'nested')
            child.close()
            deadline = time.monotonic() + 3
            while nested.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertFalse(nested.exists())
        finally:
            child.release_source()
            try:
                child.update_idletasks()
                for job in child.tk.call('after', 'info'):
                    child.after_cancel(job)
                child.destroy()
            except tk.TclError:
                pass

    def test_helper_failure_falls_back_and_cleans_after_file_release(self):
        result = self.open_copy()
        with result.open('rb'), patch('app.subprocess.Popen', side_effect=OSError('helper unavailable')):
            self.app.clear()
            self.assertTrue(result.exists())
        deadline = time.monotonic() + 3
        while result.exists() and time.monotonic() < deadline:
            time.sleep(.03)
        self.assertFalse(result.exists())

    def test_callback_failure_does_not_stop_later_results(self):
        def fail(_):
            raise OSError('callback failure')
        self.app.events.put(('success', (fail, None)))
        self.app.events.put(('progress', (1, 1, 'next result')))
        with patch('app.messagebox.showerror') as error:
            self.app.poll()
            error.assert_called_once()
        self.app.poll()
        self.assertIn('next result', self.app.status.get())


if __name__ == '__main__':
    unittest.main()
