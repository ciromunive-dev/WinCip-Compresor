import os
from pathlib import Path
import tempfile
import time
import threading
import unittest

from temporary_files import cleanup_temporary_files, finish_closed_sessions


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'Opened'
        self.root.mkdir()
        self.now = time.time()

    def session(self, age=7200):
        folder = Path(tempfile.mkdtemp(prefix='open-', dir=self.root))
        content = folder / 'content'
        content.mkdir()
        (content / 'file.txt').write_bytes(b'sample')
        for path in [*folder.rglob('*'), folder]:
            os.utime(path, (self.now - age, self.now - age))
        return folder

    def test_old_sessions_removed_and_recent_kept(self):
        old, recent = self.session(), self.session(age=60)
        result = cleanup_temporary_files(cache_root=self.root, now=self.now)
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(self.root.exists())
        self.assertEqual(result.removed_sessions, 1)
        self.assertEqual(result.freed_bytes, 6)

    def test_explicit_cleanup_can_remove_recent_copies(self):
        folder = self.session(age=60)
        result = cleanup_temporary_files(cache_root=self.root, now=self.now, min_age_seconds=0)
        self.assertFalse(folder.exists())
        self.assertEqual(result.removed_sessions, 1)

    def test_closing_one_session_preserves_another_windows_copy(self):
        first, second = self.session(age=10), self.session(age=10)
        cleanup_temporary_files(cache_root=self.root, min_age_seconds=0,
                                session_names={first.name})
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_closed_session_is_deleted_as_soon_as_viewer_releases_it(self):
        folder = self.session(age=10)
        file = folder / 'content' / 'file.txt'
        with file.open('rb'):
            worker = threading.Thread(target=finish_closed_sessions, args=([folder.name],),
                                      kwargs={'cache_root': self.root, 'retry_interval': .02})
            worker.start()
            time.sleep(.08)
            self.assertTrue(file.exists())
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(folder.exists())

    def test_recent_edits_keep_old_session(self):
        folder = self.session()
        file = folder / 'content' / 'file.txt'
        os.utime(file, (self.now - 10, self.now - 10))
        result = cleanup_temporary_files(cache_root=self.root, now=self.now)
        self.assertTrue(file.exists())
        self.assertEqual(result.removed_sessions, 0)

    def test_unrelated_folders_and_files_untouched(self):
        unrelated = self.root / 'my-documents'
        unrelated.mkdir()
        (unrelated / 'file.txt').write_bytes(b'keep')
        loose = self.root / 'file.txt'
        loose.write_bytes(b'keep')
        self.session()
        cleanup_temporary_files(cache_root=self.root, now=self.now, min_age_seconds=0)
        self.assertEqual((unrelated / 'file.txt').read_bytes(), b'keep')
        self.assertEqual(loose.read_bytes(), b'keep')

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_in_use_session_is_kept_intact_and_retried(self):
        folder = self.session()
        file = folder / 'content' / 'file.txt'
        with file.open('rb'):
            result = cleanup_temporary_files(cache_root=self.root, now=self.now)
            self.assertEqual(result.removed_sessions, 0)
            self.assertEqual(file.read_bytes(), b'sample')
        result = cleanup_temporary_files(cache_root=self.root, now=self.now)
        self.assertEqual(result.removed_sessions, 1)
        self.assertFalse(folder.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows junctions')
    def test_nested_junction_never_deletes_external_files(self):
        import _winapi
        outside = self.base / 'outside'
        outside.mkdir()
        protected = outside / 'keep.txt'
        protected.write_bytes(b'keep')
        folder = self.session()
        junction = folder / 'content' / 'linked'
        _winapi.CreateJunction(str(outside), str(junction))
        try:
            result = cleanup_temporary_files(cache_root=self.root, now=self.now, min_age_seconds=0)
            self.assertEqual(result.removed_sessions, 0)
            self.assertEqual(protected.read_bytes(), b'keep')
            self.assertTrue(folder.exists())
        finally:
            os.rmdir(junction)

    @unittest.skipUnless(os.name == 'nt', 'Windows junctions')
    def test_junction_cache_root_is_refused(self):
        import _winapi
        folder = self.session()
        junction = self.base / 'cache-link'
        _winapi.CreateJunction(str(self.root), str(junction))
        try:
            result = cleanup_temporary_files(cache_root=junction, now=self.now, min_age_seconds=0)
            self.assertEqual(result.removed_sessions, 0)
            self.assertTrue(folder.exists())
        finally:
            os.rmdir(junction)


if __name__ == '__main__':
    unittest.main()
