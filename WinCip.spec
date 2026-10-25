# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[('engine/7z.exe', 'engine'), ('engine/7z.dll', 'engine')],
    datas=[('WinCip.ico', '.'), ('icon-ui.png', '.'), ('icon-small.png', '.'), ('icon-large.png', '.'), ('engine/License.txt', 'engine'),
           ('licenses', 'licenses'), ('THIRD_PARTY_NOTICES.md', '.'), ('LICENSE', '.')],
    hiddenimports=['tkinterdnd2', 'pyzipper'],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Windows 10/11 ship UCRT and its API-set forwarders. A JDK on PATH can
# otherwise make PyInstaller copy that JDK's private copies into our EXE.
a.binaries = [entry for entry in a.binaries
              if not entry[0].lower().startswith('api-ms-win-')
              and entry[0].lower() != 'ucrtbase.dll']
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WinCip',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['WinCip.ico'],
)
