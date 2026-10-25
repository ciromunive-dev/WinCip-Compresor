import io
from pathlib import Path
import tarfile
import tempfile
import threading
import unittest
import zipfile

from archive_core import ArchiveError, Cancelled, create_zip, extract_archive, extract_into, list_archive, verify_archive


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Documentos'
        self.source.mkdir()
        (self.source / 'vacía').mkdir()
        (self.source / 'notas ñ.txt').write_text('¡Hola!\n' * 1000, encoding='utf-8')
        (self.source / 'datos.bin').write_bytes(bytes(range(256)) * 300)

    def test_zip_round_trip_and_verify(self):
        archive = create_zip([self.source], self.root / 'backup.zip')
        self.assertEqual(len(list_archive(archive)), 4)
        self.assertIn('CRC', verify_archive(archive))
        output = extract_archive(archive, self.root / 'resultado')
        self.assertTrue((output / 'Documentos' / 'vacía').is_dir())
        for original in self.source.iterdir():
            if original.is_file():
                self.assertEqual(original.read_bytes(), (output / 'Documentos' / original.name).read_bytes())

    def test_tar_variants(self):
        for mode, suffix in [('w', '.tar'), ('w:gz', '.tar.gz'), ('w:bz2', '.tar.bz2'), ('w:xz', '.tar.xz')]:
            with self.subTest(mode=mode):
                archive = self.root / ('backup' + suffix)
                with tarfile.open(archive, mode) as tar:
                    tar.add(self.source, arcname='./Documentos')
                output = extract_archive(archive, self.root / ('out' + suffix))
                self.assertEqual((self.source / 'datos.bin').read_bytes(), (output / 'Documentos/datos.bin').read_bytes())

    def test_unsafe_zip_names(self):
        for index, name in enumerate(['../escape.txt', '..\\escape.txt', '/absolute', 'C:/absolute', 'file:stream', 'CON.txt', 'dir/../../outside']):
            with self.subTest(name=name):
                archive = self.root / f'unsafe{index}.zip'
                with zipfile.ZipFile(archive, 'w') as handle:
                    handle.writestr(name, b'bad')
                with self.assertRaises(ArchiveError):
                    extract_archive(archive, self.root / 'unsafe-output')
                self.assertFalse((self.root / 'unsafe-output').exists())

    def test_extract_multiple_files_with_trailing_spaces_in_folder_names(self):
        archive = self.root / 'names.zip'
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr('#859 Virales /uno.txt', b'one')
            handle.writestr('637 [ PacksVirales.com ] /dos.txt', b'two')
            handle.writestr('tercero. ', b'three')
            handle.writestr('normal.txt', b'normal')
        output = extract_archive(archive, self.root / 'out', members=[
            '#859 Virales /', '637 [ PacksVirales.com ] /'])
        self.assertEqual((output / '#859 Virales' / 'uno.txt').read_bytes(), b'one')
        self.assertEqual((output / '637 [ PacksVirales.com ]' / 'dos.txt').read_bytes(), b'two')
        self.assertFalse((output / 'normal.txt').exists())
        extract_into(archive, output, members=['normal.txt'])
        self.assertEqual((output / 'normal.txt').read_bytes(), b'normal')
        full = extract_archive(archive, self.root / 'full')
        self.assertEqual((full / 'tercero').read_bytes(), b'three')

    def test_trailing_name_collision_leaves_no_extraction_destination(self):
        archive = self.root / 'collision-after-normalizing.zip'
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr('carpeta /uno.txt', b'first')
            handle.writestr('carpeta/uno.txt', b'second')
        destination = self.root / 'collision-output'
        with self.assertRaisesRegex(ArchiveError, 'Nombres duplicados'):
            extract_archive(archive, destination)
        self.assertFalse(destination.exists())

    def test_tar_symlink_rejected(self):
        archive = self.root / 'link.tar'
        with tarfile.open(archive, 'w') as handle:
            member = tarfile.TarInfo('link')
            member.type = tarfile.SYMTYPE
            member.linkname = '../elsewhere'
            handle.addfile(member)
        with self.assertRaises(ArchiveError):
            extract_archive(archive, self.root / 'out')

    def test_case_collisions_and_parent_conflicts(self):
        for names in [('A.txt', 'a.txt'), ('folder', 'folder/a.txt')]:
            with zipfile.ZipFile(self.root / 'collision.zip', 'w') as handle:
                for name in names:
                    handle.writestr(name, b'x')
            with self.assertRaises(ArchiveError):
                extract_archive(self.root / 'collision.zip', self.root / 'out')

    def test_no_overwrite(self):
        target = self.root / 'keep.zip'
        target.write_bytes(b'original')
        with self.assertRaises(ArchiveError):
            create_zip([self.source], target)
        self.assertEqual(target.read_bytes(), b'original')
        archive = create_zip([self.source], self.root / 'new.zip')
        with self.assertRaises(ArchiveError):
            extract_archive(archive, self.source)

    def test_duplicate_sources_and_nested_output_rejected(self):
        with self.assertRaises(ArchiveError):
            create_zip([self.source, self.source], self.root / 'out.zip')
        with self.assertRaises(ArchiveError):
            create_zip([self.source], self.source / 'inside.zip')

    def test_cancel_compression_cleans_temporary_files(self):
        cancel = threading.Event()
        target = self.root / 'cancel.zip'
        with self.assertRaises(Cancelled):
            create_zip([self.source], target, cancel=cancel, progress=lambda *_: cancel.set())
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob('.archivofacil-*')))

    def test_cancel_extraction_cleans_temporary_files(self):
        archive = create_zip([self.source], self.root / 'ok.zip')
        cancel = threading.Event()
        target = self.root / 'cancelled'
        with self.assertRaises(Cancelled):
            extract_archive(archive, target, cancel=cancel, progress=lambda *_: cancel.set())
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob('.archivofacil-*')))

    def test_corrupt_zip_rolls_back_extraction(self):
        archive = self.root / 'broken.zip'
        payload = b'Unique sample payload to corrupt'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as handle:
            handle.writestr('sample.txt', payload)
        archive.write_bytes(archive.read_bytes().replace(payload, b'X' + payload[1:]))
        with self.assertRaises(zipfile.BadZipFile):
            verify_archive(archive)
        with self.assertRaises(zipfile.BadZipFile):
            extract_archive(archive, self.root / 'out')
        self.assertFalse((self.root / 'out').exists())
        self.assertFalse(list(self.root.glob('.archivofacil-*')))

    def test_compression_level_is_applied(self):
        data = self.root / 'repeated.txt'
        data.write_bytes(b'A' * 500000)
        fast = create_zip([data], self.root / 'fast.zip', level=1)
        small = create_zip([data], self.root / 'small.zip', level=9)
        self.assertLess(small.stat().st_size, fast.stat().st_size)


if __name__ == '__main__':
    unittest.main()
