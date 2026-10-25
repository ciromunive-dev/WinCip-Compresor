import os
import tempfile
from pathlib import Path
import tkinter as tk
import unittest
import zipfile
from unittest.mock import patch
from app import App
from dialogs import monitor_area
from archive_core import ArchiveError, Entry, PasswordRequired, create_archive, list_archive, safe_name

class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'WINCIP_SETTINGS': str(Path(self.temp.name) / 'settings.json')})
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

    def load(self):
        self.app.loaded(Path(self.temp.name) / 'example.zip', [Entry('folder/one.txt', 30, 10, False), Entry('folder/two.txt', 10, 8, False), Entry('root.txt', 100, 20, False)])

    def test_main_window_starts_centered(self):
        self.app.deiconify()
        self.app.update_idletasks()
        left, top, right, bottom = monitor_area(self.app)
        self.assertAlmostEqual(self.app.winfo_x() + self.app.winfo_width() / 2,
                               (left + right) / 2, delta=2)
        self.assertAlmostEqual(self.app.winfo_y() + self.app.winfo_height() / 2,
                               (top + bottom) / 2, delta=2)

    def test_logo_and_button_padding_follow_display_scale(self):
        self.assertEqual(self.app.brand_icon.width(), self.app.px(48))
        self.assertEqual(self.app.empty_icon.width(), self.app.px(128))
        self.assertEqual(int(self.app.add_button['padx']), self.app.px(16))

    def test_main_window_fits_available_work_area(self):
        with patch('app.monitor_area', return_value=(100, 50, 900, 650)):
            small = App()
        try:
            small.update_idletasks()
            self.assertLessEqual(small.winfo_width(), 800)
            self.assertLessEqual(small.winfo_height(), 600)
            self.assertEqual(small.winfo_x(), 100 + (800 - small.winfo_width()) // 2)
            self.assertEqual(small.winfo_y(), 50 + (600 - small.winfo_height()) // 2)
        finally:
            small.update_idletasks()
            for job in small.tk.call('after', 'info'):
                small.after_cancel(job)
            small.destroy()

    def test_implicit_folders_navigation_and_search(self):
        self.load()
        self.assertEqual(self.app.up_button['text'], '↗ Carpeta')
        self.assertEqual(len(self.app.tree.get_children()), 2)
        folder = next(i for i, e in self.app.row_entries.items() if e.directory)
        self.app.tree.selection_set(folder)
        self.app.open_selected()
        self.assertEqual(self.app.current_folder, 'folder/')
        self.assertEqual(self.app.up_button['text'], '↑ Subir')
        self.assertEqual(len(self.app.tree.get_children()), 2)
        self.app.sort_by('size')
        self.assertEqual(self.app.row_entries['0'].size, 10)
        self.app.go_up()
        self.assertEqual(self.app.current_folder, '')
        self.assertEqual(self.app.up_button['text'], '↗ Carpeta')
        self.app.search.set('two')
        self.assertEqual(self.app.selected_names(), [])
        self.assertEqual(len(self.app.tree.get_children()), 1)
        self.assertEqual(self.app.row_entries['0'].name, 'folder/two.txt')

    def test_up_from_archive_root_opens_containing_folder(self):
        self.load()
        with patch('features.os.startfile') as open_folder:
            self.app.up_button.invoke()
        open_folder.assert_called_once_with(str(self.app.archive.parent))
        self.assertEqual(self.app.current_folder, '')

    def test_browse_folder_with_trailing_space_without_weakening_extraction(self):
        folder = '#859 Virales '
        self.app.loaded(Path(self.temp.name) / 'example.zip',
                        [Entry(folder + '/sample.txt', 12, 8, False)])
        self.app.tree.selection_set('0')
        self.app.open_selected()
        self.assertEqual(self.app.current_folder, folder + '/')
        self.assertEqual(self.app.row_entries['0'].name, folder + '/sample.txt')
        self.app.go_up()
        self.assertEqual(self.app.current_folder, '')
        with self.assertRaises(ArchiveError):
            safe_name(folder + '/sample.txt')

    def test_location_rejects_parent_segments(self):
        self.load()
        with patch('workflows.messagebox.showerror') as error:
            self.app.navigate('../folder')
        error.assert_called_once()
        self.assertEqual(self.app.current_folder, '')

    def test_password_retry_and_cancel(self):
        action, callback = lambda: None, lambda result: None
        self.app.retry_job = ('Reading', action, callback)
        self.app.events.put(('error', PasswordRequired('Password')))
        with patch('app.password_dialog', return_value='secret'), patch.object(self.app, 'run_job') as retry:
            self.app.poll()
            self.assertEqual(self.app.password, 'secret')
            retry.assert_called_once_with('Reading', action, callback)
        self.app.events.put(('error', PasswordRequired('Password')))
        with patch('app.password_dialog', return_value=None), patch.object(self.app, 'run_job') as retry:
            self.app.poll()
            retry.assert_not_called()

    def test_drop_files_to_sources_and_recent_preferences(self):
        source = Path(self.temp.name) / 'note.txt'
        source.write_text('text')
        event = type('Drop', (), {'data': self.app.tk.call('list', str(source))})()
        # Tcl returns a tuple for a generated list; real drop events provide its string.
        event.data = '{' + str(source) + '}'
        self.app.dropped(event)
        self.assertEqual(self.app.sources, [source])
        self.app.level_value.set(9)
        self.assertTrue(self.app.settings_path.exists())
        self.assertNotIn('password', self.app.settings_path.read_text())

    def test_opening_another_archive_does_not_replace_current_password_early(self):
        self.load()
        current=self.app.archive
        self.app.password='current secret'
        with patch.object(self.app,'run_job') as job:
            self.app.open_path(Path(self.temp.name)/'missing.zip')
        self.assertEqual(self.app.archive,current)
        self.assertEqual(self.app.password,'current secret')
        context=job.call_args.kwargs['password_context']
        self.assertIsNone(context['password'])

    def test_password_retry_updates_pending_open_only(self):
        self.load()
        self.app.password='current secret'
        context={'password':None}
        self.app.job_password_context=context
        self.app.retry_options={'password_context':context}
        action,callback=lambda:None,lambda result:None
        self.app.retry_job=('Open',action,callback)
        self.app.events.put(('error',PasswordRequired('Password')))
        with patch('app.password_dialog',return_value='new secret'),patch.object(self.app,'run_job') as job:
            self.app.poll()
        self.assertEqual(context['password'],'new secret')
        self.assertEqual(self.app.password,'current secret')
        job.assert_called_once_with('Open',action,callback,password_context=context)

    def test_executable_copy_requires_confirmation(self):
        file=Path(self.temp.name)/'program.exe'
        file.write_bytes(b'not an executable')
        with patch('app.messagebox.askyesno',return_value=False),patch('app.os.startfile') as opening:
            self.app.open_prepared(file)
        opening.assert_not_called()

    def test_unknown_packed_size_is_not_displayed_as_zero(self):
        self.app.loaded(Path(self.temp.name)/'data.tar',[Entry('file.txt',100,None,False)])
        self.assertIn('comprimido —',self.app.summary.cget('text'))

    def test_history_selection_clipboard_and_properties(self):
        with zipfile.ZipFile(Path(self.temp.name) / 'example.zip', 'w') as archive:
            archive.writestr('folder/one.txt', b'one')
            archive.writestr('folder/two.txt', b'two')
        self.load()
        self.app.navigate('folder')
        self.assertEqual(self.app.current_folder, 'folder/')
        self.app.history_move(-1)
        self.assertEqual(self.app.current_folder, '')
        self.app.history_move(1)
        self.assertEqual(self.app.current_folder, 'folder/')
        self.app.select_all()
        self.assertEqual(set(self.app.selected_names()), {'folder/one.txt', 'folder/two.txt'})
        self.app.copy_names()
        self.assertEqual(set(self.app.clipboard_get().splitlines()), {'folder/one.txt', 'folder/two.txt'})
        with patch.object(self.app, 'show_info') as show:
            self.app.properties()
        self.assertIn('Selección: 2 elementos', show.call_args.args[2])

    def test_source_list_output_folder_and_disabled_recents(self):
        first = Path(self.temp.name) / 'first.txt'
        second = Path(self.temp.name) / 'second.txt'
        first.write_text('first')
        second.write_text('second')
        self.app.add_paths([first, second, first])
        self.assertEqual(self.app.sources, [first, second])
        self.app.tree.selection_set('0')
        self.app.remove_selected()
        self.assertEqual(self.app.sources, [second])
        self.assertTrue(first.exists())
        self.app.clear()
        self.assertEqual(self.app.sources, [])
        self.app.output = second
        with patch('app.os.startfile') as opening:
            self.app.open_output()
        opening.assert_called_once_with(second.parent)
        self.app.settings['remember_recent'] = False
        self.app.remember(second)
        self.assertEqual(self.app.settings.get('recent', []), [])

    def test_save_as_copies_archive_bytes_without_changing_original(self):
        source = Path(self.temp.name) / 'note.txt'
        source.write_text('keep this content')
        archive = create_archive([source], Path(self.temp.name) / 'original.zip')
        self.app.loaded(archive, list_archive(archive))
        target = Path(self.temp.name) / 'copy.zip'
        with patch('workflows.filedialog.asksaveasfilename', return_value=str(target)), patch.object(self.app, 'run_job') as job:
            self.app.save_archive_as()
        result = job.call_args.args[1]()
        self.assertEqual(result, target)
        self.assertEqual(target.read_bytes(), archive.read_bytes())

if __name__ == '__main__':
    unittest.main()
