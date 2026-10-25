from pathlib import Path
import tempfile
import threading
import unittest
import zipfile
import tarfile
import gzip
import stat

from archive_core import ArchiveError, Cancelled, prepare_file_to_open


class OpenFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'cache'

    def archive(self, name='example.zip', content=b'selected contents'):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('other.txt', b'other contents')
            archive.writestr('folder/selected.txt', content)
        return path

    def test_only_selected_file_is_written(self):
        archive = self.archive()
        before = archive.read_bytes()
        result = prepare_file_to_open(archive, 'folder/selected.txt', cache_root=self.cache)
        self.assertEqual(result.read_bytes(), b'selected contents')
        self.assertEqual([p for p in self.cache.rglob('*') if p.is_file()], [result])
        self.assertEqual(archive.read_bytes(), before)

    def test_same_names_never_overwrite_open_copies(self):
        first = prepare_file_to_open(self.archive('one.zip', b'one'), 'folder/selected.txt', cache_root=self.cache)
        second = prepare_file_to_open(self.archive('two.zip', b'two'), 'folder/selected.txt', cache_root=self.cache)
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), b'one')
        self.assertEqual(second.read_bytes(), b'two')

    def test_open_file_in_folder_with_trailing_space(self):
        archive = self.root / 'spaces.zip'
        name = 'folder with space /subfolder. /selected.txt '
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr(name, b'correct content')
            handle.writestr('folder with space /other.txt', b'not selected')
        original = archive.read_bytes()
        result = prepare_file_to_open(archive, name, cache_root=self.cache)
        self.assertEqual(result.name, 'selected.txt')
        self.assertEqual(result.read_bytes(), b'correct content')
        self.assertEqual(archive.read_bytes(), original)
        self.assertEqual(len([p for p in self.cache.rglob('*') if p.is_file()]), 1)

    def test_path_traversal_stays_rejected_with_trailing_spaces(self):
        archive = self.root / 'traversal.zip'
        for name in ('../folder /selected.txt', '/folder /selected.txt', 'C:/folder /selected.txt', '.. /selected.txt'):
            with zipfile.ZipFile(archive, 'w') as handle:
                handle.writestr(name, b'unsafe')
            with self.assertRaises(ArchiveError):
                prepare_file_to_open(archive, name, cache_root=self.cache)
            self.assertEqual(list(self.cache.iterdir()), [])

    def test_tar_selection_keeps_original_member_index(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'first.txt').write_bytes(b'first')
        (source / 'last.txt').write_bytes(b'last')
        archive = self.root / 'sample.tar.gz'
        with tarfile.open(archive, 'w:gz') as handle:
            handle.add(source, arcname='source')
        result = prepare_file_to_open(archive, 'source/last.txt', cache_root=self.cache)
        self.assertEqual(result.read_bytes(), b'last')
        self.assertEqual(len([p for p in self.cache.rglob('*') if p.is_file()]), 1)

    def test_single_compressed_stream(self):
        archive = self.root / 'note.txt.gz'
        archive.write_bytes(gzip.compress(b'note'))
        result = prepare_file_to_open(archive, 'note.txt', cache_root=self.cache)
        self.assertEqual(result.read_bytes(), b'note')

    def test_missing_file_and_directory_leave_no_session(self):
        archive = self.root / 'directory.zip'
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr('folder/', b'')
        for name in ('folder/', 'missing.txt'):
            with self.assertRaises(ArchiveError):
                prepare_file_to_open(archive, name, cache_root=self.cache)
            self.assertEqual(list(self.cache.iterdir()), [])

    def test_unsafe_selected_name_and_link_rejected(self):
        archive = self.root / 'unsafe.zip'
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr('../outside.txt', b'unsafe')
            info = zipfile.ZipInfo('link.txt')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            handle.writestr(info, b'../outside.txt')
        for name in ('../outside.txt', 'link.txt'):
            with self.assertRaises(ArchiveError):
                prepare_file_to_open(archive, name, cache_root=self.cache)
            self.assertEqual(list(self.cache.iterdir()), [])
        self.assertFalse((self.root / 'outside.txt').exists())

    def test_cancel_cleans_only_new_session(self):
        archive = self.archive()
        saved = prepare_file_to_open(archive, 'other.txt', cache_root=self.cache)
        cancel = threading.Event()
        with self.assertRaises(Cancelled):
            prepare_file_to_open(archive, 'folder/selected.txt', cancel, lambda *_: cancel.set(), cache_root=self.cache)
        self.assertEqual(saved.read_bytes(), b'other contents')
        self.assertEqual(len(list(self.cache.iterdir())), 1)

    def test_open_copy_preserves_downloaded_zone(self):
        archive = self.archive()
        zone = b'[ZoneTransfer]\r\nZoneId=3\r\n'
        Path(str(archive) + ':Zone.Identifier').write_bytes(zone)
        result = prepare_file_to_open(archive, 'other.txt', cache_root=self.cache)
        self.assertEqual(result.read_bytes(), b'other contents')
        self.assertEqual(Path(str(result) + ':Zone.Identifier').read_bytes(), zone)
        self.assertEqual(Path(str(archive) + ':Zone.Identifier').read_bytes(), zone)


if __name__ == '__main__':
    unittest.main()
