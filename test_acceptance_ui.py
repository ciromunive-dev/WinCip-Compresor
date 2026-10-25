"""Acceptance checks through WinCip's actual Tk controls and job callbacks."""
import os
import json
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
import zipfile
from unittest.mock import patch
from PIL import Image

from app import App
from archive_core import ArchiveError, create_archive, list_archive, zip_comment
from archive_formats import available_create_formats
from dialogs import Modal


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def control(window, kind, *, text=None):
    matches = [child for child in descendants(window) if isinstance(child, kind)
               and (text is None or child.cget('text') == text)]
    if len(matches) != 1:
        raise AssertionError(f'Expected one {kind.__name__} {text!r}, found {len(matches)}')
    return matches[0]


def accept(window, label):
    control(window.footer, tk.Button, text=label).invoke()


class UserInterfaceAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'WINCIP_SETTINGS': str(self.root / 'settings.json')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.app = App()
        self.app.withdraw()
        self.addCleanup(self.dispose)

    def dispose(self):
        try:
            self.app.update_idletasks()
            for job in self.app.tk.call('after', 'info'):
                self.app.after_cancel(job)
            self.app.destroy()
        except tk.TclError:
            pass

    def archive(self):
        source = self.root / 'root.txt'
        source.write_bytes(b'from-archive')
        folder = self.root / 'folder'
        folder.mkdir()
        (folder / 'child.txt').write_bytes(b'child')
        path = create_archive([source, folder], self.root / 'source.zip')
        self.app.loaded(path, list_archive(path))
        return path

    def recent_menu(self):
        shown = []
        with patch.object(tk.Menu, 'tk_popup', lambda menu, *_: shown.append(menu)):
            self.app.show_more()
        return self.app.nametowidget(shown[0].entrycget('Recientes', 'menu'))

    def add_menu(self):
        shown = []
        with patch.object(tk.Menu, 'tk_popup', lambda menu, *_: shown.append(menu)):
            self.app.show_add()
        return shown[0]

    def immediate_job(self, label, operation, callback, **_):
        callback(operation())

    def test_recent_menu_reopens_archive_and_clears_history(self):
        first = self.archive()
        source = self.root / 'other.txt'
        source.write_bytes(b'other')
        second = create_archive([source], self.root / 'other.zip')
        self.app.loaded(second, list_archive(second))
        recent = self.recent_menu()
        self.assertEqual(recent.entrycget(0, 'label'), str(second))
        self.assertEqual(recent.entrycget(1, 'label'), str(first))
        with patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            recent.invoke(1)
        self.assertEqual(self.app.archive, first)
        self.assertEqual([entry.name for entry in self.app.entries], ['root.txt', 'folder/', 'folder/child.txt'])
        self.recent_menu().invoke('Borrar historial')
        self.assertEqual(self.app.settings['recent'], [])
        self.assertEqual(json.loads(self.app.settings_path.read_text(encoding='utf-8'))['recent'], [])

    def test_recent_preference_survives_restart_and_can_be_reenabled(self):
        source = self.root / 'source.txt'
        source.write_bytes(b'source')
        first = create_archive([source], self.root / 'first.zip')
        second = create_archive([source], self.root / 'second.zip')

        def toggle(window, focus=None):
            control(window.body, tk.Checkbutton, text='Recordar comprimidos recientes').invoke()
            accept(window, 'Guardar')

        with patch.object(Modal, 'present', toggle):
            self.app.preferences()
        self.assertFalse(self.app.settings['remember_recent'])
        self.app.loaded(first, list_archive(first))
        self.assertEqual(self.app.settings['recent'], [])

        self.dispose()
        self.app = App()
        self.app.withdraw()
        self.assertFalse(self.app.settings['remember_recent'])
        self.assertEqual(self.app.settings['recent'], [])

        with patch.object(Modal, 'present', toggle):
            self.app.preferences()
        self.assertTrue(self.app.settings['remember_recent'])
        self.app.loaded(second, list_archive(second))
        self.assertEqual(self.app.settings['recent'], [str(second)])

    def test_open_button_reads_supported_archive_formats(self):
        source = self.root / 'content.txt'
        source.write_bytes(b'format-check')
        formats = ['zip', '7z', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz']
        if 'rar' in available_create_formats():
            formats.append('rar')
        with patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            for archive_format in formats:
                with self.subTest(archive_format=archive_format):
                    path = create_archive([source], self.root / ('content.' + archive_format),
                                          format=archive_format)
                    with patch('app.filedialog.askopenfilename', return_value=str(path)):
                        self.app.open_button.invoke()
                    self.assertEqual(self.app.archive, path)
                    self.assertEqual(self.app.heading.cget('text'), path.name)
                    self.assertEqual([entry.name for entry in self.app.entries], ['content.txt'])

    def test_internal_navigation_controls_handle_explicit_and_implicit_folders(self):
        archive = self.root / 'folders.zip'
        with zipfile.ZipFile(archive, 'w') as result:
            result.writestr('explicit/', b'')
            result.writestr('explicit/one.txt', b'one')
            result.writestr('implicit/two.txt', b'two')
        self.app.loaded(archive, list_archive(archive))
        folders = {entry.name: row for row, entry in self.app.row_entries.items() if entry.directory}
        self.assertEqual(set(folders), {'explicit/', 'implicit/'})
        self.app.tree.selection_set(folders['explicit/'])
        self.app.open_selected()
        self.assertEqual(self.app.current_folder, 'explicit/')
        self.assertEqual([entry.name for entry in self.app.row_entries.values()], ['explicit/one.txt'])
        self.app.up_button.invoke()
        self.assertEqual(self.app.current_folder, '')
        row = next(row for row, entry in self.app.row_entries.items() if entry.name == 'implicit/')
        self.app.tree.selection_set(row)
        self.app.open_selected()
        self.assertEqual(self.app.current_folder, 'implicit/')
        self.assertEqual([entry.name for entry in self.app.row_entries.values()], ['implicit/two.txt'])
        self.app.history_move(-1)
        self.assertEqual(self.app.current_folder, '')
        self.app.history_move(1)
        self.assertEqual(self.app.current_folder, 'implicit/')

    def test_control_a_selects_rows_or_text_according_to_focus(self):
        self.archive()
        self.app.deiconify()
        self.app.update()
        self.app.tree.focus_set()
        self.app.tree.event_generate('<Control-a>')
        self.app.update()
        self.assertEqual(len(self.app.tree.selection()), len(self.app.tree.get_children()))

        search = next(child for child in descendants(self.app)
                      if isinstance(child, ttk.Entry)
                      and child.cget('textvariable') == str(self.app.search))
        self.app.tree.selection_remove(self.app.tree.selection())
        search.insert(0, 'buscar')
        search.focus_set()
        search.event_generate('<Control-a>')
        self.app.update()
        self.assertTrue(search.selection_present())
        self.assertEqual(search.selection_get(), 'buscar')
        self.assertEqual(self.app.tree.selection(), ())

    def test_add_menu_uses_both_pickers_and_keeps_folder_structure(self):
        first = self.root / 'first.txt'
        second = self.root / 'second.txt'
        first.write_bytes(b'first')
        second.write_bytes(b'second')
        folder = self.root / 'documents'
        folder.mkdir()
        (folder / 'nested.txt').write_bytes(b'nested')
        with patch('app.filedialog.askopenfilenames', return_value=(str(first), str(second))):
            self.add_menu().invoke('Archivos para comprimir…')
            self.add_menu().invoke('Archivos para comprimir…')
        with patch('app.filedialog.askdirectory', return_value=str(folder)):
            self.add_menu().invoke('Carpeta para comprimir…')
        self.assertEqual(self.app.sources, [first, second, folder])
        self.assertEqual(len(self.app.tree.get_children()), 3)
        target = self.root / 'selected.zip'
        with patch('workflows.filedialog.asksaveasfilename', return_value=str(target)), \
             patch.object(Modal, 'present', lambda window, focus=None: accept(window, 'Continuar')), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            self.app.compress()
        with zipfile.ZipFile(target) as result:
            self.assertEqual(set(result.namelist()), {'first.txt', 'second.txt',
                                                        'documents/', 'documents/nested.txt'})
            self.assertEqual(result.read('documents/nested.txt'), b'nested')

    def test_extraction_dialog_selection_and_all_conflict_policies(self):
        self.archive()
        folder_row = next(i for i, entry in self.app.row_entries.items() if entry.directory)
        self.app.tree.selection_set(folder_row)
        with patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            def select_folder(window, focus=None):
                self.assertIn('Extraer archivos', window.title())
                accept(window, 'Extraer')
            parent = self.root / 'selected'
            parent.mkdir()
            with patch('features.filedialog.askdirectory', return_value=str(parent)), \
                 patch.object(Modal, 'present', select_folder):
                self.app.extract_selected()
            self.assertEqual((parent / 'source' / 'folder' / 'child.txt').read_bytes(), b'child')
            self.assertFalse((parent / 'source' / 'root.txt').exists())

            for policy, expected_original, alternate in (
                ('Renombrar', b'old', True),
                ('Omitir', b'old', False),
                ('Reemplazar', b'from-archive', False),
            ):
                with self.subTest(policy=policy):
                    destination = self.root / policy
                    destination.mkdir()
                    (destination / 'root.txt').write_bytes(b'old')
                    def merge(window, focus=None):
                        control(window.body, tk.Checkbutton, text='Crear una subcarpeta nueva').invoke()
                        control(window.body, ttk.Combobox).set(policy)
                        accept(window, 'Extraer')
                    with patch('features.filedialog.askdirectory', return_value=str(destination)), \
                         patch.object(Modal, 'present', merge):
                        self.app.extract()
                    self.assertEqual((destination / 'root.txt').read_bytes(), expected_original)
                    self.assertEqual((destination / 'folder' / 'child.txt').read_bytes(), b'child')
                    self.assertEqual((destination / 'root (2).txt').exists(), alternate)

    def test_preferences_dialog_persists_controls_and_rejects_bad_limit(self):
        self.app.settings['recent'] = ['old.zip']
        def invalid(window, focus=None):
            entries = [child for child in descendants(window.body) if type(child) is tk.Entry]
            self.assertEqual(len(entries), 2)
            entries[0].delete(0, 'end')
            entries[0].insert(0, '-1')
            with patch('workflows.messagebox.showerror') as error:
                accept(window, 'Guardar')
            error.assert_called_once()
            self.assertTrue(window.winfo_exists())
            entries[0].delete(0, 'end')
            entries[0].insert(0, '25')
            entries[1].delete(0, 'end')
            entries[1].insert(0, '2')
            control(window.body, tk.Checkbutton, text='Recordar comprimidos recientes').invoke()
            control(window.body, tk.Checkbutton, text='Verificar después de crear').invoke()
            control(window.body, tk.Checkbutton, text='Crear respaldo antes de editar').invoke()
            controls = [child for child in descendants(window.body) if isinstance(child, ttk.Combobox)]
            self.assertEqual(len(controls), 3)
            controls[0].set('7z')
            controls[1].set('Máxima')
            controls[2].set('Omitir')
            accept(window, 'Guardar')
        with patch.object(Modal, 'present', invalid):
            self.app.preferences()
        self.assertEqual(self.app.settings['recent'], [])
        self.assertEqual(self.app.settings['max_entries'], 25)
        self.assertEqual(self.app.settings['max_gib'], 2)
        self.assertEqual(self.app.settings['format'], '7z')
        self.assertEqual(self.app.settings['edit_conflict'], 'Omitir')
        self.assertEqual(self.app.level_value.get(), 9)
        saved = json.loads(self.app.settings_path.read_text(encoding='utf-8'))
        self.assertEqual(saved['format'], '7z')
        self.assertEqual(saved['max_entries'], 25)
        self.assertFalse(saved['verify_created'])
        self.assertFalse(saved['backup_edits'])

        self.dispose()
        self.app = App()
        self.app.withdraw()
        self.assertEqual(self.app.settings['format'], '7z')
        self.assertEqual(self.app.level_value.get(), 9)
        self.assertEqual(self.app.settings['edit_conflict'], 'Omitir')
        self.assertFalse(self.app.settings['verify_created'])
        self.assertFalse(self.app.settings['backup_edits'])
        source = self.root / 'draft.txt'
        source.write_bytes(b'draft')
        self.app.add_paths([source])
        def inspect_defaults(window, focus=None):
            combos = [child for child in descendants(window.body) if isinstance(child, ttk.Combobox)]
            self.assertEqual(combos[0].get(), '7z')
            self.assertEqual(combos[1].get(), 'Máxima')
            verify = control(window.body, tk.Checkbutton, text='Verificar antes de guardar')
            self.assertFalse(bool(int(window.getvar(verify.cget('variable')))))
            window.destroy()
        with patch.object(Modal, 'present', inspect_defaults):
            self.app.compress()

    def test_single_properties_and_about_dialog_content(self):
        self.archive()
        row = next(i for i, entry in self.app.row_entries.items() if entry.name == 'root.txt')
        self.app.tree.selection_set(row)
        with patch.object(self.app, 'show_info') as show:
            self.app.properties()
            self.app.about()
            self.app.help()
        self.assertEqual(show.call_count, 3)
        self.assertIn('Ruta: root.txt', show.call_args_list[0].args[2])
        self.assertIn('Versión 3.2.0', show.call_args_list[1].args[1])
        self.assertIn('Alt+Izquierda/Derecha', show.call_args_list[2].args[2])

    def test_create_dialog_applies_format_level_filters_and_verify(self):
        folder = self.root / 'documents'
        folder.mkdir()
        (folder / 'keep.txt').write_bytes(b'A' * 500)
        (folder / 'omit.tmp').write_bytes(b'omit')
        self.app.add_paths([folder])
        target = self.root / 'filtered.zip'
        def interact(window, focus=None):
            if 'Filtros de archivos' in window.title():
                fields = [child for child in descendants(window.body) if type(child) is tk.Entry]
                fields[0].insert(0, '*.txt')
                fields[1].insert(0, '*.tmp')
                accept(window, 'Aplicar')
                return
            combos = [child for child in descendants(window.body) if isinstance(child, ttk.Combobox)]
            combos[0].set('zip')
            combos[1].set('Sin compresión')
            control(window.body, tk.Button, text='Elegir filtros de inclusión y exclusión…').invoke()
            verify = control(window.body, tk.Checkbutton, text='Verificar antes de guardar')
            self.assertEqual(verify.getvar(verify.cget('variable')), 1)
            accept(window, 'Continuar')
        with patch.object(Modal, 'present', interact), \
             patch('workflows.filedialog.asksaveasfilename', return_value=str(target)), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            self.app.compress()
        with zipfile.ZipFile(target) as result:
            self.assertEqual(set(result.namelist()), {'documents/', 'documents/keep.txt'})
            self.assertEqual(result.getinfo('documents/keep.txt').compress_type, zipfile.ZIP_STORED)
            self.assertEqual(result.read('documents/keep.txt'), b'A' * 500)

    def test_preview_dialog_displays_text_and_image_and_rejects_large_file(self):
        note = self.root / 'note.txt'
        note.write_text('visible preview', encoding='utf-8')
        picture = self.root / 'picture.png'
        Image.new('RGB', (8, 8), '#3266e3').save(picture)
        html = self.root / 'page.html'
        html.write_text('<b>texto HTML</b>', encoding='utf-8')
        svg = self.root / 'drawing.svg'
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding='utf-8')
        archive = create_archive([note, picture, html, svg], self.root / 'previews.zip')
        self.app.loaded(archive, list_archive(archive))
        observed = []
        def inspect(window, focus=None):
            texts = [child for child in descendants(window.body) if isinstance(child, tk.Text)]
            pictures = [child for child in descendants(window.body) if isinstance(child, tk.Label)
                        and hasattr(child, 'image')]
            if texts:
                observed.append(texts[0].get('1.0', 'end-1c'))
            elif pictures:
                observed.append('image')
            window.destroy()
        with patch.object(self.app, 'run_job', side_effect=self.immediate_job), \
             patch.object(Modal, 'present', inspect):
            for name in ('note.txt', 'picture.png', 'page.html', 'drawing.svg'):
                row = next(i for i, entry in self.app.row_entries.items() if entry.name == name)
                self.app.tree.selection_set(row)
                self.app.preview()
        self.assertEqual(observed, ['visible preview', 'image', '<b>texto HTML</b>',
                                    '<svg xmlns="http://www.w3.org/2000/svg"/>'])
        self.app.release_temporary_files()
        self.app.loaded(archive, [type(list_archive(archive)[0])('large.txt', 11 * 1024**2, None, False)])
        self.app.tree.selection_set('0')
        with patch('workflows.messagebox.showinfo') as notice:
            self.app.preview()
        notice.assert_called_once()

    def test_batch_menu_uses_selected_archives_and_reports_two_results(self):
        first = self.root / 'first.txt'
        second = self.root / 'second.txt'
        first.write_bytes(b'first')
        second.write_bytes(b'second')
        one = create_archive([first], self.root / 'one.zip')
        two = create_archive([second], self.root / 'two.zip')
        destination = self.root / 'batch'
        destination.mkdir()
        with patch('features.filedialog.askopenfilenames', return_value=(str(one), str(two))), \
             patch('features.filedialog.askdirectory', return_value=str(destination)), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job), \
             patch.object(self.app, 'show_info') as summary:
            self.app.extract_batch()
        self.assertEqual((destination / 'one' / 'first.txt').read_bytes(), b'first')
        self.assertEqual((destination / 'two' / 'second.txt').read_bytes(), b'second')
        self.assertIn('Completados: 2', summary.call_args.args[2])

    def test_edit_handlers_create_rename_remove_and_restore_backup(self):
        archive = self.archive()
        with patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            with patch('tkinter.simpledialog.askstring', return_value='new folder'):
                self.app.new_folder()
            self.assertIn('new folder/', [entry.name for entry in list_archive(archive)])

            row = next(i for i, entry in self.app.row_entries.items() if entry.name == 'root.txt')
            self.app.tree.selection_set(row)
            with patch('features.simpledialog.askstring', return_value='renamed.txt'):
                self.app.rename_entry()
            self.assertIn('renamed.txt', [entry.name for entry in list_archive(archive)])

            row = next(i for i, entry in self.app.row_entries.items() if entry.name == 'renamed.txt')
            self.app.tree.selection_set(row)
            with patch('features.messagebox.askyesno', return_value=True):
                self.app.delete_entries()
            self.assertNotIn('renamed.txt', [entry.name for entry in list_archive(archive)])

            def restore(window, focus=None):
                accept(window, 'Restaurar')
            with patch.object(Modal, 'present', restore):
                self.app.restore_archive_backup()
            self.assertIn('renamed.txt', [entry.name for entry in list_archive(archive)])

    def test_comment_dialog_checks_byte_limit_and_saves_unicode(self):
        archive = self.archive()
        def interact(window, focus=None):
            area = control(window.body, tk.Text)
            area.insert('1.0', 'ñ' * 40000)
            with patch('workflows.messagebox.showerror') as error:
                accept(window, 'Guardar')
            error.assert_called_once()
            self.assertTrue(window.winfo_exists())
            area.delete('1.0', 'end')
            area.insert('1.0', 'Comentario de prueba ñ')
            accept(window, 'Guardar')
        with patch.object(Modal, 'present', interact), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            self.app.edit_comment()
        self.assertEqual(zip_comment(archive), 'Comentario de prueba ñ'.encode('utf-8'))

    def test_password_dialog_changes_then_removes_zip_protection(self):
        archive = self.archive()
        def set_password(window, focus=None):
            accept(window, 'Continuar')
        with patch.object(Modal, 'present', set_password), \
             patch('workflows.password_dialog', return_value='secret'), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            self.app.change_password()
        self.assertEqual(self.app.password, 'secret')
        with zipfile.ZipFile(archive) as result:
            self.assertTrue(result.getinfo('root.txt').flag_bits & 1)

        def remove_password(window, focus=None):
            control(window.body, ttk.Combobox).set('Quitar contraseña')
            accept(window, 'Continuar')
        with patch.object(Modal, 'present', remove_password), \
             patch('workflows.messagebox.askyesno', return_value=True), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            self.app.change_password()
        self.assertIsNone(self.app.password)
        with zipfile.ZipFile(archive) as result:
            self.assertEqual(result.read('root.txt'), b'from-archive')

    def test_combined_selection_excludes_unselected_file_and_sort_keeps_selection(self):
        first = self.root / 'first.txt'
        second = self.root / 'second.txt'
        excluded = self.root / 'excluded.txt'
        for path in (first, second, excluded):
            path.write_bytes(path.stem.encode())
        folder = self.root / 'nested'
        folder.mkdir()
        (folder / 'child.txt').write_bytes(b'child')
        archive = create_archive([first, second, excluded, folder], self.root / 'mixed.zip')
        self.app.loaded(archive, list_archive(archive))
        selected = {'first.txt', 'second.txt', 'nested/'}
        rows = [i for i, entry in self.app.row_entries.items() if entry.name in selected]
        self.app.tree.selection_set(rows)
        for column in ('name', 'size', 'type', 'packed', 'ratio'):
            self.app.sort_by(column)
            ascending = [entry.name for entry in self.app.row_entries.values()]
            self.assertEqual(set(self.app.selected_names()), selected)
            self.app.sort_by(column)
            descending = [entry.name for entry in self.app.row_entries.values()]
            self.assertEqual(set(descending), set(ascending))
            if column == 'name':
                self.assertEqual(descending, list(reversed(ascending)))
            self.assertEqual(set(self.app.selected_names()), selected)
        destination = self.root / 'selection'
        destination.mkdir()
        def choose(window, focus=None):
            accept(window, 'Extraer')
        with patch('features.filedialog.askdirectory', return_value=str(destination)), \
             patch.object(Modal, 'present', choose), \
             patch.object(self.app, 'run_job', side_effect=self.immediate_job):
            self.app.extract_selected()
        output = destination / 'mixed'
        self.assertEqual((output / 'first.txt').read_bytes(), b'first')
        self.assertEqual((output / 'second.txt').read_bytes(), b'second')
        self.assertEqual((output / 'nested' / 'child.txt').read_bytes(), b'child')
        self.assertFalse((output / 'excluded.txt').exists())

    def test_save_as_rejects_same_path_and_split_volume(self):
        archive = self.archive()
        with patch('workflows.filedialog.asksaveasfilename', return_value=str(archive)), \
             patch.object(self.app, 'run_job') as job:
            self.app.save_archive_as()
        with self.assertRaises(ArchiveError):
            job.call_args.args[1]()
        self.assertTrue(archive.exists())

        self.app.archive = self.root / 'set.zip.001'
        self.app.archive.write_bytes(b'part')
        target = self.root / 'copy.zip'
        with patch('workflows.filedialog.asksaveasfilename', return_value=str(target)), \
             patch.object(self.app, 'run_job') as job:
            self.app.save_archive_as()
        with self.assertRaisesRegex(ArchiveError, 'Convertir'):
            job.call_args.args[1]()
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
