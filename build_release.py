"""Build the application, licenses, portable archive, and Windows installer."""
import argparse
import hashlib
import importlib.metadata as metadata
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent


def run(command):
    subprocess.run([str(part) for part in command], cwd=ROOT, check=True)


def sync_local_executable():
    """Keep the already registered repository executable in sync with release."""
    local = ROOT/'WinCip.exe'
    if local.is_file():
        try:
            shutil.copy2(ROOT/'release/WinCip.exe', local)
        except PermissionError as error:
            raise RuntimeError('Cierra WinCip.exe de la carpeta del proyecto antes de compilar.') from error


def collect_licenses(zig_executable=None):
    target = ROOT / 'licenses'
    target.mkdir(exist_ok=True)
    versions = {}
    for name in ('tkinterdnd2', 'pyzipper', 'pycryptodomex', 'Pillow', 'pyinstaller', 'pyinstaller-hooks-contrib'):
        package = metadata.distribution(name)
        versions[name] = package.version
        for item in package.files or []:
            if any(part.lower().startswith(('license', 'copying', 'authors')) for part in item.parts):
                source = Path(package.locate_file(item))
                if source.is_file():
                    output = target / name / Path(*item.parts)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, output)
    python_root = Path(sys.base_prefix)
    for source, filename in [(python_root/'LICENSE.txt', 'Python.txt'),
                             (python_root/'tcl/tk8.6/license.terms', 'Tk.txt'),
                             (python_root/'tcl/tcl8.6/license.terms', 'Tcl.txt')]:
        if source.is_file():
            shutil.copy2(source, target/filename)
    for filename in ('Tcl.txt', 'TkDND.txt', 'LGPL-2.1.txt'):
        source = ROOT/'licenses'/filename
        if source.is_file() and not (target/filename).is_file():
            shutil.copy2(source, target/filename)
    tcl_license = target/'Tcl.txt'
    if not tcl_license.exists():
        urllib.request.urlretrieve('https://raw.githubusercontent.com/tcltk/tcl/core-8-6-branch/license.terms', tcl_license)
    tkdnd_license = target/'TkDND.txt'
    if not tkdnd_license.exists():
        urllib.request.urlretrieve('https://raw.githubusercontent.com/petasis/tkdnd/master/license.terms', tkdnd_license)
    lgpl = target/'LGPL-2.1.txt'
    if not lgpl.exists():
        urllib.request.urlretrieve('https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt', lgpl)
    shutil.copy2(ROOT/'engine/License.txt', target/'7-Zip.txt')
    compiler_license = ROOT/'build/toolchain/nsis-3.13/COPYING'
    if compiler_license.exists():
        shutil.copy2(compiler_license, target/'NSIS.txt')
    zig_root = Path(zig_executable).resolve().parent if zig_executable else ROOT/'build/toolchain/ziglang'
    zig_notices = {
        'Zig.txt': 'LICENSE',
        'mingw-w64.txt': 'lib/libc/mingw/COPYING',
        'LLVM-libcxx.txt': 'lib/libcxx/LICENSE.TXT',
        'LLVM-libcxxabi.txt': 'lib/libcxxabi/LICENSE.TXT',
        'LLVM-libunwind.txt': 'lib/libunwind/LICENSE.TXT',
    }
    for filename, relative in zig_notices.items():
        source = zig_root / relative
        if source.is_file():
            shutil.copy2(source, target/filename)
    required = ('Python.txt', 'Tcl.txt', 'Tk.txt', 'TkDND.txt', '7-Zip.txt', 'LGPL-2.1.txt', 'NSIS.txt', *zig_notices)
    missing = [name for name in required if not (target/name).is_file()]
    if missing:
        raise FileNotFoundError(f'Faltan avisos de licencias: {missing}')
    notice = f'''# Componentes de terceros

El código propio de WinCip Compresor se distribuye bajo [MIT](LICENSE). Los componentes siguientes conservan sus propias licencias. Las atribuciones y los textos completos se incluyen en `licenses/`, tanto en el código fuente como en el portable y el instalador.

| Componente | Versión | Licencia o aviso | Texto incluido |
| --- | --- | --- | --- |
| Python | {sys.version.split()[0]} | PSF; el archivo incluye avisos de OpenSSL, libffi, bzip2 y código redistribuible de Microsoft | `licenses/Python.txt` |
| Tcl / Tk | 8.6 | Licencias Tcl/Tk | `licenses/Tcl.txt`, `licenses/Tk.txt` |
| tkinterdnd2 | {versions['tkinterdnd2']} | MIT | `licenses/tkinterdnd2/` |
| TkDND, incluido con tkinterdnd2 | versión provista por tkinterdnd2 | Licencia permisiva propia; exige conservar su aviso íntegro | `licenses/TkDND.txt` |
| pyzipper | {versions['pyzipper']} | MIT; incluye código derivado de Python | `licenses/pyzipper/` (incluido `LICENSE.python`) |
| pycryptodomex | {versions['pycryptodomex']} | Dominio público y BSD de 2 cláusulas | `licenses/pycryptodomex/` |
| Pillow | {versions['Pillow']} | MIT-CMU; avisos adicionales en su licencia | `licenses/Pillow/` |
| 7-Zip (`7z.exe`, `7z.dll`) | 26.03 | LGPL 2.1 o posterior, BSD y restricción unRAR según los archivos | `licenses/7-Zip.txt`, `licenses/LGPL-2.1.txt`, `engine/License.txt` |

7-Zip se distribuye sin modificaciones. Su [página oficial](https://www.7-zip.org/) y el [código fuente de la versión 26.03](https://www.7-zip.org/a/7z2603-src.tar.xz) están disponibles públicamente. La restricción unRAR se reproduce en el aviso de 7-Zip. WinCip no distribuye WinRAR ni `Rar.exe`.

Pillow incorpora componentes de [The FreeType Project](https://www.freetype.org/); su atribución y licencia se reproducen en `licenses/Pillow/`, junto con los demás avisos de bibliotecas incluidas por Pillow.

## Herramientas de compilación

| Herramienta | Versión | Alcance | Texto incluido |
| --- | --- | --- | --- |
| PyInstaller | {versions['pyinstaller']} | Genera el EXE; su excepción permite distribuir la aplicación con su propia licencia | `licenses/pyinstaller/` |
| pyinstaller-hooks-contrib | {versions['pyinstaller-hooks-contrib']} | Hooks de compilación GPL 2.0 o posterior; hooks de ejecución Apache 2.0 | `licenses/pyinstaller-hooks-contrib/` |
| NSIS | 3.13 | Genera el instalador; sus módulos usan zlib/libpng, bzip2 y CPL 1.0 | `licenses/NSIS.txt` |
| Zig | 0.14.1 | Compila la DLL nativa; licencia MIT del compilador | `licenses/Zig.txt` |
| MinGW-w64 | incluido con Zig | Código de ejecución y cabeceras; ZPL 2.1 con excepciones por archivo | `licenses/mingw-w64.txt` |
| LLVM libc++, libc++abi y libunwind | incluidos con Zig | Bibliotecas de ejecución; Apache 2.0 con excepción LLVM | `licenses/LLVM-libcxx.txt`, `licenses/LLVM-libcxxabi.txt`, `licenses/LLVM-libunwind.txt` |

Los términos de las herramientas de compilación y los componentes empaquetados son independientes de la licencia MIT del código propio. El instalador contiene sus avisos; el EXE contiene los de las bibliotecas y del motor.
'''
    (ROOT/'THIRD_PARTY_NOTICES.md').write_text(notice, encoding='utf-8')


def stage_payload():
    stage = ROOT/'build/installer-payload'
    stage.mkdir(parents=True, exist_ok=True)
    files = [Path(name) for name in ('WinCip.exe', 'WinCip.ico', 'WinCipShell-3.2.dll',
                                     'README.md', 'ALCANCE.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md')]
    files += [path.relative_to(ROOT) for directory in ('docs', 'licenses', 'shell_extension/Assets')
              for path in (ROOT/directory).rglob('*') if path.is_file()]
    files += [Path('shell_extension')/name for name in ('AppxManifest.xml','Install.ps1','Uninstall.ps1')]
    files.append(Path('engine/License.txt'))
    for relative in files:
        source = ROOT/'release'/relative if relative.name in ('WinCip.exe','WinCipShell-3.2.dll') else ROOT/relative
        output = stage/relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output)
    install, uninstall = [], ['StrCpy $R5 0']
    for relative in sorted(set(files)):
        directory = str(relative.parent).replace('/', '\\')
        install.append(f'SetOutPath "$INSTDIR\\{directory}"')
        install.append(f'File "{stage/relative}"')
        uninstall += ['ClearErrors', f'Delete "$INSTDIR\\{relative}"', 'IfErrors 0 +2', 'StrCpy $R5 1']
    directories = {parent for file in files for parent in file.parents if parent != Path('.')}
    uninstall += [f'RMDir "$INSTDIR\\{directory}"' for directory in sorted(directories,key=lambda p:len(p.parts),reverse=True)]
    (ROOT/'build/installer-files.nsh').write_text('\n'.join(install)+'\n',encoding='utf-8-sig')
    (ROOT/'build/uninstaller-files.nsh').write_text('\n'.join(uninstall)+'\n',encoding='utf-8-sig')
    return stage, files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nsis', default=shutil.which('makensis') or str(ROOT/'build/toolchain/nsis-3.13/makensis.exe'))
    parser.add_argument('--zig', default=shutil.which('zig') or str(ROOT/'build/toolchain/ziglang/zig.exe'))
    parser.add_argument('--package-only',action='store_true',help='Reuse a previously built release EXE and DLL')
    args=parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error('Compila desde un entorno virtual con requirements.txt y requirements-dev.txt instalados.')
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'release').mkdir(exist_ok=True)
    if not args.package_only:
        run([sys.executable,'build_assets.py'])
        collect_licenses(args.zig)
        run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath','release','--workpath','build','WinCip.spec'])
        run([args.zig,'c++','-target','x86_64-windows-gnu','-shared','-O2','-std=c++17','-static',
             'shell_extension/WinCipShell.cpp','-o','release/WinCipShell-3.2.dll','-lole32','-lshell32','-lshlwapi','-luuid'])
    else:
        collect_licenses(args.zig)
    sync_local_executable()
    stage,files=stage_payload()
    run([args.nsis,'/V3',ROOT/'installer/WinCip.nsi'])
    with ZipFile(ROOT/'release/WinCip-Compresor-3.2.0-Portable.zip','w',ZIP_DEFLATED) as archive:
        for relative in sorted(set(files)):
            archive.write(stage/relative, relative.as_posix())
    sources = [path for path in ROOT.iterdir() if path.is_file() and path.suffix in ('.py','.md','.txt','.spec','.ico')]
    sources += [ROOT/name for name in ('icon-ui.png','icon-small.png','icon-large.png','icon-preview.png')]
    sources += [ROOT/'LICENSE', ROOT/'.gitignore', ROOT/'.gitattributes']
    sources += [path for directory in ('docs','licenses','shell_extension','installer','engine')
                for path in (ROOT/directory).rglob('*') if path.is_file()]
    with ZipFile(ROOT/'release/WinCip-Compresor-3.2.0-Source.zip','w',ZIP_DEFLATED) as archive:
        for source in sorted(set(sources)):
            archive.write(source, source.relative_to(ROOT).as_posix())
    outputs=('WinCip.exe','WinCipShell-3.2.dll','WinCip-Compresor-3.2.0-Setup.exe','WinCip-Compresor-3.2.0-Portable.zip','WinCip-Compresor-3.2.0-Source.zip')
    checksums=[]
    for name in outputs:
        digest=hashlib.sha256((ROOT/'release'/name).read_bytes()).hexdigest()
        checksums.append(f'{digest}  {name}')
    (ROOT/'release/SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n',encoding='utf-8')
    print('Installer, portable archive and checksums written to release/.')


if __name__ == '__main__':
    main()
