import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
import unittest
from unittest.mock import patch

from dialogs import Modal


def measure_layout():
    root = tk.Tk()
    root.px = lambda value: round(value * 2)
    root.geometry('800x600+0+0')
    root.update_idletasks()
    try:
        modal = Modal(root, 'Preferencias', 'Opciones de visualización y extracción ' * 3)
        tk.Label(modal.body, text='Un nombre de archivo largo dentro de un comprimido',
                 padx=root.px(12), wraplength=root.px(340)).pack(fill='x')
        tk.Text(modal.body, width=65, height=3, wrap='word').pack(fill='x')
        for _ in range(18):
            modal.check('Conservar las opciones elegidas para los archivos existentes', tk.BooleanVar(modal))
        modal.actions('Guardar', modal.destroy)
        dimensions = {}

        def inspect():
            modal.update_idletasks()
            dimensions['width'] = modal.winfo_width()
            dimensions['height'] = modal.winfo_height()
            dimensions['body_width'] = modal.body.winfo_reqwidth()
            dimensions['canvas_width'] = modal.canvas.winfo_width()
            dimensions['scrollbar'] = modal.scrollbar.winfo_ismapped()
            modal.destroy()

        modal.after(50, inspect)
        with patch('dialogs.monitor_area', return_value=(0, 0, 800, 600)):
            modal.present()

        wide = Modal(root, 'Vista previa', 'Imagen de ejemplo')
        tk.Canvas(wide.body, width=root.px(500), height=30).pack()
        wide.actions('Cerrar', wide.destroy)
        image_dimensions = {}

        def inspect_wide():
            wide.update_idletasks()
            image_dimensions['width'] = wide.winfo_width()
            image_dimensions['height'] = wide.winfo_height()
            image_dimensions['horizontal'] = wide.hscrollbar.winfo_ismapped()
            image_dimensions['x_before'] = wide.canvas.xview()[0]
            wide.canvas.xview_moveto(1)
            image_dimensions['x_after'] = wide.canvas.xview()[0]
            wide.destroy()

        wide.after(50, inspect_wide)
        with patch('dialogs.monitor_area', return_value=(0, 0, 800, 600)):
            wide.present()
        return {'form': dimensions, 'image': image_dimensions}
    finally:
        root.destroy()


class ModalLayoutTests(unittest.TestCase):
    def test_scaled_dialog_fits_small_work_area_and_scrolls(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--measure'],
                                capture_output=True, text=True, timeout=15, check=True,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        measurements = json.loads(result.stdout)
        form, image = measurements['form'], measurements['image']
        self.assertLessEqual(form['width'], 800)
        self.assertLessEqual(form['height'], 600)
        self.assertLessEqual(form['body_width'], form['canvas_width'])
        self.assertTrue(form['scrollbar'])
        self.assertLessEqual(image['width'], 800)
        self.assertLessEqual(image['height'], 600)
        self.assertTrue(image['horizontal'])
        self.assertGreater(image['x_after'], image['x_before'])


if __name__ == '__main__':
    if '--measure' in sys.argv:
        print(json.dumps(measure_layout()))
    else:
        unittest.main()
