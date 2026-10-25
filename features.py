"""Archive browsing, preferences and desktop actions."""
from pathlib import Path, PurePosixPath
import tempfile
from workflows import Workflows
from archive_support import archive_stem
from archive_formats import CREATE_FORMATS
import json
import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from archive_core import (Entry, create_archive, extract_archive, extract_into,
                          modify_zip, list_archive, verify_archive, PasswordRequired)


from dialogs import Modal, password_dialog, WHITE, MUTED


class Features(Workflows):
    def init_features(self):
        self.password = None
        self.current_folder = ''
        self.folder_history = ['']
        self.folder_index = 0
        self.row_entries = {}
        self.sort_column = 'name'
        self.sort_reverse = False
        self.job_start = time.monotonic()
        self.settings_path = Path(os.environ.get('WINCIP_SETTINGS', str(Path(os.environ.get('APPDATA', Path.home())) / 'WinCip' / 'settings.json')))
        try:
            self.settings = json.loads(self.settings_path.read_text(encoding='utf-8'))
            if not isinstance(self.settings, dict):
                self.settings = {}
        except (OSError, ValueError):
            self.settings = {}
        if self.settings.get('format') not in CREATE_FORMATS:
            self.settings['format']='zip'
        if self.settings.get('level',6) not in (0,1,6,9):
            self.settings['level']=6
        self.settings['recent']=[p for p in self.settings.get('recent',[]) if isinstance(p,str)][:10] if isinstance(self.settings.get('recent',[]),list) else []
        if self.settings.get('edit_conflict','Reemplazar') not in ('Reemplazar','Omitir','Solo más recientes'):
            self.settings['edit_conflict']='Reemplazar'
        if self.settings.get('conflict','Renombrar') not in ('Renombrar','Omitir','Reemplazar'):
            self.settings['conflict']='Renombrar'
        for key in ('remember_recent','verify_created','backup_edits'):
            if not isinstance(self.settings.get(key,True),bool):
                self.settings[key]=True
        for key, default in (('max_entries', 100_000), ('max_gib', 50)):
            if type(self.settings.get(key, default)) is not int or self.settings.get(key, default) < 0:
                self.settings[key] = default

    def save_settings(self):
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix='settings-', suffix='.tmp', dir=self.settings_path.parent)
            temp = Path(name)
            try:
                with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
                    json.dump(self.settings,stream,ensure_ascii=False,indent=2)
                os.replace(temp,self.settings_path)
            finally:
                temp.unlink(missing_ok=True)
        except OSError:
            pass

    def remember(self, path):
        if not self.settings.get('remember_recent',True):
            return
        recent = self.settings.get('recent', [])
        self.settings['recent'] = [str(path)] + [p for p in recent if p != str(path)][:9]
        self.save_settings()

    def install_features(self):
        self.level_value.set(self.settings.get('level', 6))
        self.level_value.trace_add('write', lambda *_: self.store_level())
        self.drop_target_register('DND_Files')
        self.dnd_bind('<<Drop>>', self.dropped)
        self.tree.bind('<Button-3>', self.context_menu)
        self.tree.bind('<Delete>', lambda _: None if self.busy else (self.delete_entries() if self.archive else self.remove_selected()))
        self.bind('<Alt-Up>', lambda _: self.go_up())
        self.bind('<Control-a>', self.select_all)
        self.bind('<Alt-Left>', lambda _: self.history_move(-1))
        self.bind('<Alt-Right>', lambda _: self.history_move(1))
        self.bind('<F1>', lambda _: self.help())
        self.bind('<F2>', lambda event: self.rename_entry() if event.widget.winfo_class() not in ('Entry','TEntry','Text','TCombobox') else None)
        self.bind('<Control-e>', lambda _: self.extract_selected())

    def store_level(self):
        self.settings['level'] = self.level_value.get()
        self.save_settings()

    def dropped(self, event):
        if self.busy:
            return
        paths = self.tk.splitlist(event.data)
        if len(paths) == 1 and Path(paths[0]).is_file():
            from archive_core import archive_kind, ArchiveError
            try:
                archive_kind(paths[0])
            except (ArchiveError, OSError):
                self.add_paths(paths)
            else:
                self.open_path(paths[0])
        else:
            self.add_paths(paths)

    def sort_by(self, column):
        self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
        self.sort_column = column
        self.render_rows()

    def render_rows(self):
        from app import size_text
        selected = set(self.selected_names()) if self.archive else set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        self.row_entries = {}
        self.up_button.configure(
            text='↑ Subir' if self.current_folder else '↗ Carpeta',
            state='normal' if self.archive and not self.busy else 'disabled')
        query = self.search.get().replace('\\','/').casefold()
        if self.archive:
            files = [e for e in self.entries if not e.directory]
            packed = sum(e.packed or 0 for e in files) if all(e.packed is not None for e in files) else None
            self.summary.configure(text=f'{len(self.entries):,} elementos · {size_text(sum(e.size for e in files))} · comprimido {size_text(packed) if packed is not None else "—"}')
            self.location.set('/'+self.current_folder)
            visible, totals = {}, {}
            for e in self.entries:
                name = e.name.replace('\\','/').removeprefix('./')
                if query:
                    if query in name.casefold():
                        visible[name.rstrip('/')]=(e,name)
                elif name.startswith(self.current_folder):
                    tail=name[len(self.current_folder):].rstrip('/')
                    if not tail:
                        continue
                    first,sep,_=tail.partition('/')
                    key=self.current_folder+first
                    if sep:
                        visible.setdefault(key,(Entry(key+'/',0,None,True),first))
                        if not e.directory:
                            aggregate=totals.setdefault(key,[0,0,True,False])
                            aggregate[0]+=e.size
                            aggregate[1]+=e.packed or 0
                            aggregate[2]=aggregate[2] and e.packed is not None
                            aggregate[3]=aggregate[3] or e.encrypted
                    else:
                        visible[key]=(e,first)
            from dataclasses import replace
            rows=[]
            for key,(e,label) in visible.items():
                if e.directory and key in totals:
                    total,compressed,known,encrypted=totals[key]
                    e=replace(e,size=total,packed=compressed if known else None,encrypted=encrypted)
                rows.append((e,label))
            def sort_value(item):
                e,label=item
                if self.sort_column=='name': return label.casefold()
                if self.sort_column=='size': return e.size
                if self.sort_column=='type': return 'Carpeta' if e.directory else Path(e.name).suffix.casefold()
                if self.sort_column=='packed': return e.packed if e.packed is not None else -1
                return (1-e.packed/e.size) if e.size and e.packed is not None else -1
            rows.sort(key=sort_value,reverse=self.sort_reverse)
            for index,(e,label) in enumerate(rows):
                iid=str(index)
                self.row_entries[iid]=e
                ratio=f'{100*(1-e.packed/e.size):.0f} %' if e.size and e.packed is not None else '—'
                self.tree.insert('','end',iid=iid,values=(label,size_text(e.size),'Carpeta' if e.directory else (Path(e.name).suffix or 'Archivo'),size_text(e.packed) if e.packed is not None else '—',ratio))
                if e.name in selected:
                    self.tree.selection_add(iid)
        else:
            self.location.set('/')
            self.summary.configure(text=f'{len(self.sources)} elementos')
            rows=[]
            for index,path in enumerate(self.sources):
                if query not in path.name.casefold(): continue
                try:
                    size=path.stat().st_size if path.is_file() else None
                    label='Carpeta' if path.is_dir() else 'Archivo'
                except OSError:
                    size,label=None,'No disponible'
                value=path.name.casefold() if self.sort_column=='name' else label if self.sort_column=='type' else (size if size is not None else -1) if self.sort_column=='size' else -1
                rows.append((value,index,path,size,label))
            for _,index,path,size,label in sorted(rows,key=lambda row:row[0],reverse=self.sort_reverse):
                iid=str(index)
                self.tree.insert('','end',iid=iid,values=(path.name,size_text(size) if size is not None else '—',label,'—','—'))
                if iid in selected: self.tree.selection_add(iid)
        self.update_actions()

    def go_up(self):
        if self.busy or not self.archive:
            return
        if not self.current_folder:
            try:
                os.startfile(str(self.archive.parent))
            except OSError as error:
                messagebox.showerror('Abrir carpeta', str(error), parent=self)
            return
        self.navigate(self.current_folder.rstrip('/').rpartition('/')[0])

    def selected_names(self):
        return [self.row_entries[i].name for i in self.tree.selection() if i in self.row_entries]

    def context_menu(self, event):
        if self.busy:
            return
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        menu = self.menu()
        if self.archive:
            menu.add_command(label='Abrir', command=self.open_selected)
            menu.add_command(label='Vista previa',command=self.preview)
            menu.add_command(label='Propiedades',command=self.properties)
            menu.add_command(label='Copiar ruta interna',command=self.copy_names)
            menu.add_command(label='Extraer selección…', command=self.extract_selected)
            if self.editable():
                menu.add_separator()
                menu.add_command(label='Añadir o actualizar…', command=self.add_to_zip)
                menu.add_command(label='Renombrar…', command=self.rename_entry)
                menu.add_command(label='Eliminar del comprimido', command=self.delete_entries)
                menu.add_command(label='Nueva carpeta…',command=self.new_folder)
        else:
            menu.add_command(label='Quitar selección', command=self.remove_selected)
        menu.tk_popup(event.x_root, event.y_root)


    def extract_selected(self):
        if self.busy or not self.archive:
            return
        names = self.selected_names()
        if not names:
            messagebox.showinfo('Extraer selección', 'Selecciona archivos o carpetas de la lista.')
            return
        self.extract_options(names)

    def extract_options(self, members=None):
        if self.busy or not self.archive:
            return
        parent = filedialog.askdirectory(title='Destino de extracción', initialdir=self.settings.get('destination', ''))
        if not parent:
            return
        self.settings['destination'] = parent
        self.save_settings()
        window = Modal(self, 'Extraer archivos', 'Elige cómo organizar los archivos en el destino.')
        window.label('Destino')
        tk.Label(window.body, text=parent, bg='#f7f8fa', fg='#202733', font=('Segoe UI', 10),
                 anchor='w', justify='left', wraplength=window.px(340), padx=window.px(12),
                 pady=window.px(10)).pack(fill='x', pady=(0, window.px(14)))
        new = tk.BooleanVar(value=True)
        def destination_changed():
            policy_field.configure(state='disabled' if new.get() else 'readonly')
        window.check('Crear una subcarpeta nueva', new, destination_changed)
        window.label('Si un archivo ya existe')
        policy = tk.StringVar(value=self.settings.get('conflict', 'Renombrar'))
        policy_field = window.select(policy, ['Renombrar', 'Omitir', 'Reemplazar'])
        destination_changed()
        def accept():
            fresh, conflict = new.get(), {'Renombrar': 'rename', 'Omitir': 'skip', 'Reemplazar': 'replace'}[policy.get()]
            self.settings['conflict'] = policy.get()
            self.save_settings()
            window.destroy()
            target = self.unique_destination(parent, self.archive) if fresh else Path(parent)
            action = extract_archive if fresh else extract_into
            options = {} if fresh else {'conflict': conflict}
            self.run_job('Extrayendo…', lambda: action(self.archive, target, self.cancel, self.report, password=self.password, members=members, **options), self.completed)
        window.actions('Extraer', accept)
        window.present()

    def unique_destination(self, parent, archive):
        base = Path(parent) / archive_stem(archive)
        target,index=base,2
        while target.exists():
            target=base.with_name(f'{base.name} ({index})')
            index+=1
        return target

    def delete_entries(self):
        if self.busy or not self.editable():
            return
        names = self.selected_names()
        if names and messagebox.askyesno('Eliminar del comprimido', f'¿Eliminar {len(names)} elementos seleccionados y su contenido?'):
            self.edit_zip(remove=names)

    def rename_entry(self):
        if self.busy or not self.editable():
            return
        names = self.selected_names()
        if len(names) != 1:
            return
        old = names[0].rstrip('/')
        new = simpledialog.askstring('Renombrar', 'Nuevo nombre:', initialvalue=PurePosixPath(old).name, parent=self)
        if new:
            if '/' in new or '\\' in new:
                messagebox.showerror('Nombre', 'Escribe un nombre sin carpetas.')
                return
            parent = old.rpartition('/')[0]
            self.edit_zip(rename=(old, parent + '/' + new if parent else new))


    def extract_batch(self):
        if self.busy:
            return
        paths = filedialog.askopenfilenames(title='Selecciona los comprimidos para extraer por lotes')
        if not paths:
            return
        parent = filedialog.askdirectory(title='Destino de los comprimidos')
        if parent:
            self.extract_paths(paths, destination=parent)
