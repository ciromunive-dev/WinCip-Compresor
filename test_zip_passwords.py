"""ZIP passwords from Windows tools and UTF-8 tools use different bytes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import pyzipper

from archive_core import (PasswordRequired, extract_archive,
                          modify_archive, prepare_file_to_open, verify_archive)


class ZipPasswordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.password = 'contraseña café 123'
        self.content = bytes(range(256)) * 5000

    def fixture(self, encoding):
        archive = self.root / (encoding + '.zip')
        with pyzipper.AESZipFile(archive, 'w', compression=pyzipper.ZIP_DEFLATED,
                               encryption=pyzipper.WZ_AES) as writer:
            writer.setpassword(self.password.encode(encoding))
            writer.writestr('carpeta/notas.txt', self.content)
        return archive

    def test_utf8_and_windows_passwords_extract_and_verify(self):
        for encoding in ('utf-8', 'cp1252', 'cp437'):
            with self.subTest(encoding=encoding):
                archive = self.fixture(encoding)
                before = archive.read_bytes()
                verify_archive(archive, password=self.password)
                output = extract_archive(archive, self.root / ('out-' + encoding), password=self.password)
                self.assertEqual((output / 'carpeta/notas.txt').read_bytes(), self.content)
                self.assertEqual(archive.read_bytes(), before)

    def test_wrong_password_leaves_no_partial_files(self):
        archive = self.fixture('cp437')
        destination = self.root / 'output'
        before = set(self.root.iterdir())
        with self.assertRaises(PasswordRequired):
            extract_archive(archive, destination, password='clave errónea')
        self.assertFalse(destination.exists())
        self.assertEqual(set(self.root.iterdir()), before)

    def test_legacy_password_preview_copy_and_edit(self):
        archive = self.fixture('cp1252')
        copy = prepare_file_to_open(archive, 'carpeta/notas.txt', password=self.password,
                                    cache_root=self.root / 'cache')
        self.assertEqual(copy.read_bytes(), self.content)
        original = archive.read_bytes()
        modify_archive(archive, password=self.password, new_password='nueva contraseña',
                       rename=('carpeta/notas.txt', 'carpeta/editado.txt'), backup=True)
        self.assertEqual(archive.with_name(archive.name + '.bak').read_bytes(), original)
        output = extract_archive(archive, self.root / 'edited', password='nueva contraseña')
        self.assertEqual((output / 'carpeta/editado.txt').read_bytes(), self.content)

    def test_damaged_ciphertext_is_not_accepted_as_a_password_variant(self):
        archive = self.fixture('utf-8')
        with pyzipper.AESZipFile(archive) as reader:
            info = reader.infolist()[0]
        data = bytearray(archive.read_bytes())
        name_size = int.from_bytes(data[info.header_offset + 26:info.header_offset + 28], 'little')
        extra_size = int.from_bytes(data[info.header_offset + 28:info.header_offset + 30], 'little')
        payload = info.header_offset + 30 + name_size + extra_size
        data[payload + info.compress_size - 1] ^= 1
        archive.write_bytes(data)
        destination = self.root / 'damaged'
        with self.assertRaises(pyzipper.BadZipFile):
            extract_archive(archive, destination, password=self.password)
        self.assertFalse(destination.exists())

    @unittest.skipUnless(os.name == 'nt' and Path(r'C:\Program Files\WinRAR\WinRAR.exe').is_file(),
                         'WinRAR ZIP fixture generator unavailable')
    def test_real_winrar_zip_with_non_ascii_password(self):
        source = self.root / 'sample.txt'
        source.write_bytes(self.content)
        archive = self.root / 'winrar.zip'
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        subprocess.run([r'C:\Program Files\WinRAR\WinRAR.exe', 'a', '-afzip', '-inul',
                        '-p' + self.password, str(archive), source.name],
                       cwd=self.root, check=True, timeout=30, startupinfo=startup)
        verify_archive(archive, password=self.password)
        output = extract_archive(archive, self.root / 'winrar-out', password=self.password)
        self.assertEqual((output / source.name).read_bytes(), self.content)


if __name__ == '__main__':
    unittest.main()
