from pathlib import Path
import os
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from archive_core import (create_archive, create_zip, extract_archive, extract_into,
    list_archive, verify_archive, modify_zip, prepare_file_to_open, PasswordRequired,
    ArchiveError, Cancelled)

class CompleteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'niño'
        self.source.mkdir()
        (self.source / 'vacía').mkdir()
        (self.source / 'uno.txt').write_text('contenido único', encoding='utf-8')
        (self.source / 'dos.txt').write_bytes(b'hello' * 100)

    def test_password_round_trips(self):
        for fmt in ('zip', '7z'):
            with self.subTest(fmt=fmt):
                archive = create_archive([self.source], self.root / ('private.' + fmt), format=fmt, password='secreto ñ !')
                with self.assertRaises(PasswordRequired):
                    list_archive(archive)
                with self.assertRaises(PasswordRequired):
                    extract_archive(archive, self.root / ('bad' + fmt), password='incorrecta')
                self.assertFalse((self.root / ('bad' + fmt)).exists())
                entries = list_archive(archive, password='secreto ñ !')
                self.assertTrue(any(e.name == 'niño/uno.txt' for e in entries))
                verify_archive(archive, password='secreto ñ !')
                copy = prepare_file_to_open(archive, 'niño/uno.txt', password='secreto ñ !', cache_root=self.root / 'cache')
                self.assertEqual(copy.read_bytes(), (self.source / 'uno.txt').read_bytes())

    def test_plain_7z_does_not_require_password(self):
        archive = create_archive([self.source], self.root / 'plain.7z', format='7z')
        self.assertEqual(len(list_archive(archive)), 4)
        extract_archive(archive, self.root / 'out')

    def test_select_directory_and_timestamp(self):
        date = 1600000000
        os.utime(self.source / 'uno.txt', (date, date))
        archive = create_zip([self.source], self.root / 'data.zip')
        out = extract_archive(archive, self.root / 'out', members=['niño/uno.txt'])
        self.assertEqual(len(list(out.rglob('*.txt'))), 1)
        self.assertAlmostEqual((out / 'niño/uno.txt').stat().st_mtime, date, delta=2)
        out2 = extract_archive(archive, self.root / 'out2', members=['niño/'])
        self.assertEqual(len(list(out2.rglob('*.txt'))), 2)
        self.assertTrue((out2 / 'niño/vacía').is_dir())

    def test_conflict_policies(self):
        archive = create_zip([self.source / 'uno.txt'], self.root / 'data.zip')
        for policy in ('rename', 'skip', 'replace'):
            out = self.root / policy
            out.mkdir()
            (out / 'uno.txt').write_bytes(b'original')
            extract_into(archive, out, conflict=policy)
            self.assertEqual((out / 'uno.txt').read_bytes(), (self.source / 'uno.txt').read_bytes() if policy == 'replace' else b'original')
            if policy == 'rename':
                self.assertEqual((out / 'uno (2).txt').read_bytes(), (self.source / 'uno.txt').read_bytes())

    def test_merge_rollback(self):
        archive = create_zip([self.source], self.root / 'data.zip')
        out = self.root / 'out'
        (out / 'niño').mkdir(parents=True)
        (out / 'niño/uno.txt').write_bytes(b'old')
        cancel = threading.Event()
        original = Path.rename
        def move(path, target):
            result = original(path, target)
            if path.name == 'uno.txt' and 'content' in str(path):
                cancel.set()
            return result
        with patch.object(Path, 'rename', move):
            with self.assertRaises(Cancelled):
                extract_into(archive, out, cancel, conflict='replace')
        self.assertEqual((out / 'niño/uno.txt').read_bytes(), b'old')
        self.assertFalse((out / 'niño/dos.txt').exists())

    def test_zip_edit_plain_and_encrypted(self):
        extra = self.root / 'extra.txt'
        extra.write_bytes(b'extra')
        for secret, name in [(None, 'plain.zip'), ('secret', 'encrypted.zip')]:
            archive = create_archive([self.source], self.root / name, password=secret)
            modify_zip(archive, password=secret, remove=['niño/dos.txt'], rename=('niño/uno.txt', 'niño/nuevo.txt'), additions=[extra], folder='niño')
            names = [e.name for e in list_archive(archive, password=secret)]
            self.assertIn('niño/nuevo.txt', names)
            self.assertIn('niño/extra.txt', names)
            self.assertNotIn('niño/dos.txt', names)
            verify_archive(archive, password=secret)
            if secret:
                with self.assertRaises(PasswordRequired):
                    list_archive(archive)

    def test_failed_edit_preserves_source(self):
        archive = create_zip([self.source], self.root / 'data.zip')
        before = archive.read_bytes()
        with self.assertRaises(ArchiveError):
            modify_zip(archive, rename=('niño/uno.txt', '../escape.txt'))
        self.assertEqual(archive.read_bytes(), before)

    def test_split_archive_round_trip(self):
        (self.source / 'random.bin').write_bytes(os.urandom(2300000))
        parts = create_archive([self.source], self.root / 'split.7z', format='7z', volume_mb=1, password='secret')
        self.assertGreaterEqual(len(list(parts.iterdir())), 3)
        first = parts / 'split.7z.001'
        out = extract_archive(first, self.root / 'out', password='secret')
        self.assertEqual((out / 'niño/random.bin').read_bytes(), (self.source / 'random.bin').read_bytes())

    def test_split_zip_unicode_password(self):
        (self.source / 'random.bin').write_bytes(os.urandom(2300000))
        parts = create_archive([self.source], self.root / 'split.zip', volume_mb=1, password='clave ñ')
        first = parts / 'split.zip.001'
        with self.assertRaises(PasswordRequired):
            list_archive(first)
        verify_archive(first, password='clave ñ')
        out = extract_archive(first, self.root / 'out', password='clave ñ')
        self.assertEqual((out / 'niño/random.bin').read_bytes(), (self.source / 'random.bin').read_bytes())

    def test_rar_split_password(self):
        engine = Path(r'C:\Program Files\WinRAR\Rar.exe')
        if not engine.exists():
            self.skipTest('WinRAR unavailable for fixture')
        (self.source / 'random.bin').write_bytes(os.urandom(2300000))
        archive = self.root / 'split.rar'
        subprocess.run([str(engine), 'a', '-r', '-idq', '-hpsecret', '-v1m', str(archive), str(self.source)], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        first = self.root / 'split.part1.rar'
        self.assertTrue(first.exists())
        out = extract_archive(first, self.root / 'out', password='secret')
        self.assertEqual(next(out.rglob('random.bin')).read_bytes(), (self.source / 'random.bin').read_bytes())

    def test_rar_password_and_hidden_names(self):
        engine = Path(r'C:\Program Files\WinRAR\Rar.exe')
        if not engine.exists():
            self.skipTest('WinRAR unavailable for fixture')
        for flag in ('-psecret', '-hpsecret'):
            archive = self.root / (flag[1:3] + '.rar')
            subprocess.run([str(engine), 'a', '-r', '-idq', flag, str(archive), str(self.source)], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            with self.assertRaises(PasswordRequired):
                list_archive(archive)
            verify_archive(archive, password='secret')
            out = extract_archive(archive, self.root / (flag[1:3] + '-out'), password='secret')
            self.assertEqual(len(list(out.rglob('uno.txt'))), 1)

if __name__ == '__main__':
    unittest.main()
