from pathlib import Path
import bz2
import gzip
import lzma
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from archive_core import (ArchiveError, Cancelled, extract_archive, list_archive, prepare_file_to_open,
                          list_seven, seven_zip, validate_entries, verify_archive)


class SevenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Carpeta con espacios'
        (self.source / 'vacía').mkdir(parents=True)
        (self.source / 'interior').mkdir()
        (self.source / 'niño.txt').write_text('Información con acentos.\n' * 500, encoding='utf-8')
        (self.source / 'interior' / 'niño.txt').write_text('Otro contenido', encoding='utf-8')

    def run_engine(self, command):
        subprocess.run(command, cwd=self.root, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)

    def assert_round_trip(self, archive):
        entries = list_archive(archive)
        self.assertEqual(len([e for e in entries if not e.directory]), 2)
        self.assertIn('No se encontraron errores', verify_archive(archive))
        selected = next(e for e in entries if 'interior' in e.name and not e.directory)
        cache = self.root / 'preview'
        preview = prepare_file_to_open(archive, selected.name, cache_root=cache)
        self.assertEqual(preview.read_bytes(), (self.source / 'interior' / 'niño.txt').read_bytes())
        self.assertEqual(len([p for p in cache.rglob('*') if p.is_file()]), 1)
        out = extract_archive(archive, self.root / 'resultado')
        for path in self.source.rglob('*'):
            destination = out / path.relative_to(self.root)
            if path.is_dir():
                self.assertTrue(destination.is_dir(), path)
            else:
                self.assertEqual(path.read_bytes(), destination.read_bytes())

    def test_solid_7z_unicode_nested_round_trip(self):
        archive = self.root / 'prueba.7z'
        self.run_engine([seven_zip(), 'a', '-t7z', str(archive), self.source.name])
        self.assert_round_trip(archive)

    @unittest.skipUnless(Path(r'C:\Program Files\WinRAR\Rar.exe').exists(), 'RAR test fixture generator unavailable')
    def test_rar_round_trip(self):
        archive = self.root / 'prueba.rar'
        self.run_engine([r'C:\Program Files\WinRAR\Rar.exe', 'a', '-r', '-idq', str(archive), self.source.name])
        self.assert_round_trip(archive)

    def test_single_stream_formats(self):
        payload = b'compressed payload' * 1000
        for extension, compress in [('gz', gzip.compress), ('bz2', bz2.compress), ('xz', lzma.compress)]:
            with self.subTest(extension=extension):
                archive = self.root / ('sample.txt.' + extension)
                archive.write_bytes(compress(payload))
                destination = extract_archive(archive, self.root / ('out-' + extension))
                files = [p for p in destination.rglob('*') if p.is_file()]
                self.assertEqual(len(files), 1)
                self.assertEqual(files[0].read_bytes(), payload)

    def test_encrypted_7z_rejected(self):
        archive = self.root / 'encrypted.7z'
        self.run_engine([seven_zip(), 'a', '-t7z', '-ptest-only', str(archive), self.source.name])
        with self.assertRaises(ArchiveError):
            extract_archive(archive, self.root / 'out')
        self.assertFalse((self.root / 'out').exists())

    def test_cancel_external_extraction(self):
        archive = self.root / 'prueba.7z'
        self.run_engine([seven_zip(), 'a', '-t7z', str(archive), self.source.name])
        cancel = threading.Event()
        with self.assertRaises(Cancelled):
            extract_archive(archive, self.root / 'out', cancel, lambda *_: cancel.set())
        self.assertFalse((self.root / 'out').exists())
        self.assertFalse(list(self.root.glob('.archivofacil-*')))

    def test_external_unsafe_names_and_links(self):
        for block in ['Path = ../outside\nSize = 1', 'Path = link\nSize = 1\nSymbolic Link = ../outside']:
            with patch('archive_core.run_seven', return_value=block):
                with self.assertRaises(ArchiveError):
                    validate_entries(list_seven('mock.7z'))


if __name__ == '__main__':
    unittest.main()
