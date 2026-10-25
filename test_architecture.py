from pathlib import Path
import os
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch
import zipfile
import gzip

from archive_core import (ArchiveError, Cancelled, PasswordRequired, archive_version,
                          create_archive, extract_archive, list_archive, list_backups,
                          modify_archive, restore_backup, verify_archive)
from archive_formats import CREATE_FORMATS, format_for_path, available_create_formats, can_edit
from rar_backend import rar_encoder
from edit_sessions import ExternalEdits
from archive_policy import ResourceLimits, current_limits, operation_limits


class ArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.note = self.root / 'note.txt'
        self.note.write_bytes(b'original')

    def test_create_edit_and_empty_all_tar_formats_and_aliases(self):
        for extension in ('tar', 'tar.gz', 'tgz', 'tar.bz2', 'tbz2', 'tar.xz', 'txz'):
            with self.subTest(extension=extension):
                path = self.root / ('data.' + extension)
                fmt = format_for_path(path)
                create_archive([self.note], path, format=fmt.name, verify=True)
                modify_archive(path, rename=('note.txt', 'renamed.txt'), backup=True)
                modify_archive(path, additions=[self.note], new_folder='empty')
                self.assertEqual({e.name.rstrip('/') for e in list_archive(path)}, {'renamed.txt', 'note.txt', 'empty'})
                modify_archive(path, remove=['note.txt', 'renamed.txt', 'empty'])
                self.assertEqual(list_archive(path), [])
                verify_archive(path)
                self.assertTrue(list_backups(path))

    def test_tar_conversion_and_compression_levels(self):
        from archive_core import convert_archive
        original = create_archive([self.note], self.root / 'original.zip')
        for fmt in ('tar.bz2', 'tar.xz'):
            for level in (0, 1, 6, 9):
                path = self.root / f'level-{level}.{fmt}'
                create_archive([self.note], path, format=fmt, level=level, verify=True)
            converted = convert_archive(original, self.root / ('converted.' + fmt), format=fmt)
            output = extract_archive(converted, self.root / ('out-' + fmt))
            self.assertEqual((output / self.note.name).read_bytes(), b'original')

    def test_tar_password_and_multipart_edit_are_rejected(self):
        path = create_archive([self.note], self.root / 'data.tar', format='tar')
        before = path.read_bytes()
        with self.assertRaises(ArchiveError):
            modify_archive(path, new_password='secret')
        self.assertEqual(path.read_bytes(), before)
        split = self.root / 'split.zip'
        split.with_suffix('.z01').write_bytes(b'part')
        self.assertIsNone(format_for_path(split))
        self.assertIsNone(format_for_path(self.root / 'split.7z.001'))

    def test_restore_preserves_current_and_checks_encrypted_backup(self):
        for fmt in ('zip', '7z', 'tar.xz'):
            with self.subTest(fmt=fmt):
                secret = 'old password' if fmt in ('zip', '7z') else None
                path = create_archive([self.note], self.root / ('data.' + fmt), format=fmt, password=secret)
                old = path.read_bytes()
                modify_archive(path, password=secret, rename=('note.txt', 'renamed.txt'), backup=True)
                current = path.read_bytes()
                backup = list_backups(path)[0]
                if secret:
                    with self.assertRaises(PasswordRequired):
                        restore_backup(path, backup, password='wrong')
                    self.assertEqual(path.read_bytes(), current)
                restore_backup(path, backup, password=secret)
                self.assertEqual(path.read_bytes(), old)
                self.assertTrue(any(b.read_bytes() == current for b in list_backups(path)))

    def test_invalid_cancelled_or_racing_restore_never_replaces_current(self):
        path = create_archive([self.note], self.root / 'data.zip')
        original = path.read_bytes()
        corrupt = self.root / 'corrupt.bak'
        corrupt.write_bytes(b'broken')
        with self.assertRaises(ArchiveError):
            restore_backup(path, corrupt)
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaises(Cancelled):
            restore_backup(path, corrupt, cancelled)
        self.assertEqual(path.read_bytes(), original)
        valid = self.root / 'valid.bak'
        valid.write_bytes(original)
        def race(*args, **kwargs):
            path.write_bytes(b'another process changed it')
        with patch('archive_core.verify_archive', side_effect=race):
            with self.assertRaises(ArchiveError):
                restore_backup(path, valid)
        self.assertEqual(path.read_bytes(), b'another process changed it')

    def test_backup_listing_ignores_unrelated_names(self):
        source = self.root / 'data.zip'
        expected = ['data.zip.bak', 'data.zip.bak.2', 'data.zip.bak.10', 'data.zip.bak.100']
        for name in expected + ['data.zip.bak.1', 'data.zip.bak.evil', 'other.zip.bak', 'data.zip.bak.02']:
            (self.root / name).touch()
        self.assertEqual({p.name for p in list_backups(source)}, set(expected))

    def prepare_editor(self, fmt='zip', password=None):
        path = create_archive([self.note], self.root / ('data.' + fmt), format=fmt, password=password)
        copy = self.root / 'editor.txt'
        copy.write_bytes(b'original')
        manager = ExternalEdits()
        manager.track(path, 'note.txt', copy)
        return path, copy, manager

    def test_external_editor_writeback_for_zip_7z_and_tar(self):
        for fmt in available_create_formats():
            with self.subTest(fmt=fmt):
                path, copy, manager = self.prepare_editor(fmt)
                copy.write_bytes(b'edited externally')
                self.assertTrue(manager.needs_scan())
                changes = manager.changed()
                self.assertEqual(len(changes), 1)
                manager.commit(changes, backup=True)
                output = extract_archive(path, self.root / ('external-' + fmt))
                self.assertEqual((output / 'note.txt').read_bytes(), b'edited externally')
                self.assertEqual(manager.changed(), [])
                self.assertTrue(list_backups(path))

    def test_editor_copy_never_overwrites_a_changed_source(self):
        path, copy, manager = self.prepare_editor()
        copy.write_bytes(b'editor changes')
        modify_archive(path, rename=('note.txt', 'new.txt'))
        current = path.read_bytes()
        with self.assertRaises(ArchiveError):
            manager.commit(manager.changed())
        self.assertEqual(path.read_bytes(), current)
        self.assertEqual(copy.read_bytes(), b'editor changes')

    def test_editor_cancel_and_wrong_password_preserve_both_files(self):
        path, copy, manager = self.prepare_editor(password='secret')
        before = path.read_bytes()
        copy.write_bytes(b'edited')
        changes = manager.changed()
        with self.assertRaises(PasswordRequired):
            manager.commit(changes, password='wrong')
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(Cancelled):
            manager.commit(changes, cancel, password='secret')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(copy.read_bytes(), b'edited')

    def test_save_during_compression_remains_pending(self):
        path, copy, manager = self.prepare_editor()
        copy.write_bytes(b'first save')
        real_modify = modify_archive
        def later_save(*args, **kwargs):
            result = real_modify(*args, **kwargs)
            copy.write_bytes(b'new save during compression')
            return result
        with patch('edit_sessions.modify_archive', side_effect=later_save):
            manager.commit(manager.changed())
        self.assertEqual(len(manager.changed()), 1)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read('note.txt'), b'first save')
        manager.commit(manager.changed())
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read('note.txt'), b'new save during compression')

    def test_replacement_checks_original_version(self):
        path, copy, manager = self.prepare_editor()
        version = archive_version(path)
        modify_archive(path, new_folder='new')
        before = path.read_bytes()
        with self.assertRaises(ArchiveError):
            modify_archive(path, replacements=[('note.txt', copy)], expected_version=version)
        self.assertEqual(path.read_bytes(), before)

    def test_configurable_resource_limits_and_unbounded_opt_in(self):
        path = create_archive([self.note], self.root / 'data.zip')
        with operation_limits(ResourceLimits(max_entries=1, max_bytes=3)):
            with self.assertRaises(ArchiveError):
                extract_archive(path, self.root / 'too-large')
            with self.assertRaises(ArchiveError):
                verify_archive(path)
            with self.assertRaises(ArchiveError):
                create_archive([self.note], self.root / 'too-large.zip')
        self.assertFalse((self.root / 'too-large').exists())
        self.assertFalse((self.root / 'too-large.zip').exists())
        with operation_limits(ResourceLimits(0, 0)):
            output = extract_archive(path, self.root / 'unbounded')
            self.assertEqual((output / 'note.txt').read_bytes(), b'original')
            unsafe = self.root / 'unsafe.zip'
            with zipfile.ZipFile(unsafe, 'w') as archive:
                archive.writestr('../outside.txt', b'unsafe')
            with self.assertRaises(ArchiveError):
                extract_archive(unsafe, self.root / 'unsafe-output')

    def test_resource_context_is_thread_local_and_resets_on_failure(self):
        default = current_limits()
        other = []
        with self.assertRaises(RuntimeError):
            with operation_limits(ResourceLimits(2, 3)):
                thread = threading.Thread(target=lambda: other.append(current_limits()))
                thread.start()
                thread.join()
                self.assertEqual(current_limits(), ResourceLimits(2, 3))
                raise RuntimeError('reset')
        self.assertEqual(current_limits(), default)
        self.assertEqual(other, [default])

    def test_stream_and_seven_verification_obey_limits(self):
        stream = self.root / 'note.gz'
        stream.write_bytes(gzip.compress(b'content'))
        seven = create_archive([self.note], self.root / 'note.7z', format='7z')
        with operation_limits(ResourceLimits(1, 2)):
            for path in (stream, seven):
                with self.assertRaises(ArchiveError):
                    verify_archive(path)

    def test_zip_archive_and_entry_comments_survive_edits_and_encryption(self):
        path = self.root / 'comments.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.comment = b'archive comment'
            entry = zipfile.ZipInfo('note.txt')
            entry.comment = b'entry comment'
            entry.external_attr = 0o100640 << 16
            archive.writestr(entry, b'original')
        modify_archive(path, rename=('note.txt', 'renamed.txt'), new_password='secret')
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.comment, b'archive comment')
            self.assertEqual(archive.getinfo('renamed.txt').comment, b'entry comment')
            self.assertEqual(archive.getinfo('renamed.txt').external_attr, entry.external_attr)
        verify_archive(path, password='secret')
        modify_archive(path, password='secret', new_password=None, comment='Comentario nuevo'.encode('utf-8'))
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.comment, b'Comentario nuevo')
            self.assertEqual(archive.read('renamed.txt'), b'original')
        before = path.read_bytes()
        with self.assertRaises(ArchiveError):
            modify_archive(path, comment=b'x' * 65536)
        self.assertEqual(path.read_bytes(), before)

    @unittest.skipUnless(rar_encoder(), 'Installed RAR encoder is optional')
    def test_rar_create_edit_passwords_unicode_and_backup_restore(self):
        folder = self.root / 'carpeta ñ'
        (folder / 'vacía').mkdir(parents=True)
        (folder / 'archivo ñ.txt').write_bytes(b'content')
        for hide_names in (False, True):
            path = create_archive([folder], self.root / f'rar-{hide_names}.rar', format='rar',
                                  password='contraseña ñ', hide_names=hide_names, verify=True)
            with self.assertRaises(PasswordRequired):
                verify_archive(path, password='wrong')
            original = path.read_bytes()
            modify_archive(path, password='contraseña ñ', new_password='new', backup=True,
                           rename=('carpeta ñ/archivo ñ.txt', 'carpeta ñ/renombrado.txt'))
            output = extract_archive(path, self.root / f'rar-out-{hide_names}', password='new')
            self.assertEqual((output / 'carpeta ñ/renombrado.txt').read_bytes(), b'content')
            self.assertTrue((output / 'carpeta ñ/vacía').is_dir())
            restore_backup(path, list_backups(path)[0], password='contraseña ñ')
            self.assertEqual(path.read_bytes(), original)

    @unittest.skipUnless(rar_encoder(), 'Installed RAR encoder is optional')
    def test_rar_volumes_create_verify_and_extract_from_later_part(self):
        import os
        source = self.root / 'large.bin'
        source.write_bytes(os.urandom(2 * 1024**2))
        parts = create_archive([source], self.root / 'volumes.rar', format='rar', volume_mb=1,
                               level=0, password='secret', verify=True)
        volumes = sorted(parts.glob('*.rar'))
        self.assertGreaterEqual(len(volumes), 2)
        self.assertFalse(can_edit(volumes[0]))
        output = extract_archive(volumes[-1], self.root / 'rar-volumes-out', password='secret')
        self.assertEqual((output / source.name).read_bytes(), source.read_bytes())

    def test_absent_rar_writer_keeps_readers_and_other_formats_available(self):
        with patch('archive_formats.rar_encoder', return_value=None):
            self.assertNotIn('rar', available_create_formats())
            self.assertFalse(can_edit(self.root / 'source.rar'))
            self.assertIn('zip', available_create_formats())
        with patch('archive_core.rar_encoder', return_value=None):
            with self.assertRaises(ArchiveError):
                create_archive([self.note], self.root / 'missing.rar', format='rar')
        self.assertFalse((self.root / 'missing.rar').exists())

    def test_multiple_external_edits_commit_together_and_keep_other_members(self):
        path, copy, manager = self.prepare_editor()
        second = self.root / 'second.txt'
        second.write_bytes(b'second original')
        modify_archive(path, additions=[second])
        manager = ExternalEdits()
        manager.track(path, 'note.txt', copy)
        other = self.root / 'second-editor.txt'
        other.write_bytes(b'second original')
        manager.track(path, 'second.txt', other)
        copy.write_bytes(b'first edit')
        other.write_bytes(b'second edit')
        manager.commit(manager.changed())
        self.assertEqual(len(list_backups(path)), 1)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(archive.read('note.txt'), b'first edit')
            self.assertEqual(archive.read('second.txt'), b'second edit')

    def test_entry_count_limit_and_unbounded_listing(self):
        path = self.root / 'entries.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('one', b'1')
            archive.writestr('two', b'2')
        with operation_limits(ResourceLimits(1, 0)):
            with self.assertRaises(ArchiveError):
                list_archive(path)
        with operation_limits(ResourceLimits(0, 0)):
            self.assertEqual(len(list_archive(path)), 2)


class EditorInterfaceTests(unittest.TestCase):
    def setUp(self):
        from app import App
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'data.zip'
        environment = patch.dict(os.environ, {'WINCIP_SETTINGS': str(self.root / 'settings.json')})
        environment.start()
        self.addCleanup(environment.stop)
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('note.txt', b'original')
        self.app = App()
        self.app.withdraw()
        self.app.loaded(self.path, list_archive(self.path))
        self.addCleanup(self.finish)

    def finish(self):
        self.app.release_temporary_files()
        self.app.release_source()
        try:
            self.app.update_idletasks()
            for job in self.app.tk.call('after', 'info'):
                self.app.after_cancel(job)
            self.app.destroy()
        except tk.TclError:
            pass

    def wait(self):
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(.01)
        self.assertFalse(self.app.busy)

    def open_copy(self):
        self.app.tree.selection_set(self.app.tree.get_children()[0])
        with patch('app.os.startfile'), patch('app.messagebox.showerror') as error:
            self.app.open_selected()
            self.wait()
            error.assert_not_called()
        return self.app.output

    def test_save_editor_changes_and_reuse_same_copy(self):
        copy = self.open_copy()
        copy.write_bytes(b'edited')
        with patch('app.messagebox.askyesnocancel', return_value=True), patch('app.messagebox.showerror') as error:
            self.app.update_external_edits()
            self.wait()
            error.assert_not_called()
        with zipfile.ZipFile(self.path) as archive:
            self.assertEqual(archive.read('note.txt'), b'edited')
        self.assertTrue(copy.exists())
        self.assertEqual(self.open_copy(), copy)

    def test_clear_cancel_keeps_changed_copy_and_archive(self):
        copy = self.open_copy()
        copy.write_bytes(b'unsaved')
        with patch('app.messagebox.askyesnocancel', return_value=None):
            self.app.clear()
            self.wait()
        self.assertEqual(self.app.archive, self.path)
        self.assertEqual(copy.read_bytes(), b'unsaved')

    def test_clear_discard_removes_copy_without_changing_archive(self):
        copy = self.open_copy()
        copy.write_bytes(b'unsaved')
        with patch('app.messagebox.askyesnocancel', return_value=False):
            self.app.clear()
            self.wait()
        self.assertIsNone(self.app.archive)
        self.assertFalse(copy.exists())
        with zipfile.ZipFile(self.path) as archive:
            self.assertEqual(archive.read('note.txt'), b'original')

    def test_clear_save_commits_before_releasing_the_copy(self):
        copy = self.open_copy()
        copy.write_bytes(b'keep these edits')
        with patch('app.messagebox.askyesnocancel', return_value=True), patch('app.messagebox.showerror') as error:
            self.app.clear()
            self.wait()
            self.app.update()
            error.assert_not_called()
        self.assertIsNone(self.app.archive)
        self.assertFalse(copy.exists())
        with zipfile.ZipFile(self.path) as archive:
            self.assertEqual(archive.read('note.txt'), b'keep these edits')


if __name__ == '__main__':
    unittest.main()
