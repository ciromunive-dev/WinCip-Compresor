import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
from archive_core import (create_archive, modify_archive, list_archive, extract_archive, verify_archive, convert_archive, PasswordRequired, Cancelled, ArchiveError)
from archive_support import resolve_volume, archive_stem, MissingVolumeError

class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'notes.txt'
        self.source.write_bytes(b'old')

    def test_password_change_and_remove_both_formats(self):
        for fmt in ('zip','7z'):
            archive=create_archive([self.source],self.root/('data.'+fmt),format=fmt,password='old')
            modify_archive(archive,password='old',new_password='new',backup=True)
            self.assertTrue(archive.with_name(archive.name+'.bak').exists())
            with self.assertRaises(PasswordRequired):
                extract_archive(archive,self.root/('bad-'+fmt),password='old')
            verify_archive(archive,password='new')
            modify_archive(archive,password='new',new_password=None)
            out=extract_archive(archive,self.root/('out-'+fmt))
            self.assertEqual((out/self.source.name).read_bytes(),b'old')

    def test_update_policies_and_internal_folder(self):
        archive=create_archive([self.source],self.root/'data.zip')
        self.source.write_bytes(b'new')
        modify_archive(archive,additions=[self.source],conflict='skip',new_folder='empty')
        out=extract_archive(archive,self.root/'skip')
        self.assertEqual((out/'notes.txt').read_bytes(),b'old')
        self.assertTrue((out/'empty').is_dir())
        modify_archive(archive,additions=[self.source],conflict='replace')
        out=extract_archive(archive,self.root/'replace')
        self.assertEqual((out/'notes.txt').read_bytes(),b'new')
        old=1600000000
        os.utime(self.source,(old,old))
        self.source.write_bytes(b'older')
        os.utime(self.source,(old,old))
        modify_archive(archive,additions=[self.source],conflict='newer')
        out=extract_archive(archive,self.root/'newer')
        self.assertEqual((out/'notes.txt').read_bytes(),b'new')

    def test_edit_save_as_keeps_original(self):
        archive=create_archive([self.source],self.root/'data.zip')
        original=archive.read_bytes()
        copy=self.root/'copy.zip'
        modify_archive(archive,rename=('notes.txt','renamed.txt'),destination=copy)
        self.assertEqual(archive.read_bytes(),original)
        self.assertEqual(list_archive(copy)[0].name,'renamed.txt')

    def test_verified_creation_failure_does_not_replace_target(self):
        target=self.root/'data.zip'
        target.write_bytes(b'original')
        with patch('archive_core.verify_archive',side_effect=ArchiveError('verification failed')):
            with self.assertRaises(ArchiveError):
                create_archive([self.source],target,verify=True,overwrite=True)
        self.assertEqual(target.read_bytes(),b'original')

    def test_filter_and_store_mode(self):
        folder=self.root/'folder'
        (folder/'cache').mkdir(parents=True)
        (folder/'a.txt').write_bytes(b'text')
        (folder/'a.bin').write_bytes(b'bin')
        (folder/'cache'/'b.txt').write_bytes(b'excluded')
        archive=create_archive([folder],self.root/'filtered.zip',level=0,include=('*.txt',),exclude=('cache',),verify=True)
        with zipfile.ZipFile(archive) as handle:
            files=[info for info in handle.infolist() if not info.is_dir()]
            self.assertEqual([i.filename for i in files],['folder/a.txt'])
            self.assertEqual(files[0].compress_type,zipfile.ZIP_STORED)

    def test_tar_and_conversion_preserve_source(self):
        archive=create_archive([self.source],self.root/'data.zip',password='secret')
        before=archive.read_bytes()
        for fmt in ('tar','tar.gz','7z'):
            result=convert_archive(archive,self.root/('result.'+fmt),password='secret',format=fmt)
            out=extract_archive(result,self.root/('out-'+fmt))
            self.assertEqual((out/'notes.txt').read_bytes(),b'old')
        self.assertEqual(archive.read_bytes(),before)

    def test_volume_selection_and_missing_part(self):
        (self.root/'file.7z.001').write_bytes(b'1')
        (self.root/'file.7z.002').write_bytes(b'2')
        self.assertEqual(resolve_volume(self.root/'file.7z.002').name,'file.7z.001')
        (self.root/'file.7z.004').write_bytes(b'4')
        with self.assertRaisesRegex(MissingVolumeError,'003'):
            resolve_volume(self.root/'file.7z.002')
        self.assertEqual(archive_stem('movie.part01.rar'),'movie')
        self.assertEqual(archive_stem('backup.tar.gz'),'backup')

    def test_downloaded_zone_propagates_for_each_backend(self):
        Path(str(self.source)+':Zone.Identifier').write_bytes(b'[ZoneTransfer]\r\nZoneId=3\r\n')
        for fmt in ('zip','7z','tar.gz'):
            archive=create_archive([self.source],self.root/('data.'+fmt),format=fmt)
            Path(str(archive)+':Zone.Identifier').write_bytes(b'[ZoneTransfer]\r\nZoneId=3\r\n')
            out=extract_archive(archive,self.root/('out-'+fmt))
            self.assertIn(b'ZoneId=3',Path(str(out/'notes.txt')+':Zone.Identifier').read_bytes())

    def test_cancelled_verified_create_leaves_no_output(self):
        cancel=threading.Event()
        with self.assertRaises(Cancelled):
            create_archive([self.source],self.root/'cancel.zip',cancel=cancel,progress=lambda *_:cancel.set(),verify=True)
        self.assertFalse((self.root/'cancel.zip').exists())

if __name__=='__main__': unittest.main()
