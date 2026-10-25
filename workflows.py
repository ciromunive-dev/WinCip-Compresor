"""Archive workflows and user preferences."""
from pathlib import Path, PurePosixPath
from branding import APP_NAME
import datetime
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dialogs import Modal, password_dialog, WHITE, INK, MUTED
from archive_core import (ArchiveError, Cancelled, PasswordRequired, checkpoint, create_archive,
                          modify_archive, convert_archive, list_archive, extract_archive, extract_into)
from archive_support import resolve_volume, archive_stem, error_text, volume_key
from archive_formats import format_for_path, available_create_formats, can_edit

VERSION = '3.2.0'
LEVELS = {'Sin compresión': 0, 'Rápida': 1, 'Equilibrada': 6, 'Máxima': 9}

class BatchFailure(Exception):
    def __init__(self, path, cause):
        self.path, self.cause = path, cause
        super().__init__(error_text(cause))

class Workflows:
    def editable(self):
        return bool(self.archive and can_edit(self.archive))

    def supports_password(self):
        fmt = format_for_path(self.archive) if self.archive else None
        return bool(fmt and fmt.password)

    def navigate(self, folder='', record=True):
        if self.busy or not self.archive:
            return
        folder = folder.replace('\\', '/').strip('/')
        if folder:
            parts = folder.split('/')
            if (any(part in ('', '.', '..') for part in parts)
                    or (len(folder) > 1 and folder[0].isalpha() and folder[1] == ':')):
                messagebox.showerror('Ruta', 'Ruta interna no válida.', parent=self)
                return
            folder += '/'
            if not any(e.name.replace('\\', '/').removeprefix('./').startswith(folder) for e in self.entries):
                messagebox.showinfo('Ruta', 'No existe esa carpeta dentro del comprimido.', parent=self)
                return
        if record and folder != self.current_folder:
            self.folder_history = self.folder_history[:self.folder_index + 1] + [folder]
            self.folder_index += 1
        self.current_folder = folder
        self.search.set('')
        self.render_rows()

    def history_move(self, amount):
        if self.busy:
            return
        index = self.folder_index + amount
        if 0 <= index < len(self.folder_history):
            self.folder_index = index
            self.navigate(self.folder_history[index], record=False)

    def select_all(self, event=None):
        if event and event.widget.winfo_class() in ('Entry', 'TEntry', 'Text', 'TCombobox'):
            return
        self.tree.selection_set(self.tree.get_children())
        return 'break'

    def copy_names(self):
        names = self.selected_names()
        if names:
            self.clipboard_clear()
            self.clipboard_append('\n'.join(names))

    def show_info(self, title, subtitle, text):
        window = Modal(self, title, subtitle)
        area = tk.Text(window.body, height=12, width=45, wrap='word', bg=WHITE, fg=INK,
                       relief='flat', font=('Segoe UI', 10), padx=2, pady=6)
        area.pack(fill='both', expand=True)
        area.insert('1.0', text)
        area.configure(state='disabled')
        window.actions('Cerrar', window.destroy)
        window.present()

    def properties(self):
        if not self.archive:
            return
        from app import size_text
        names = self.selected_names()
        entries = [self.row_entries[i] for i in self.tree.selection() if i in self.row_entries]
        if len(entries) == 1:
            e = entries[0]
            date = datetime.datetime.fromtimestamp(e.mtime).strftime('%d/%m/%Y %H:%M:%S') if e.mtime else 'No disponible'
            text = f'Ruta: {e.name}\nTipo: {"Carpeta" if e.directory else "Archivo"}\nTamaño: {size_text(e.size)}\nComprimido: {size_text(e.packed) if e.packed is not None else "No disponible"}\nModificado: {date}\nCifrado: {"Sí" if e.encrypted else "No"}\nMétodo: {e.method or "No disponible"}'
            self.show_info('Propiedades', self.archive.name, text)
        else:
            encrypted = any(e.encrypted for e in self.entries)
            text = f'Ubicación: {self.archive}\nFormato: {self.archive.suffix.upper()}\nTamaño en disco: {size_text(self.archive.stat().st_size)}\nEntradas: {len(self.entries)}\nTamaño original: {size_text(sum(e.size for e in self.entries))}\nContiene cifrado: {"Sí" if encrypted else "No"}\nSelección: {len(names)} elementos'
            self.show_info('Propiedades del comprimido', self.archive.name, text)

    def preferences(self):
        if self.busy:
            return
        window = Modal(self, 'Preferencias', 'Opciones predeterminadas para tus operaciones.')
        recent = tk.BooleanVar(value=self.settings.get('remember_recent', True))
        verify = tk.BooleanVar(value=self.settings.get('verify_created', True))
        backup = tk.BooleanVar(value=self.settings.get('backup_edits', True))
        window.check('Recordar comprimidos recientes', recent)
        window.check('Verificar después de crear', verify)
        window.check('Crear respaldo antes de editar', backup)
        window.label('Formato predeterminado')
        selected_format = self.settings.get('format', 'zip')
        fmt = tk.StringVar(value=selected_format if selected_format in available_create_formats() else 'zip')
        window.select(fmt, available_create_formats())
        window.label('Nivel de compresión')
        level = tk.StringVar(value=next((n for n, v in LEVELS.items() if v == self.level_value.get()), 'Equilibrada'))
        window.select(level, list(LEVELS))
        window.label('Al actualizar archivos existentes')
        conflict = tk.StringVar(value=self.settings.get('edit_conflict', 'Reemplazar'))
        window.select(conflict, ['Reemplazar', 'Omitir', 'Solo más recientes'])
        window.label('Entradas máximas por operación · 0 sin tope')
        max_entries = tk.StringVar(value=str(self.settings.get('max_entries', 100_000)))
        window.entry(max_entries)
        window.label('Contenido descomprimido máximo en GiB · 0 sin tope')
        max_gib = tk.StringVar(value=str(self.settings.get('max_gib', 50)))
        window.entry(max_gib)
        tk.Button(window.body, text='Borrar historial de recientes', command=self.clear_recent,
                  bg=WHITE, fg='#3266e3', relief='flat', cursor='hand2', font=('Segoe UI', 10)).pack(anchor='w', pady=10)
        def accept():
            try:
                entries, gib = int(max_entries.get()), int(max_gib.get())
                if entries < 0 or gib < 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror('Límites', 'Escribe enteros mayores o iguales a cero.', parent=window)
                return
            self.settings.update(remember_recent=recent.get(), verify_created=verify.get(), backup_edits=backup.get(),
                                 format=fmt.get(), edit_conflict=conflict.get(), max_entries=entries, max_gib=gib)
            if not recent.get():
                self.settings['recent'] = []
            self.level_value.set(LEVELS[level.get()])
            self.save_settings()
            window.destroy()
        window.actions('Guardar', accept)
        window.present()

    def clear_recent(self):
        self.settings['recent'] = []
        self.save_settings()

    def about(self):
        self.show_info('Acerca de ' + APP_NAME, 'Versión ' + VERSION,
                       'Herramienta local para comprimir y extraer archivos.\n\nCrea y edita ZIP, 7Z y TAR comprimidos. RAR se habilita con su codificador instalado.\n\nUtiliza el motor de 7-Zip y bibliotecas Python.\n\nMenú Ayuda: instrucciones de las operaciones y sus límites.')

    def help(self):
        self.show_info('Ayuda', 'Primeros pasos',
            'Abrir: selecciona o arrastra un comprimido.\n\nCrear: añade archivos y elige formato, nivel, filtros y contraseña. TAR no admite contraseña.\n\nExtraer selección: selecciona archivos o carpetas y elige el destino.\n\nEdición de comprimidos: añade, actualiza, elimina, renombra o crea carpetas. Activa el respaldo para conservar el original como .bak.\n\nContraseña: puedes establecerla, cambiarla o quitarla conociendo la actual.\n\nVolúmenes: guarda todas las partes juntas; al seleccionar cualquier parte se busca la primera.\n\nAlt+Izquierda/Derecha: historial. Alt+Arriba: subir. Ctrl+E: extraer selección. F2: renombrar.\n\nPreferencias: presupuestos de entradas y GiB ajustables; 0 sin tope. Editores externos: confirma sus cambios al volver. Respaldos: usa Restaurar respaldo. No se crean enlaces ni se restauran ACL de Windows.')

    def compress(self):
        if self.busy or not self.sources:
            return
        window = Modal(self, 'Crear comprimido', 'Formato, protección y contenido del resultado.')
        selected_format = self.settings.get('format', 'zip')
        fmt = tk.StringVar(value=selected_format if selected_format in available_create_formats() else 'zip')
        window.label('Formato')
        format_field = window.select(fmt, available_create_formats())
        window.label('Nivel de compresión')
        level = tk.StringVar(value=next((n for n,v in LEVELS.items() if v == self.level_value.get()), 'Equilibrada'))
        level_field = window.select(level, list(LEVELS))
        protected, hidden = tk.BooleanVar(), tk.BooleanVar(value=True)
        def changed(*_):
            archive_format = fmt.get()
            password_check.configure(state='disabled' if archive_format.startswith('tar') else 'normal')
            names_check.configure(state='normal' if protected.get() and archive_format in ('7z', 'rar') else 'disabled')
            volume_field.configure(state='disabled' if archive_format.startswith('tar') else 'normal')
            level_field.configure(state='disabled' if archive_format == 'tar' else 'readonly')
        password_check = window.check('Proteger con contraseña', protected, changed)
        names_check = window.check('Ocultar nombres de archivos (7Z/RAR)', hidden)
        volume = tk.StringVar(value='0')
        window.label('Volumen en MB · 0 = archivo único')
        volume_field = window.entry(volume)
        verified = tk.BooleanVar(value=self.settings.get('verify_created', True))
        window.check('Verificar antes de guardar', verified)
        filters = {'include': '', 'exclude': ''}
        def edit_filters():
            modal = Modal(window, 'Filtros de archivos', 'Patrones separados por punto y coma. Ejemplo: *.pdf; *.txt')
            include, exclude = tk.StringVar(value=filters['include']), tk.StringVar(value=filters['exclude'])
            modal.label('Incluir · vacío incluye todo')
            entry = modal.entry(include)
            modal.label('Excluir · archivos o carpetas')
            modal.entry(exclude)
            def save():
                filters.update(include=include.get(), exclude=exclude.get())
                modal.destroy()
            modal.actions('Aplicar', save)
            modal.present(entry)
        tk.Button(window.body, text='Elegir filtros de inclusión y exclusión…', command=edit_filters,
                  bg=WHITE, fg='#3266e3', relief='flat', cursor='hand2', font=('Segoe UI', 10)).pack(anchor='w', pady=8)
        fmt.trace_add('write', changed)
        changed()
        def accept():
            archive_format = fmt.get()
            try:
                mb = 0 if archive_format.startswith('tar') else int(volume.get())
                if mb < 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror('Volúmenes', 'Introduce un entero mayor o igual a cero.', parent=window)
                return
            secure = protected.get() and not archive_format.startswith('tar')
            secret = password_dialog(window, confirm=True, archive_format=archive_format) if secure else None
            if secure and secret is None:
                return
            destination = filedialog.asksaveasfilename(parent=window, title='Guardar comprimido', defaultextension='.' + archive_format,
                          initialfile='Archivo.' + archive_format, filetypes=[(archive_format.upper(), '*.' + archive_format)])
            if not destination:
                return
            chosen_level, hide = LEVELS[level.get()], hidden.get()
            verify = verified.get()
            patterns = {key: tuple(p.strip() for p in text.split(';') if p.strip()) for key, text in filters.items()}
            self.settings.update(format=archive_format, verify_created=verify)
            self.level_value.set(chosen_level)
            self.save_settings()
            sources = list(self.sources)
            window.destroy()
            self.run_job('Comprimiendo…', lambda: create_archive(sources, destination, chosen_level, self.cancel, self.report,
                         format=archive_format, password=secret, hide_names=hide, volume_mb=mb, verify=verify,
                         overwrite=Path(destination).is_file(), **patterns), self.completed)
        window.actions('Continuar', accept)
        window.present(format_field)

    def edit_zip(self, **options):
        if self.busy or not self.editable():
            return
        source = self.archive
        secret = options.get('new_password', self.password)
        options.setdefault('backup', self.settings.get('backup_edits', True))
        def done(result):
            context = {'password': secret}
            self.open_path(result, password_context=context)
        self.run_job('Actualizando comprimido…', lambda: modify_archive(source, self.cancel, self.report,
                     password=self.password, **options), done)

    def addition_policy(self, paths):
        if not paths:
            return
        window = Modal(self, 'Actualizar comprimido', 'Elige qué hacer si un archivo ya existe.')
        choice = tk.StringVar(value=self.settings.get('edit_conflict', 'Reemplazar'))
        field = window.select(choice, ['Reemplazar', 'Omitir', 'Solo más recientes'])
        def accept():
            self.settings['edit_conflict'] = choice.get()
            self.save_settings()
            conflict = {'Reemplazar':'replace','Omitir':'skip','Solo más recientes':'newer'}[choice.get()]
            window.destroy()
            self.edit_zip(additions=paths, folder=self.current_folder, conflict=conflict)
        window.actions('Actualizar', accept)
        window.present(field)

    def add_to_zip(self):
        if not self.busy:
            self.addition_policy(filedialog.askopenfilenames(title='Añadir o actualizar archivos'))

    def add_folder_to_zip(self):
        if not self.busy:
            path = filedialog.askdirectory(title='Añadir o actualizar carpeta')
            if path:
                self.addition_policy([path])

    def new_folder(self):
        if self.busy or not self.editable():
            return
        from tkinter import simpledialog
        name = simpledialog.askstring('Crear carpeta', 'Nombre de la carpeta:', parent=self)
        if name:
            self.edit_zip(new_folder=name, folder=self.current_folder)

    def change_password(self):
        if self.busy or not self.supports_password():
            return
        window = Modal(self, 'Contraseña del comprimido', 'Reconstruiremos el archivo y verificaremos el resultado.')
        choice = tk.StringVar(value='Establecer o cambiar contraseña')
        field = window.select(choice, ['Establecer o cambiar contraseña', 'Quitar contraseña'])
        def accept():
            secret = password_dialog(window, confirm=True, archive_format=self.archive.suffix[1:].lower()) if choice.get().startswith('Establecer') else None
            if choice.get().startswith('Establecer') and secret is None:
                return
            if secret is None and not messagebox.askyesno('Quitar contraseña', 'El resultado quedará sin protección. ¿Continuar?', parent=window):
                return
            window.destroy()
            self.edit_zip(new_password=secret)
        window.actions('Continuar', accept)
        window.present(field)

    def restore_archive_backup(self):
        if self.busy or not self.archive:
            return
        from archive_core import list_backups, restore_backup
        try:
            backups = list_backups(self.archive)
        except OSError as error:
            messagebox.showerror('Respaldos', str(error), parent=self)
            return
        if not backups:
            messagebox.showinfo('Respaldos', 'No hay respaldos de este comprimido en su carpeta.', parent=self)
            return
        window = Modal(self, 'Restaurar respaldo', 'Se verificará la copia y se guardará un respaldo del estado actual.')
        labels = {f'{path.name} · {datetime.datetime.fromtimestamp(path.stat().st_mtime):%d/%m/%Y %H:%M:%S}': path for path in backups}
        choice = tk.StringVar(value=next(iter(labels)))
        field = window.select(choice, tuple(labels))
        def accept():
            source, backup = self.archive, labels[choice.get()]
            context = {'password': self.password}
            window.destroy()
            self.run_job('Restaurando respaldo…', lambda: restore_backup(source, backup, self.cancel, self.report,
                         password=context['password']),
                         lambda result: self.open_path(result, password_context=context), password_context=context)
        window.actions('Restaurar', accept)
        window.present(field)

    def edit_comment(self):
        if self.busy or not self.archive or self.archive.suffix.lower() != '.zip':
            return
        from archive_core import zip_comment
        try:
            comment = zip_comment(self.archive).decode('utf-8', errors='replace')
        except (OSError, ValueError) as error:
            messagebox.showerror('Comentario ZIP', str(error), parent=self)
            return
        window = Modal(self, 'Comentario ZIP', 'El comentario es visible aunque los archivos estén cifrados.')
        area = tk.Text(window.body, height=10, width=48, wrap='word', font=('Segoe UI', 10))
        area.pack(fill='both', expand=True, pady=8)
        area.insert('1.0', comment)
        def accept():
            value = area.get('1.0', 'end-1c').encode('utf-8')
            if len(value) > 65535:
                messagebox.showerror('Comentario ZIP', 'El máximo es 65 535 bytes en UTF-8.', parent=window)
                return
            window.destroy()
            self.edit_zip(comment=value)
        window.actions('Guardar', accept)
        window.present(area)

    def save_archive_as(self):
        if self.busy or not self.archive:
            return
        extension = '.tar' + self.archive.suffix if self.archive.name.lower().endswith(('.tar.gz','.tar.bz2','.tar.xz')) else self.archive.suffix
        destination = filedialog.asksaveasfilename(title='Guardar copia del comprimido', initialfile=self.archive.name, defaultextension=extension)
        if not destination:
            return
        source, secret = self.archive, self.password
        def operation():
            from workspaces import archive_workspace
            from archive_core import copy_stream
            from archive_support import propagate_zone
            target = Path(destination).absolute()
            if target == source:
                raise ArchiveError('Elige otro nombre para la copia.')
            import re
            if re.search(r'\.\d{3,}$|\.part\d+\.rar$',source.name,re.I) or source.with_suffix('.z01').exists() or source.with_suffix('.r00').exists():
                raise ArchiveError('Para guardar un conjunto de volúmenes en un solo archivo utiliza Convertir.')
            with archive_workspace(prefix='.archivofacil-', dir=target.parent) as temp:
                stage = Path(temp) / target.name
                before = source.stat()
                size = before.st_size
                with source.open('rb') as src, stage.open('xb') as dst:
                    copy_stream(src,dst,self.cancel,self.report,0,size,source.name,size)
                propagate_zone(source,stage)
                current=source.stat()
                if (current.st_mtime_ns,current.st_size)!=(before.st_mtime_ns,before.st_size):
                    raise ArchiveError('El comprimido cambió durante la copia. Vuelve a intentarlo.')
                checkpoint(self.cancel)
                os.replace(stage,target)
            return target
        self.run_job('Guardando copia…', operation, self.completed)

    def convert(self):
        if self.busy or not self.archive:
            return
        window = Modal(self, 'Convertir comprimido', 'El original se conservará. Elige el formato de la nueva copia.')
        fmt = tk.StringVar(value='zip')
        field = window.select(fmt, available_create_formats())
        secure = tk.BooleanVar()
        check = window.check('Proteger la nueva copia con contraseña', secure)
        fmt.trace_add('write', lambda *_: check.configure(state='disabled' if fmt.get().startswith('tar') else 'normal'))
        def accept():
            chosen = fmt.get()
            secret = password_dialog(window, confirm=True, archive_format=chosen) if secure.get() and not chosen.startswith('tar') else None
            if secure.get() and not chosen.startswith('tar') and secret is None:
                return
            destination = filedialog.asksaveasfilename(parent=window, title='Guardar conversión', initialfile=archive_stem(self.archive) + '.' + chosen, defaultextension='.'+chosen)
            if destination:
                source = self.archive
                window.destroy()
                self.run_job('Convirtiendo…', lambda: convert_archive(source,destination,self.cancel,self.report,password=self.password,
                             format=chosen,new_password=secret,level=self.level_value.get()), self.completed)
        window.actions('Continuar', accept)
        window.present(field)

    def preview(self):
        if self.busy or not self.archive:
            return
        names = self.selected_names()
        if len(names) != 1:
            return
        entry = self.row_entries[self.tree.selection()[0]]
        if entry.directory:
            return
        images = {'.png','.jpg','.jpeg','.gif','.bmp','.webp','.ico'}
        texts = {'.txt','.md','.csv','.json','.xml','.ini','.log','.py','.js','.css','.html','.yaml','.yml','.toml','.svg'}
        suffix = Path(entry.name).suffix.lower()
        if suffix not in images | texts or entry.size > 10 * 1024**2:
            messagebox.showinfo('Vista previa', 'Disponible para texto e imágenes de hasta 10 MB. No se ejecutará contenido activo.', parent=self)
            return
        from archive_core import prepare_file_to_open
        def show(path):
            from temporary_files import session_name_for_file, claim_temporary_file
            name = session_name_for_file(path)
            if name:
                self._temporary_sessions.add(name)
                self._temporary_leases[name] = claim_temporary_file(path)
            window = Modal(self, 'Vista previa', entry.name)
            try:
                if suffix in images:
                    from PIL import Image, ImageTk
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter('error', Image.DecompressionBombWarning)
                        with Image.open(path) as raw:
                            if raw.width * raw.height > 25_000_000:
                                raise ArchiveError('La imagen supera el límite de 25 millones de píxeles.')
                            raw.thumbnail((window.px(500),window.px(350)))
                            picture = ImageTk.PhotoImage(raw.copy(), master=window)
                    label = tk.Label(window.body,image=picture,bg=WHITE)
                    label.image = picture
                    label.pack()
                else:
                    with Path(path).open('rb') as stream:
                        data = stream.read(1024**2)
                    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
                        text = data.decode('utf-16', errors='replace')
                    else:
                        try:
                            text = data.decode('utf-8-sig')
                        except UnicodeDecodeError:
                            text = data.decode('cp1252', errors='replace')
                    area = tk.Text(window.body,width=65,height=18,wrap='word',font=('Consolas',10),bg=WHITE,fg=INK)
                    area.pack(fill='both',expand=True)
                    area.insert('1.0',text + ('\n\n[Vista limitada al primer MB]' if entry.size > 1024**2 else ''))
                    area.configure(state='disabled')
            except BaseException:
                window.destroy()
                raise
            window.actions('Cerrar',window.destroy)
            window.present()
        source = self.archive
        self.run_job('Preparando vista previa…',lambda:prepare_file_to_open(source,entry.name,self.cancel,self.report,password=self.password),show)

    def extract_paths(self, paths, *, destination=None, here=False):
        if self.busy:
            return
        # Resolve and deduplicate lazily so a missing volume can be reported per item.
        pending, groups = [], set()
        for path in paths:
            key = volume_key(path)
            if key not in groups:
                pending.append(Path(path).absolute())
                groups.add(key)
        secrets, seen, results, failures = {}, set(), [], []
        self.batch_password_path = None
        self.batch_secrets = secrets
        def skip():
            if pending:
                path = pending.pop(0)
                failures.append((path,error_text(self.batch_error)))
        self.batch_skip = skip
        def work():
            while pending:
                checkpoint(self.cancel)
                path = pending[0]
                self.events.put(('batch',f'Comprimido {len(results)+len(failures)+1} · {path.name}'))
                try:
                    source = resolve_volume(path)
                    key = str(source).casefold()
                    if key in seen:
                        pending.pop(0)
                        continue
                    parent = Path(destination) if destination else source.parent
                    self.password_target = source
                    if here:
                        output = extract_into(source,parent,self.cancel,self.report,password=secrets.get(path),conflict='rename')
                    else:
                        output = extract_archive(source,self.unique_destination(parent,source),self.cancel,self.report,password=secrets.get(path))
                except PasswordRequired:
                    self.batch_password_path = path
                    raise
                except Cancelled:
                    raise
                except Exception as error:
                    self.batch_error = error
                    raise BatchFailure(path,error) from error
                results.append((source,output))
                seen.add(key)
                pending.pop(0)
            return Path(destination) if destination else results[-1][1].parent if results else Path(paths[-1]).parent
        work._batch = True
        self.batch_report = (results, failures, pending)
        def done(output):
            if results:
                self.completed(output)
            self.status.set(f'Lote terminado: {len(results)} completados · {len(failures)} omitidos')
            if len(paths)>1 or failures:
                self.batch_summary()
        if pending:
            self.run_job('Extrayendo…',work,done)

    def batch_summary(self):
        report = getattr(self,'batch_report',None)
        if not report:
            return
        results, failures, pending = report
        lines = [f'Completados: {len(results)} · Omitidos: {len(failures)} · Pendientes: {len(pending)}']
        lines += ['\n✓ '+str(path)+'\n  '+str(out) for path,out in results]
        lines += ['\nOmitido: '+str(path)+'\n  '+error for path,error in failures]
        self.show_info('Resultado del lote','Resumen de las operaciones','\n'.join(lines))

    def batch_failure_action(self, error):
        result = ['cancel']
        window = Modal(self,'No se pudo extraer',error.path.name)
        tk.Label(window.body,text=error_text(error.cause),bg=WHITE,fg=INK,justify='left',wraplength=window.px(372),font=('Segoe UI',10)).pack(fill='x')
        def choose(action):
            result[0]=action
            window.destroy()
        window.actions('Reintentar',lambda:choose('retry'))
        tk.Button(window.footer,text='Omitir y continuar',command=lambda:choose('skip'),bg=WHITE,fg=INK,relief='flat',font=('Segoe UI',10)).pack(side='left')
        window.present()
        return result[0]
