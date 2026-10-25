import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import tkinter as tk
from branding import APP_NAME
from tkinter import font as tkfont, ttk

WHITE = '#ffffff'
INK = '#202733'
MUTED = '#6b7585'
BLUE = '#3266e3'
BORDER = '#dce2eb'
SOFT = '#f7f8fa'


def monitor_area(window):
    try:
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                        ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
        user32 = ctypes.windll.user32
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        monitor = user32.MonitorFromWindow(window.winfo_id(), 2)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return info.work.left, info.work.top, info.work.right, info.work.bottom
    except (AttributeError, OSError):
        pass
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()


class Modal(tk.Toplevel):
    def __init__(self, parent, title, subtitle, *, secure=False):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.previous_grab = parent.grab_current()
        self.root = parent._root()
        self.px = getattr(self.root, 'px', lambda value: value)
        self.title(APP_NAME + ' · ' + ('Contraseña' if secure else title))
        self.configure(bg=WHITE)
        self.resizable(False, False)
        self.transient(parent)
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'WinCip.ico'
        if icon.is_file():
            self.iconbitmap(str(icon))
        self.bind('<Escape>', lambda _: self.destroy())
        self.scroller = tk.Frame(self, bg=WHITE)
        self.scroller.pack(fill='both', expand=True)
        self.canvas_row = tk.Frame(self.scroller, bg=WHITE)
        self.canvas_row.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(self.canvas_row, bg=WHITE, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar = ttk.Scrollbar(self.canvas_row, orient='vertical', command=self.canvas.yview)
        self.hscrollbar = ttk.Scrollbar(self.scroller, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.hscrollbar.set)
        self.body = tk.Frame(self.canvas, bg=WHITE, padx=self.px(28), pady=self.px(26))
        self.body_item = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.bind('<MouseWheel>', self.scroll_body)
        self.bind('<FocusIn>', self.reveal_focus, add='+')
        # The preferred width keeps labels and fields aligned at normal DPI.
        self.width_marker = tk.Frame(self.body, bg=WHITE, width=self.px(372), height=1)
        self.width_marker.pack(fill='x')
        if secure:
            badge = tk.Canvas(self.body, width=self.px(42), height=self.px(42), bg=WHITE, highlightthickness=0)
            badge.pack(anchor='w', pady=(0, self.px(15)))
            def points(*values):
                return [self.px(n) for n in values]
            badge.create_oval(*points(0, 0, 42, 42), fill='#edf2fe', outline='')
            badge.create_arc(*points(15, 10, 27, 28), start=0, extent=180, style='arc', outline=BLUE, width=self.px(2))
            badge.create_rectangle(*points(12, 20, 30, 32), fill=BLUE, outline=BLUE)
            badge.create_line(*points(21, 24, 21, 28), fill=WHITE, width=self.px(2))
        tk.Label(self.body, text=title, bg=WHITE, fg=INK, font=('Segoe UI Semibold', 17), anchor='w').pack(fill='x')
        tk.Label(self.body, text=subtitle, bg=WHITE, fg=MUTED, font=('Segoe UI', 10),
                 justify='left', anchor='w', wraplength=self.px(372)).pack(fill='x', pady=(self.px(6), self.px(22)))
        self.footer = tk.Frame(self, bg=SOFT, padx=self.px(28), pady=self.px(18))
        tk.Frame(self, bg='#edf0f5', height=1).pack(fill='x')
        self.footer.pack(fill='x')

    def label(self, text):
        label = tk.Label(self.body, text=text, bg=WHITE, fg=INK, font=('Segoe UI Semibold', 10), anchor='w')
        label.pack(fill='x', pady=(self.px(12), self.px(7)))
        return label

    def scroll_body(self, event):
        if self.scrollbar.winfo_ismapped() and event.widget.winfo_class() not in ('Text', 'TCombobox'):
            self.canvas.yview_scroll(-int(event.delta / 120), 'units')
            return 'break'

    def reveal_focus(self, event):
        if self.scrollbar.winfo_ismapped() and str(event.widget).startswith(str(self.body) + '.'):
            self.update_idletasks()
            y = event.widget.winfo_rooty() - self.body.winfo_rooty()
            start = self.canvas.canvasy(0)
            height = event.widget.winfo_height()
            if y < start or y + height > start + self.canvas.winfo_height():
                self.canvas.yview_moveto(max(0, y - self.px(20)) / max(1, self.body.winfo_height()))

    def check(self, text, variable, command=None):
        field = tk.Checkbutton(self.body, text=text, variable=variable, command=command,
                               bg=WHITE, fg=INK, activebackground=WHITE, selectcolor=WHITE,
                               font=('Segoe UI', 10), cursor='hand2', anchor='w',
                               highlightthickness=0, bd=0, padx=0, pady=self.px(6))
        field.pack(fill='x')
        return field

    def select(self, variable, values):
        field = ttk.Combobox(self.body, textvariable=variable, values=values,
                             state='readonly', style='Dialog.TCombobox')
        field.pack(fill='x', ipady=self.px(6), pady=(0, self.px(12)))
        return field

    def entry(self, variable, *, secret=False, toggle=None):
        border = tk.Frame(self.body, bg=BORDER, padx=1, pady=1)
        border.pack(fill='x', pady=(0, self.px(7)))
        inside = tk.Frame(border, bg=SOFT, padx=self.px(12), pady=self.px(10))
        inside.pack(fill='both', expand=True)
        if toggle:
            button = tk.Button(inside, text='Mostrar', command=toggle, bg=SOFT, fg=BLUE,
                               activebackground=SOFT, activeforeground='#244fb8', relief='flat',
                               bd=0, font=('Segoe UI Semibold', 9), cursor='hand2', takefocus=True)
            button.pack(side='right', padx=(self.px(10), 0))
            self.reveal_button = button
        field = tk.Entry(inside, textvariable=variable, show='•' if secret else '', bg=SOFT,
                         fg=INK, insertbackground=BLUE, selectbackground='#dfe9ff',
                         relief='flat', bd=0, highlightthickness=0, font=('Segoe UI', 11), width=18)
        field.pack(side='left', fill='x', expand=True)
        field.bind('<FocusIn>', lambda _: border.configure(bg=BLUE))
        field.bind('<FocusOut>', lambda _: border.configure(bg=BORDER))
        return field

    def actions(self, label, command):
        def button(text, action, primary):
            normal = BLUE if primary else '#e9edf3'
            hover = '#2856c7' if primary else '#dfe5ed'
            result = tk.Button(self.footer, text=text, command=action, bg=normal,
                               fg=WHITE if primary else INK, activebackground=hover,
                               activeforeground=WHITE if primary else INK, relief='flat', bd=0,
                               font=('Segoe UI Semibold', 10), padx=self.px(19), pady=self.px(9),
                               cursor='hand2', takefocus=True)
            result.bind('<Enter>', lambda _: result.configure(bg=hover))
            result.bind('<Leave>', lambda _: result.configure(bg=normal))
            return result
        primary = button(label, command, True)
        primary.pack(side='right')
        button('Cancelar', self.destroy, False).pack(side='right', padx=(0, self.px(10)))
        self.bind('<Return>', lambda _: command())
        return primary

    def present(self, focus=None):
        self.parent.update_idletasks()
        self.update_idletasks()
        left, top, right, bottom = monitor_area(self.parent)
        work_width = right - left
        work_height = bottom - top
        # Keep the body within the monitor's work area at high display scales.
        # Labels and checkboxes must reflow before measuring the final height.
        margin = min(self.px(32), work_width // 12)
        body_padding = 2 * self.px(28)
        scrollbar_width = self.scrollbar.winfo_reqwidth()
        content_width = max(1, min(self.px(372), work_width - 2 * margin - body_padding - scrollbar_width))
        self.width_marker.configure(width=content_width)
        def reflow(widget):
            for child in widget.winfo_children():
                if isinstance(child, (tk.Label, tk.Checkbutton, tk.Button)):
                    padding = child.winfo_pixels(str(child.cget('padx')))
                    child.configure(wraplength=max(1, content_width - 2 * padding))
                elif isinstance(child, tk.Text):
                    char_width = max(1, tkfont.Font(font=child.cget('font')).measure('M'))
                    child.configure(width=min(int(child.cget('width')),
                                              max(1, (content_width - self.px(12)) // char_width)))
                reflow(child)
        reflow(self.body)
        self.update_idletasks()
        content_height = self.body.winfo_reqheight()
        vertical_margin = min(self.px(80), work_height // 10)
        canvas_width = max(1, min(self.body.winfo_reqwidth(), work_width - 2 * margin - scrollbar_width))
        horizontal = self.body.winfo_reqwidth() > canvas_width
        available = max(1, work_height - self.footer.winfo_reqheight() - vertical_margin
                        - (self.hscrollbar.winfo_reqheight() if horizontal else 0))
        self.canvas.configure(width=canvas_width,
                              height=min(content_height, available))
        if content_height > available:
            self.scrollbar.pack(side='right', fill='y')
        if horizontal:
            self.hscrollbar.pack(side='bottom', fill='x')
        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - width) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - height) // 2
        x = max(left, min(x, right - width))
        y = max(top, min(y, bottom - height))
        self.geometry(f'{width}x{height}{x:+d}{y:+d}')
        self.deiconify()
        self.lift()
        self.grab_set()
        if focus:
            self.after_idle(focus.focus_set)
        try:
            self.parent.wait_window(self)
        finally:
            try:
                if self.previous_grab and self.previous_grab.winfo_exists():
                    self.previous_grab.grab_set()
            except tk.TclError:
                pass


def password_dialog(parent, confirm=False, *, archive_format=None):
    result = [None]
    window = Modal(parent, 'Protege tu comprimido' if confirm else 'Introduce la contraseña',
                   'Elige una contraseña para proteger tus archivos.' if confirm else 'Este comprimido está protegido con contraseña.', secure=True)
    if not confirm:
        root = parent._root()
        name = getattr(root, 'batch_password_path', None) or getattr(root, 'password_target', None) or getattr(root, 'archive', None)
        if name:
            tk.Label(window.body, text=Path(name).name, bg=SOFT, fg=INK, font=('Segoe UI', 10),
                     anchor='w', padx=window.px(12), pady=window.px(10), wraplength=window.px(340)).pack(fill='x', pady=(0, window.px(6)))
    value = tk.StringVar(window)
    repeat = tk.StringVar(window)
    fields = []
    visible = [False]
    def toggle():
        visible[0] = not visible[0]
        for field in fields:
            field.configure(show='' if visible[0] else '•')
        window.reveal_button.configure(text='Ocultar' if visible[0] else 'Mostrar')
    window.label('Contraseña')
    entry = window.entry(value, secret=True, toggle=toggle)
    fields.append(entry)
    if confirm:
        window.label('Confirmar contraseña')
        fields.append(window.entry(repeat, secret=True))
    error = tk.StringVar(window)
    tk.Label(window.body, textvariable=error, bg=WHITE, fg='#bc3345', font=('Segoe UI', 9),
             anchor='w').pack(fill='x', pady=(window.px(2), 0))
    if confirm:
        tk.Label(window.body, text='Guárdala en un lugar seguro para poder abrir tus archivos.',
                 bg=WHITE, fg=MUTED, font=('Segoe UI', 9), wraplength=window.px(372), justify='left').pack(fill='x', pady=(window.px(7), 0))
        if archive_format == 'zip':
            tk.Label(window.body,
                     text='Para compartir un ZIP con otros programas, usa una clave sin tildes ni ñ. Si necesitas esos caracteres, elige 7Z.',
                     bg=WHITE, fg=MUTED, font=('Segoe UI', 9), wraplength=window.px(372), justify='left').pack(fill='x', pady=(window.px(7), 0))
    def accept():
        if not value.get():
            error.set('Escribe una contraseña para continuar.')
            entry.focus_set()
            return
        if confirm and value.get() != repeat.get():
            error.set('Las contraseñas no coinciden.')
            fields[-1].focus_set()
            return
        result[0] = value.get()
        window.destroy()
    window.actions('Proteger' if confirm else 'Desbloquear', accept)
    window.present(entry)
    return result[0]
