"""Smoke check run inside the packaged application, without user data."""
import json
from pathlib import Path
from archive_core import create_archive, extract_archive, verify_archive
from archive_core import modify_archive, convert_archive, restore_backup, list_backups, zip_comment, list_archive
from workspaces import archive_workspace

def smoke_report(app, report):
    checks = []
    with archive_workspace(prefix='wincip-check-') as folder:
        root = Path(folder)
        source = root / 'sample.txt'
        source.write_text('WinCip prueba ñ', encoding='utf-8')
        for fmt in ('zip', '7z'):
            archive = create_archive([source], root / ('test.' + fmt), format=fmt, password='clave ñ')
            verify_archive(archive, password='clave ñ')
            result = extract_archive(archive, root / fmt, password='clave ñ')
            assert (result / source.name).read_bytes() == source.read_bytes()
            checks.append(fmt + ': contraseña y extracción correctas')
        import pyzipper
        legacy = root / 'windows-password.zip'
        legacy_password = 'contraseña café'
        with pyzipper.AESZipFile(legacy, 'w', encryption=pyzipper.WZ_AES) as archive:
            archive.setpassword(legacy_password.encode('cp1252'))
            archive.writestr(source.name, source.read_bytes())
        restored = extract_archive(legacy, root / 'windows-password', password=legacy_password)
        assert (restored / source.name).read_bytes() == source.read_bytes()
        checks.append('ZIP con contraseña en codificación de Windows correcto')
        app.update_idletasks()
        checks.append('Tk y arrastrar/soltar inicializados')
        from PIL import Image, ImageTk
        picture = ImageTk.PhotoImage(Image.new('RGB', (16, 16), '#3266e3'), master=app)
        assert picture.width() == 16
        checks.append('Motor de imágenes y vista previa inicializados')
        archive = root / 'test.7z'
        modify_archive(archive, password='clave ñ', new_password='otra clave', backup=True, new_folder='vacía')
        verify_archive(archive, password='otra clave')
        converted = convert_archive(archive, root / 'converted.tar.gz', password='otra clave', format='tar.gz')
        output = extract_archive(converted, root / 'converted')
        assert (output / 'sample.txt').read_bytes() == source.read_bytes()
        assert (output / 'vacía').is_dir()
        checks.append('Edición 7Z, cambio de contraseña, respaldo y conversión TAR.GZ correctos')
        for fmt in ('tar', 'tar.gz', 'tar.bz2', 'tar.xz'):
            tar = create_archive([source], root / ('editable.' + fmt), format=fmt, verify=True)
            modify_archive(tar, rename=('sample.txt', 'edited.txt'), backup=True)
            assert any(e.name == 'edited.txt' for e in list_archive(tar))
            restore_backup(tar, list_backups(tar)[0])
            result = extract_archive(tar, root / ('restored-' + fmt))
            assert (result / 'sample.txt').read_bytes() == source.read_bytes()
        checks.append('Creación, edición y restauración de TAR/GZ/BZ2/XZ correctas')
        from edit_sessions import ExternalEdits
        zip_path = root / 'editor.zip'
        create_archive([source], zip_path)
        modify_archive(zip_path, comment=b'WinCip comment')
        copy = root / 'editor-copy.txt'
        copy.write_bytes(source.read_bytes())
        manager = ExternalEdits()
        manager.track(zip_path, source.name, copy)
        copy.write_bytes(b'external edit')
        manager.commit(manager.changed(), backup=True)
        result = extract_archive(zip_path, root / 'editor-result')
        assert (result / source.name).read_bytes() == b'external edit'
        assert zip_comment(zip_path) == b'WinCip comment'
        checks.append('Guardado del editor externo y conservación del comentario ZIP correctos')
        from rar_backend import rar_encoder
        if rar_encoder():
            rar = create_archive([source], root / 'optional.rar', format='rar', password='clave ñ', verify=True)
            modify_archive(rar, password='clave ñ', new_folder='empty', backup=True)
            verify_archive(rar, password='clave ñ')
            checks.append('Codificador RAR instalado: creación y edición cifradas correctas')
    Path(report).write_text(json.dumps({'ok': True, 'checks': checks}, ensure_ascii=False), encoding='utf-8')
