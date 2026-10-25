from pathlib import Path
from branding import APP_NAME
import ctypes
import os
import sys
import subprocess
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from ui import SimpleUI
from features import Features, password_dialog
from tkinterdnd2 import TkinterDnD
from archive_core import PasswordRequired
from edit_sessions import ExternalEdits
from archive_policy import ResourceLimits, operation_limits
from workflows import BatchFailure
from archive_support import resolve_volume, error_text, DANGEROUS_EXTENSIONS
from windows_integration import open_defaults
from temporary_files import (cleanup_temporary_files, session_name_for_file,
                             pending_sessions, finish_closed_sessions, claim_temporary_file,
                             hold_archive_source, temporary_root)

from archive_core import create_zip, extract_archive, list_archive, verify_archive, prepare_file_to_open, Cancelled, checkpoint
from dialogs import monitor_area


BG = '#f1f5f9'
INK = '#172c44'
BLUE = '#1766d5'


def size_text(value):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024:
            return f'{value:,.1f} {unit}' if unit != 'B' else f'{int(value):,} B'
        value /= 1024


class App(Features, SimpleUI, TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'WinCip.ico'
        if icon.is_file():
            self.iconbitmap(str(icon))
        self.display_scale = max(1.0, self.winfo_fpixels('1i') / 96)
        left, top, right, bottom = monitor_area(self)
        width = min(self.px(840), max(1, right - left))
        height = min(self.px(580), max(1, bottom - top))
        x = left + max(0, (right - left - width) // 2)
        y = top + max(0, (bottom - top - height) // 2)
        self.geometry(f'{width}x{height}{x:+d}{y:+d}')
        self.minsize(min(self.px(720), width), min(self.px(480), height))
        self.configure(bg=BG)
        self.sources = []
        self.archive = None
        self.entries = []
        self.output = None
        self.busy = False
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.last_progress = 0
        self.buttons = []
        self._temporary_sessions = set()
        self._temporary_leases = {}
        self._source_lease = None
        self.external_edits = ExternalEdits()
        self._edit_scan_after = None
        self.init_features()
        self.setup_style()
        self.build_ui()
        self.install_features()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Control-o>', lambda _: self.open_archive() if not self.busy else None)
        self.bind('<FocusIn>', self.schedule_edit_scan, add='+')
        self.after(80, self.poll)
        self._cleanup_thread = None
        self.after(200, self.clean_temporary_files)

    def clean_temporary_files(self):
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(target=cleanup_temporary_files, daemon=True)
            self._cleanup_thread.start()

    def release_temporary_files(self):
        self.external_edits.copies.clear()
        names = set(self._temporary_sessions)
        if not names:
            return
        for name in names:
            lease = self._temporary_leases.pop(name, None)
            if lease is not None:
                lease.close()
        cleanup_temporary_files(min_age_seconds=0, session_names=names)
        pending = pending_sessions(names)
        if pending:
            command = [sys.executable]
            if not getattr(sys, 'frozen', False):
                command.append(str(Path(__file__).resolve()))
            command.extend(['--cleanup-temporaries', *pending])
            try:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, close_fds=True,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                threading.Thread(target=process.wait, daemon=True).start()
            except OSError:
                # If Windows cannot launch the helper, retain responsibility in
                # this process until the external viewer releases the copies.
                threading.Thread(target=finish_closed_sessions, args=(pending,),
                                 kwargs={'cache_root': temporary_root()}, daemon=False).start()
        self._temporary_sessions.difference_update(names)
        if self.output is not None and session_name_for_file(self.output) in names:
            self.output = None
            self.output_button.pack_forget()

    def px(self, value):
        return round(value * self.display_scale)

    def render_rows(self):
        Features.render_rows(self)

    def clear(self, _checked=False):
        if self.busy:
            return
        if not _checked and self.protect_external_edits(lambda: self.clear(_checked=True)):
            return
        self.retry_job = None
        self.retry_options = {}
        self.job_password_context = None
        self.batch_secrets = {}
        self.folder_history = ['']
        self.folder_index = 0
        self.release_temporary_files()
        self.release_source()
        self.title(APP_NAME)
        self.sources = []
        self.archive = None
        self.entries = []
        self.password = None
        self.current_folder = ""
        self.search.set('')
        self.heading.configure(text='')
        self.subtitle.configure(text='')
        self.render_rows()

    def add_paths(self, paths, force_new=False):
        if not paths:
            return
        if self.archive:
            if self.editable() and not force_new:
                answer=messagebox.askyesnocancel('Añadir archivos','¿Añadir o actualizar estos archivos en el comprimido abierto?\n\nElige No para preparar un comprimido nuevo.',parent=self)
                if answer is None:
                    return
                if answer:
                    self.addition_policy(paths)
                    return
            def prepare_new():
                self.clear(_checked=True)
                self.add_paths(paths, force_new=True)
            if self.protect_external_edits(prepare_new):
                return
            self.clear(_checked=True)
        for path in map(Path, paths):
            if any(path == existing or path.is_relative_to(existing) for existing in self.sources):
                continue
            self.sources = [existing for existing in self.sources if not existing.is_relative_to(path)]
            self.sources.append(path)
        self.heading.configure(text='Archivos para comprimir')
        self.subtitle.configure(text='ZIP · 7Z · TAR · TAR.GZ · TAR.BZ2 · TAR.XZ')
        self.render_rows()

    def add_files(self):
        self.add_paths(filedialog.askopenfilenames(title='Selecciona los archivos'))

    def add_folder(self):
        path = filedialog.askdirectory(title='Selecciona una carpeta')
        if path:
            self.add_paths([path])

    def remove_selected(self):
        if self.archive:
            messagebox.showinfo('Contenido del comprimido', 'Para crear un ZIP nuevo, añade archivos o carpetas desde tu equipo.')
            return
        selected = set(map(int, self.tree.selection()))
        self.sources = [path for i, path in enumerate(self.sources) if i not in selected]
        self.render_rows()

    def open_archive(self):
        path = filedialog.askopenfilename(title='Abrir comprimido', filetypes=[('Archivos comprimidos', '*.zip *.rar *.7z *.tar *.gz *.bz2 *.xz *.tgz *.tbz2 *.txz *.001'), ('Todos los archivos', '*.*')])
        if path:
            self.open_path(path)

    def open_path(self, path, keep_password=False, on_loaded=None, password_context=None, _checked=False):
        if self.busy:
            return
        requested=Path(path).absolute()
        if not _checked and requested != self.archive and self.protect_external_edits(
                lambda: self.open_path(path, keep_password, on_loaded, password_context, _checked=True)):
            return
        context=password_context if password_context is not None else {'password':self.password if keep_password else None}
        self.password_target=requested
        def load():
            checkpoint(self.cancel)
            actual=resolve_volume(requested)
            lease=hold_archive_source(actual)
            try:
                entries=list_archive(actual,self.cancel,context['password'])
                checkpoint(self.cancel)
                return actual,entries,lease
            except BaseException:
                if lease is not None: lease.close()
                raise
        def accept(result):
            actual,entries,lease=result
            self.loaded(actual,entries,source_lease=lease)
            self.password=context['password']
            self.password_target=actual
            if on_loaded is not None: self.after_idle(on_loaded)
        self.run_job('Leyendo contenido…',load,accept,password_context=context)

    def default_settings(self):
        try:
            open_defaults()
        except Exception as exc:
            messagebox.showerror('Aplicación predeterminada', str(exc))

    def release_source(self):
        if self._source_lease is not None:
            self._source_lease.close()
            self._source_lease = None

    def loaded(self, path, entries, *, source_lease=None):
        lease = source_lease if source_lease is not None else hold_archive_source(path)
        try:
            if self.archive != Path(path) or not self.external_edits.copies:
                self.release_temporary_files()
        except BaseException:
            if lease is not None:
                lease.close()
            raise
        self.release_source()
        self._source_lease = lease
        self.sources = []
        self.archive = Path(path)
        self.remember(path)
        self.current_folder = ""
        self.folder_history = ['']
        self.folder_index = 0
        self.entries = entries
        self.title(f'{self.archive.name} — {APP_NAME}')
        self.heading.configure(text=self.archive.name)
        self.subtitle.configure(text=str(self.archive.parent))
        self.search.set('')
        self.render_rows()

    def compress(self):
        Features.compress(self)

    def extract(self):
        self.extract_options()

    def verify(self):
        self.run_job('Verificando lectura…', lambda: verify_archive(self.archive, self.cancel, self.report, password=self.password),
                     lambda result: messagebox.showinfo('Verificación completada', result))

    def open_selected(self, event=None):
        if self.busy or not self.archive:
            return
        if event is not None and getattr(event, 'num', None) == 1:
            if self.tree.identify_region(event.x, event.y) not in ('cell', 'tree'):
                return
            row = self.tree.identify_row(event.y)
            if not row:
                return
            self.tree.selection_set(row)
        selected = self.tree.selection()
        if len(selected) != 1:
            return
        entry = self.row_entries[selected[0]]
        if entry.directory:
            self.navigate(entry.name.replace('\\','/').removeprefix('./'))
            return
        source = self.archive
        existing = self.external_edits.find(source, entry.name)
        if existing:
            self.open_prepared(existing)
            return
        def prepare():
            from archive_core import ArchiveError, archive_version
            version = archive_version(source)
            result = prepare_file_to_open(source, entry.name, self.cancel, self.report, password=self.password)
            try:
                if self.editable():
                    self.external_edits.track(source, entry.name, result, self.cancel)
                    if archive_version(source) != version:
                        raise ArchiveError('El comprimido cambió durante la apertura. Vuelve a abrirlo.')
            except BaseException:
                self.external_edits.copies.pop((source, entry.name), None)
                name = session_name_for_file(result)
                if name:
                    cleanup_temporary_files(min_age_seconds=0, session_names={name})
                raise
            return result
        self.run_job('Abriendo archivo…',
                     prepare,
                     self.open_prepared)

    def open_prepared(self, result):
        name = session_name_for_file(result)
        if name is not None:
            lease = claim_temporary_file(result)
            previous = self._temporary_leases.get(name)
            self._temporary_leases[name] = lease
            if previous is not None:
                previous.close()
            self._temporary_sessions.add(name)
        self.output = Path(result)
        self.output_button.configure(state='normal')
        self.output_button.pack(side='right')
        if self.output.suffix.lower() in DANGEROUS_EXTENSIONS:
            if not messagebox.askyesno('Abrir archivo ejecutable',
                f'{self.output.name} puede ejecutar instrucciones en tu equipo.\n\nÁbrelo solo si confías en su origen. ¿Quieres continuar?',parent=self):
                self.status.set('Apertura cancelada')
                return
        try:
            os.startfile(str(result))
            self.status.set(f'Copia temporal · {self.output.name}')
        except OSError as exc:
            self.status.set('No se pudo abrir el archivo')
            messagebox.showerror('Abrir archivo', f'{exc}\n\nEl archivo está disponible en:\n{result}')

    def schedule_edit_scan(self, event=None):
        if self._edit_scan_after is not None:
            self.after_cancel(self._edit_scan_after)
        self._edit_scan_after = self.after(700, self.scan_external_edits_on_return)

    def scan_external_edits_on_return(self):
        self._edit_scan_after = None
        if (not self.busy and self.grab_current() is None and self.focus_get() is not None
                and self.external_edits.needs_scan()):
            self.update_external_edits()

    def protect_external_edits(self, continuation):
        if not self.external_edits.copies:
            return False
        self.update_external_edits(continuation=continuation)
        return True

    def update_external_edits(self, continuation=None):
        if self.busy:
            return
        def scanned(copies):
            if not copies:
                if continuation:
                    continuation()
                else:
                    self.status.set('No hay cambios pendientes de editores externos')
                return
            names = '\n'.join(copy.member for copy in copies[:8])
            text = f'Hay cambios en {len(copies)} archivo(s):\n\n{names}\n\n¿Actualizar el comprimido con estos cambios?'
            text += ('\n\nSí: guardar y continuar. No: descartar las copias y continuar. Cancelar: volver a la app.'
                     if continuation else '\n\nSí: guardar. No o Cancelar: conservar las copias para después.')
            answer = messagebox.askyesnocancel('Cambios del editor externo', text, parent=self)
            if answer is None or (answer is False and continuation is None):
                return
            if answer is False:
                continuation()
                return
            context = {'password': self.password}
            def saved(result):
                self.password = context['password']
                next_step = (lambda: self.update_external_edits(continuation=continuation)) if continuation else None
                self.open_path(result, password_context=context, on_loaded=next_step)
            self.run_job('Guardando cambios del editor…', lambda: self.external_edits.commit(copies, self.cancel,
                         self.report, password=context['password'], backup=self.settings.get('backup_edits', True)),
                         saved, password_context=context)
        self.run_job('Comprobando cambios de editores…', lambda: self.external_edits.changed(self.cancel), scanned)

    def report(self, done, total, label):
        now = time.monotonic()
        if now - self.last_progress > .08 or done == total:
            self.last_progress = now
            self.events.put(('progress', (done, total, label)))

    def run_job(self, label, operation, callback, *, password_context=None):
        if self.busy:
            return
        self.busy = True
        if not getattr(operation,'_batch',False):
            self.batch_report=None
            self.batch_password_path=None
        self.retry_job = (label, operation, callback)
        self.retry_options = {'password_context':password_context} if password_context is not None else {}
        self.job_password_context = password_context
        self.progress_sample = None
        self.batch_caption = ''
        self.job_start = time.monotonic()
        self.cancel.clear()
        self.status.set(label)
        self.progress.configure(value=0, mode='indeterminate')
        self.progress.start(12)
        self.show_progress()
        for button in self.buttons:
            button.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        limits = ResourceLimits(self.settings.get('max_entries', 100_000), self.settings.get('max_gib', 50) * 1024**3)
        def worker():
            try:
                with operation_limits(limits):
                    result = operation()
                self.events.put(('success', (callback, result)))
            except Exception as exc:
                self.events.put(('error', exc))
        threading.Thread(target=worker, daemon=True).start()

    def finish_job(self):
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode='determinate')
        for button in self.buttons:
            button.configure(state='normal')
        self.hide_progress()
        self.cancel_button.configure(state='disabled')
        self.update_actions()

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'progress':
                    done,total,label=data
                    if total<=0:
                        self.progress.stop()
                        self.progress.configure(mode='indeterminate')
                        self.progress.start(12)
                        self.progress_sample=None
                        self.status.set(label)
                    else:
                        self.progress.stop()
                        self.progress.configure(mode='determinate',value=100*done/total)
                        now=time.monotonic()
                        sample=getattr(self,'progress_sample',None)
                        if sample is None or sample[1]!=total or done<sample[0]:
                            self.progress_sample=(done,total,now)
                            rate=''
                        else:
                            speed=(done-sample[0])/max(.01,now-sample[2])
                            rate=f' · {size_text(speed)}/s · {(total-done)/speed:.0f}s' if speed>0 and done<total else ''
                        prefix=getattr(self,'batch_caption','')
                        text=label if done==total else f'{100*done/total:.0f}%{rate} · {label[:55]}'
                        self.status.set((prefix+' · ' if prefix else '')+text)
                elif kind == 'success':
                    self.finish_job()
                    self.retry_job=None
                    self.retry_options={}
                    self.job_password_context=None
                    self.batch_secrets={}
                    self.progress.configure(value=100)
                    self.status.set('Operación completada')
                    callback,result=data
                    callback(result)
                elif kind == 'batch':
                    self.batch_caption=data
                    self.status.set(data)
                else:
                    self.finish_job()
                    if isinstance(data,PasswordRequired):
                        self.status.set(str(data))
                        secret=password_dialog(self)
                        if secret is not None:
                            if getattr(self,'batch_password_path',None):
                                self.batch_secrets[self.batch_password_path]=secret
                                self.batch_password_path=None
                            elif getattr(self,'job_password_context',None) is not None:
                                self.job_password_context['password']=secret
                            else:
                                self.password=secret
                            self.run_job(*self.retry_job,**getattr(self,'retry_options',{}))
                        else:
                            self.batch_password_path=None
                            self.retry_job=None
                            self.retry_options={}
                            self.job_password_context=None
                            self.batch_secrets={}
                            self.status.set('Operación cancelada')
                            if getattr(self,'batch_report',None): self.batch_summary()
                        continue
                    if isinstance(data,BatchFailure):
                        action=self.batch_failure_action(data)
                        if action=='skip': self.batch_skip()
                        if action in ('skip','retry'):
                            self.run_job(*self.retry_job)
                        else:
                            self.retry_job=None
                            self.batch_secrets={}
                            self.status.set('Lote detenido')
                            self.batch_summary()
                        continue
                    self.retry_job=None
                    self.retry_options={}
                    self.job_password_context=None
                    self.batch_secrets={}
                    self.progress.configure(value=0)
                    self.status.set('Operación cancelada' if isinstance(data,Cancelled) else 'No se pudo completar la operación')
                    if isinstance(data,Cancelled):
                        if getattr(self,'batch_report',None): self.batch_summary()
                    else:
                        messagebox.showerror(APP_NAME,error_text(data),parent=self)
        except queue.Empty:
            pass
        except Exception as exc:
            self.finish_job()
            self.status.set('No se pudo completar la operación')
            messagebox.showerror(APP_NAME,error_text(exc),parent=self)
        finally:
            try:
                self.after(80, self.poll)
            except tk.TclError:
                pass

    def completed(self, result):
        self.output = Path(result)
        self.output_button.configure(state='normal')
        self.output_button.pack(side='right')
        self.status.set(f'Guardado en {result}')

    def open_output(self):
        if self.output:
            os.startfile(self.output if self.output.is_dir() else self.output.parent)

    def close(self, _checked=False):
        if self.busy:
            messagebox.showinfo('Operación en curso', 'Pulsa Cancelar y espera a que termine antes de cerrar.')
            return
        if not _checked and self.protect_external_edits(lambda: self.close(_checked=True)):
            return
        self.password=None
        self.retry_job=None
        self.batch_secrets={}
        self.release_temporary_files()
        self.release_source()
        self.update_idletasks()
        for job in self.tk.call('after', 'info'):
            self.after_cancel(job)
        self.destroy()


if __name__ == '__main__':
    if sys.getwindowsversion().build < 10240:
        ctypes.windll.user32.MessageBoxW(None,
            'WinCip Compresor requiere Windows 10 u 11 de 64 bits.',
            'WinCip Compresor', 0x10)
        sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1] in ('--register-shell', '--unregister-shell'):
        from windows_integration import register, unregister, install_modern_menu
        executable = Path(sys.executable if getattr(sys, 'frozen', False) else Path(__file__).with_name('WinCip.exe'))
        try:
            if sys.argv[1] == '--register-shell':
                register(executable)
                if '--modern' in sys.argv[2:]:
                    install_modern_menu(executable)
            else:
                unregister(executable)
        except Exception as error:
            sys.exit(1)
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == '--cleanup-temporaries':
        finish_closed_sessions(sys.argv[2:])
        sys.exit(0)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    app = App()
    if len(sys.argv) > 2 and sys.argv[1] == '--self-test':
        app.withdraw()
        try:
            from diagnostics import smoke_report
            smoke_report(app, sys.argv[2])
        except Exception as exc:
            import json
            import traceback
            Path(sys.argv[2]).write_text(json.dumps({
                'ok': False, 'error': str(exc), 'traceback': traceback.format_exc()
            }, ensure_ascii=False), encoding='utf-8')
            app.destroy()
            sys.exit(1)
        app.destroy()
        sys.exit(0)
    args = sys.argv[1:]
    if args:
        if args[0] == '--compress':
            def shell_compress():
                app.add_paths(args[1:])
                app.after_idle(app.compress)
            app.after(100, shell_compress)
        elif args[0] == '--extract' and len(args) > 1:
            def shell_extract_prompt():
                if len(args) == 2:
                    app.open_path(args[1], on_loaded=app.extract)
                else:
                    parent = filedialog.askdirectory(title='Destino de los comprimidos')
                    if parent:
                        app.extract_paths(args[1:], destination=parent)
            app.after(100, shell_extract_prompt)
        elif args[0] in ('--extract-here', '--extract-folder') and len(args) > 1:
            app.after(100, lambda: app.extract_paths(args[1:], here=args[0] == '--extract-here'))
        else:
            app.after(100, lambda: app.open_path(args[0]))
    app.mainloop()
