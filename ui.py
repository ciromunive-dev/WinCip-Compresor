import tkinter as tk
from branding import APP_NAME
from pathlib import Path
import sys
from tkinter import ttk
from PIL import Image, ImageTk

BG = '#f7f8fa'
INK = '#202733'
MUTED = '#77808e'
BLUE = '#3266e3'


class SimpleUI:
    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('Dialog.TCombobox', fieldbackground='white', background='white',
                        foreground=INK, bordercolor='#dce2eb', lightcolor='#dce2eb',
                        darkcolor='#dce2eb', arrowcolor=MUTED, arrowsize=self.px(14), padding=self.px(6))
        style.map('Dialog.TCombobox', fieldbackground=[('readonly', 'white'), ('disabled', '#f7f8fa')],
                  foreground=[('disabled', MUTED), ('readonly', INK)],
                  selectbackground=[('readonly', 'white')], selectforeground=[('readonly', INK)])
        style.configure('Treeview', background='white', fieldbackground='white', foreground=INK,
                        rowheight=self.px(39), borderwidth=0)
        style.configure('Treeview.Heading', font=('Segoe UI', 9), background='white',
                        foreground=MUTED, padding=self.px(10), relief='flat')
        style.map('Treeview', background=[('selected', '#edf2fe')], foreground=[('selected', INK)])
        style.configure('Horizontal.TProgressbar', background=BLUE, troughcolor='#e9edf5', borderwidth=0)

    def button(self, parent, text, command, primary=False):
        button = tk.Button(parent, text=text, command=command, relief='flat', bd=0,
                           cursor='hand2', padx=self.px(16), pady=self.px(9), font=('Segoe UI Semibold', 10),
                           bg=BLUE if primary else 'white', fg='white' if primary else INK,
                           activebackground='#e9effe', activeforeground=INK,
                           disabledforeground='#a8b0bd')
        self.buttons.append(button)
        return button

    def build_ui(self):
        self.configure(bg=BG)
        assets = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        with Image.open(assets / 'icon-ui.png') as source:
            logo = source.convert('RGBA')
        self.brand_icon = ImageTk.PhotoImage(
            logo.resize((self.px(48), self.px(48)), Image.Resampling.LANCZOS), master=self)
        self.empty_icon = ImageTk.PhotoImage(
            logo.resize((self.px(128), self.px(128)), Image.Resampling.LANCZOS), master=self)
        self.level_value = tk.IntVar(value=6)
        header = tk.Frame(self, bg='white', padx=self.px(24), pady=self.px(16))
        header.pack(fill='x')
        tk.Label(header, image=self.brand_icon, bg='white').pack(side='left', padx=(0, self.px(10)))
        tk.Label(header, text=APP_NAME, font=('Segoe UI Semibold', 14), bg='white', fg=INK).pack(side='left')
        self.more_button = self.button(header, '···', self.show_more)
        self.more_button.pack(side='right', padx=(self.px(12), 0))
        self.primary_button = self.button(header, 'Crear comprimido', self.compress, True)
        self.open_button = self.button(header, 'Abrir', self.open_archive)
        self.open_button.pack(side='right', padx=(self.px(8), 0))
        self.add_button = self.button(header, '+ Añadir', self.show_add)
        self.add_button.pack(side='right', padx=(self.px(8), 0))
        tk.Frame(self, bg='#e9ecf1', height=1).pack(fill='x')

        self.footer = tk.Frame(self, bg=BG, padx=self.px(26), pady=self.px(13))
        self.footer.pack(side='bottom', fill='x')
        self.status = tk.StringVar(value='ZIP · RAR · 7Z · TAR')
        self.status_label = tk.Label(self.footer, textvariable=self.status, bg=BG, fg=MUTED,
                                     font=('Segoe UI', 9), anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True)
        self.cancel_button = tk.Button(self.footer, text='Cancelar', command=self.cancel.set,
                                       relief='flat', bg=BG, fg=INK, cursor='hand2')
        self.output_button = tk.Button(self.footer, text='Abrir carpeta ↗', command=self.open_output,
                                       relief='flat', bg=BG, fg=BLUE, cursor='hand2')
        self.progress = ttk.Progressbar(self, mode='determinate', maximum=100)

        self.content = tk.Frame(self, bg=BG, padx=self.px(26), pady=self.px(22))
        self.content.pack(fill='both', expand=True)
        self.empty = tk.Frame(self.content, bg=BG)
        welcome = tk.Frame(self.empty, bg=BG)
        welcome.place(relx=.5, rely=.46, anchor='center')
        tk.Label(welcome, image=self.empty_icon, bg=BG).pack(pady=(0, self.px(18)))
        tk.Label(welcome, text='Tus archivos, en un solo lugar', font=('Segoe UI Semibold', 19), bg=BG, fg=INK).pack()
        tk.Label(welcome, text='Abre un comprimido o crea uno nuevo.', font=('Segoe UI', 11), bg=BG, fg=MUTED).pack(pady=(self.px(8), self.px(4)))
        choice = tk.Frame(welcome, bg=BG)
        choice.pack(pady=(self.px(16), 0))
        self.button(choice, 'Abrir comprimido', self.open_archive, True).pack(side='left', padx=self.px(5))
        self.button(choice, 'Crear comprimido', self.add_files).pack(side='left', padx=self.px(5))
        tk.Label(welcome, text='También puedes arrastrar archivos aquí', font=('Segoe UI', 9), bg=BG, fg=MUTED).pack(pady=(self.px(20), 0))

        self.details = tk.Frame(self.content, bg=BG)
        self.heading = tk.Label(self.details, font=('Segoe UI Semibold', 17), anchor='w', bg=BG, fg=INK)
        self.heading.pack(fill='x')
        self.subtitle = tk.Label(self.details, font=('Segoe UI', 9), anchor='w', bg=BG, fg=MUTED)
        self.subtitle.pack(fill='x', pady=(5, 18))
        search_row = tk.Frame(self.details, bg=BG)
        search_row.pack(fill='x', pady=(0, 10))
        self.summary = tk.Label(search_row, bg=BG, fg=MUTED, anchor='w', font=('Segoe UI', 9))
        self.summary.pack(side='left', fill='x', expand=True)
        self.search = tk.StringVar()
        ttk.Entry(search_row, textvariable=self.search, width=22).pack(side='right', ipady=self.px(4))
        tk.Label(search_row, text='Buscar', bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(side='right', padx=self.px(8))
        self.search.trace_add('write', lambda *_: self.render_rows())
        navigation = tk.Frame(self.details, bg=BG)
        navigation.pack(fill='x', pady=(0, 8))
        self.button(navigation,'←',lambda:self.history_move(-1)).pack(side='left')
        self.button(navigation,'→',lambda:self.history_move(1)).pack(side='left')
        self.up_button = self.button(navigation, '↑ Subir', self.go_up)
        self.up_button.pack(side='left')
        self.location = tk.StringVar(value='/')
        location=ttk.Entry(navigation,textvariable=self.location,width=14)
        location.pack(side='left',fill='x',expand=True,padx=self.px(10),ipady=self.px(5))
        location.bind('<Return>',lambda _:self.navigate(self.location.get()))
        self.button(navigation, 'Extraer selección', self.extract_selected).pack(side='right')
        table = tk.Frame(self.details, bg='white', highlightthickness=1, highlightbackground='#e8ebf0')
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('name', 'size', 'type', 'packed', 'ratio'), show='headings', selectmode='extended')
        for col, title, width in [('name', 'Nombre', 420), ('size', 'Tamaño', 100), ('type', 'Tipo', 95), ('packed', 'Comprimido', 110), ('ratio', 'Ahorro', 80)]:
            self.tree.heading(col, text=title, anchor='w', command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=self.px(width), minwidth=self.px(60), anchor='w', stretch=col == 'name')
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        horizontal = ttk.Scrollbar(table, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scroll.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        self.tree.bind('<Delete>', lambda _: self.remove_selected() if not self.busy and not self.archive else None)
        self.tree.bind('<Double-1>', self.open_selected)
        self.tree.bind('<Return>', self.open_selected)
        self.update_actions()

    def menu(self):
        return tk.Menu(self, tearoff=False, font=('Segoe UI', 10), bg='white', fg=INK,
                       activebackground='#edf2fe', activeforeground=INK, bd=0)

    def show_add(self):
        menu=self.menu()
        if self.editable():
            menu.add_command(label='Archivos al comprimido abierto…',command=self.add_to_zip)
            menu.add_command(label='Carpeta al comprimido abierto…',command=self.add_folder_to_zip)
            menu.add_command(label='Nueva carpeta interna…',command=self.new_folder)
            menu.add_separator()
        def new_files():
            from tkinter import filedialog
            paths=filedialog.askopenfilenames(title='Archivos para un comprimido nuevo')
            if paths:self.add_paths(paths,force_new=True)
        menu.add_command(label='Archivos para comprimir…',command=new_files if self.archive else self.add_files)
        menu.add_command(label='Carpeta para comprimir…',command=self.add_folder)
        menu.tk_popup(self.add_button.winfo_rootx(),self.add_button.winfo_rooty()+self.add_button.winfo_height())

    def show_more(self):
        menu=self.menu()
        menu.add_command(label='Cerrar comprimido' if self.archive else 'Limpiar lista',command=self.clear)
        if self.archive:
            menu.add_command(label='Extraer selección…',command=self.extract_selected)
            menu.add_command(label='Vista previa',command=self.preview)
            menu.add_command(label='Propiedades',command=self.properties)
            menu.add_command(label='Copiar ruta interna',command=self.copy_names)
            menu.add_command(label='Guardar como…',command=self.save_archive_as)
            menu.add_command(label='Convertir formato…',command=self.convert)
            if self.editable():
                for title,action in [('Añadir o actualizar archivos…',self.add_to_zip),('Añadir o actualizar carpeta…',self.add_folder_to_zip),
                                     ('Nueva carpeta interna…',self.new_folder),('Renombrar selección…',self.rename_entry),
                                     ('Eliminar selección',self.delete_entries)]:
                    menu.add_command(label=title,command=action)
                if self.supports_password():
                    menu.add_command(label='Cambiar o quitar contraseña…',command=self.change_password)
                if self.archive.suffix.lower() == '.zip':
                    menu.add_command(label='Comentario ZIP…',command=self.edit_comment)
                menu.add_command(label='Actualizar desde editores externos…',command=self.update_external_edits)
            menu.add_command(label='Restaurar respaldo…',command=self.restore_archive_backup)
            menu.add_command(label='Abrir archivo',command=self.open_selected,state='normal' if len(self.tree.selection())==1 else 'disabled')
            menu.add_command(label='Verificar comprimido',command=self.verify)
        elif self.sources:
            menu.add_command(label='Quitar selección',command=self.remove_selected)
        menu.add_command(label='Extraer varios comprimidos…',command=self.extract_batch)
        recent=self.menu()
        for path in self.settings.get('recent',[]):
            recent.add_command(label=path,command=lambda p=path:self.open_path(p))
        recent.add_separator()
        recent.add_command(label='Borrar historial',command=self.clear_recent)
        menu.add_cascade(label='Recientes',menu=recent)
        menu.add_separator()
        menu.add_command(label='Preferencias…',command=self.preferences)
        menu.add_command(label='Ayuda',command=self.help)
        menu.add_command(label='Acerca de ' + APP_NAME,command=self.about)
        menu.add_command(label='Aplicación predeterminada y menú del Explorador…',command=self.default_settings)
        menu.tk_popup(self.more_button.winfo_rootx(),self.more_button.winfo_rooty()+self.more_button.winfo_height())

    def update_actions(self):
        populated = bool(self.sources or self.archive)
        if populated:
            self.empty.pack_forget()
            self.details.pack(fill='both', expand=True)
            self.primary_button.configure(text='Extraer' if self.archive else 'Crear comprimido',
                                           command=self.extract if self.archive else self.compress)
            self.primary_button.pack(side='right', after=self.more_button, padx=(self.px(10), 0))
        else:
            self.details.pack_forget()
            self.empty.pack(fill='both', expand=True)
            self.primary_button.pack_forget()
        self.primary_button.configure(state='disabled' if self.busy else 'normal')

    def show_progress(self):
        self.progress.pack(side='bottom', before=self.content, fill='x', padx=self.px(26))
        self.cancel_button.pack(side='right')
        self.output_button.pack_forget()

    def hide_progress(self):
        self.progress.pack_forget()
        self.cancel_button.pack_forget()
