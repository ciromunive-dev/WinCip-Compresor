# Componentes de terceros

El código propio de WinCip Compresor se distribuye bajo [MIT](LICENSE). Los componentes siguientes conservan sus propias licencias. Las atribuciones y los textos completos se incluyen en `licenses/`, tanto en el código fuente como en el portable y el instalador.

| Componente | Versión | Licencia o aviso | Texto incluido |
| --- | --- | --- | --- |
| Python | 3.11.9 | PSF; el archivo incluye avisos de OpenSSL, libffi, bzip2 y código redistribuible de Microsoft | `licenses/Python.txt` |
| Tcl / Tk | 8.6 | Licencias Tcl/Tk | `licenses/Tcl.txt`, `licenses/Tk.txt` |
| tkinterdnd2 | 0.6.4 | MIT | `licenses/tkinterdnd2/` |
| TkDND, incluido con tkinterdnd2 | versión provista por tkinterdnd2 | Licencia permisiva propia; exige conservar su aviso íntegro | `licenses/TkDND.txt` |
| pyzipper | 0.4.0 | MIT; incluye código derivado de Python | `licenses/pyzipper/` (incluido `LICENSE.python`) |
| pycryptodomex | 3.24.1 | Dominio público y BSD de 2 cláusulas | `licenses/pycryptodomex/` |
| Pillow | 12.2.0 | MIT-CMU; avisos adicionales en su licencia | `licenses/Pillow/` |
| 7-Zip (`7z.exe`, `7z.dll`) | 26.03 | LGPL 2.1 o posterior, BSD y restricción unRAR según los archivos | `licenses/7-Zip.txt`, `licenses/LGPL-2.1.txt`, `engine/License.txt` |

7-Zip se distribuye sin modificaciones. Su [página oficial](https://www.7-zip.org/) y el [código fuente de la versión 26.03](https://www.7-zip.org/a/7z2603-src.tar.xz) están disponibles públicamente. La restricción unRAR se reproduce en el aviso de 7-Zip. WinCip no distribuye WinRAR ni `Rar.exe`.

Pillow incorpora componentes de [The FreeType Project](https://www.freetype.org/); su atribución y licencia se reproducen en `licenses/Pillow/`, junto con los demás avisos de bibliotecas incluidas por Pillow.

## Herramientas de compilación

| Herramienta | Versión | Alcance | Texto incluido |
| --- | --- | --- | --- |
| PyInstaller | 6.22.2 | Genera el EXE; su excepción permite distribuir la aplicación con su propia licencia | `licenses/pyinstaller/` |
| pyinstaller-hooks-contrib | 2026.9 | Hooks de compilación GPL 2.0 o posterior; hooks de ejecución Apache 2.0 | `licenses/pyinstaller-hooks-contrib/` |
| NSIS | 3.13 | Genera el instalador; sus módulos usan zlib/libpng, bzip2 y CPL 1.0 | `licenses/NSIS.txt` |
| Zig | 0.14.1 | Compila la DLL nativa; licencia MIT del compilador | `licenses/Zig.txt` |
| MinGW-w64 | incluido con Zig | Código de ejecución y cabeceras; ZPL 2.1 con excepciones por archivo | `licenses/mingw-w64.txt` |
| LLVM libc++, libc++abi y libunwind | incluidos con Zig | Bibliotecas de ejecución; Apache 2.0 con excepción LLVM | `licenses/LLVM-libcxx.txt`, `licenses/LLVM-libcxxabi.txt`, `licenses/LLVM-libunwind.txt` |

Los términos de las herramientas de compilación y los componentes empaquetados son independientes de la licencia MIT del código propio. El instalador contiene sus avisos; el EXE contiene los de las bibliotecas y del motor.
