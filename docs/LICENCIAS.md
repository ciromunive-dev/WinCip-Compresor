# Revisión de licencias y contenido distribuido

Revisión local del 24 de octubre de 2026. Esta página registra el inventario comprobado en la compilación Windows 10/11 x64 de WinCip Compresor 3.2.0. Los términos están en [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) y `licenses/`.

## Inventario

| Parte | Inclusión | Aviso |
| --- | --- | --- |
| Código y extensión de WinCip | Fuente, EXE y DLL propios | [MIT](../LICENSE) |
| Python 3.11.9 y módulos estándar | EXE | `licenses/Python.txt`, con avisos adicionales de OpenSSL, libffi, bzip2 y el CRT de Microsoft |
| Tcl/Tk 8.6 | EXE | `licenses/Tcl.txt` y `licenses/Tk.txt` |
| tkinterdnd2 0.6.4 y TkDND | EXE | MIT y licencia propia de TkDND; esta última pide reproducir el aviso íntegro |
| pyzipper 0.4.0 y pycryptodomex 3.24.1 | EXE | MIT más licencia del código derivado de Python; dominio público y BSD de 2 cláusulas, respectivamente |
| Pillow 12.2.0 | EXE | MIT-CMU y avisos de bibliotecas incluidas, entre ellas FreeType |
| 7-Zip 26.03 | EXE (`7z.exe`, `7z.dll`) | LGPL 2.1 o posterior, partes BSD y restricción unRAR, según `engine/License.txt` |
| PyInstaller 6.22.2 y pyinstaller-hooks-contrib 2026.9 | Compilación; bootloader de PyInstaller en el EXE | GPL con excepción para el bootloader; hooks estándar GPL y hooks de ejecución Apache 2.0 |
| NSIS 3.13 | Instalador | zlib/libpng, bzip2 y CPL 1.0 para LZMA |
| Zig 0.14.1, MinGW-w64 y bibliotecas LLVM | Compilación de la DLL C++ con enlace estático | MIT, ZPL 2.1 con excepciones por archivo, y Apache 2.0 con excepción LLVM; textos en `licenses/` |

El icono actual y las tres propuestas nuevas se dibujan con primitivas de Pillow; no se incorporaron imágenes de terceros. El instalador contiene texto rasterizado con fuentes de Windows, sin empaquetar el archivo de la fuente. WinRAR y su codificador RAR son opcionales en el equipo del usuario y no se distribuyen con WinCip.

## Comprobaciones realizadas

- Se compararon los SHA-256 de `engine/7z.exe`, `engine/7z.dll` y `engine/License.txt` con los archivos extraídos del [instalador oficial 7-Zip 26.03 x64](https://github.com/ip7z/7zip/releases/download/26.03/7z2603-x64.exe): los tres coinciden. Los ejecutables de 7-Zip están intactos. Se enlaza el [código fuente exacto de 26.03](https://www.7-zip.org/a/7z2603-src.tar.xz).
- Una compilación hecha antes desde el Python global había arrastrado NumPy, Jinja2, YAML y otros módulos no utilizados. La nueva compilación usa `.venv` con dependencias fijadas. El inventario del paquete PyInstaller contiene los módulos externos esperados: `pyzipper`, `Cryptodome`, `PIL` y `tkinterdnd2`.
- Se retiró la recolección completa de TkDND. El paquete contiene solo su DLL `win-x64` y los archivos Tcl de ese directorio. También se excluyeron 43 DLL del CRT universal que PyInstaller encontraba en el JDK del equipo; Windows 10/11 ya proporcionan ese componente.
- El portable y el archivo de código fuente contienen `LICENSE`, `THIRD_PARTY_NOTICES.md` y los archivos de `licenses/`. El instalador toma esos mismos archivos; el EXE incluye los avisos pertinentes.
- Se ejecutaron 121 pruebas Python en el entorno x64; el diagnóstico del EXE recompilado terminó con `ok: true`, incluido TkDND, ZIP y 7Z cifrados, imágenes y edición.

Huellas SHA-256 verificadas de 7-Zip: `7z.exe` = `6ee3c0ed0b27663c1b948ae85a7c0bb073aed1498983182f3f0df1f6a8c30b2f`, `7z.dll` = `65e4c1f855f9ef6e8f0f5df8e3f27d9eb5f07311408639da0a1ca0b8f4871b0d` y `License.txt` = `519ac0a4bded9c18ea02e0afb71f663d8c47373bd9facd3ac96a79f51d77765d`.

La atribución de 7-Zip en la documentación, su licencia y el enlace al código fuente siguen la [FAQ del autor](https://www.7-zip.org/faq.html). La [excepción de PyInstaller](https://pyinstaller.org/en/stable/license.html) permite distribuir el paquete con la licencia de la aplicación, respetando las de sus dependencias. La [licencia de NSIS](https://nsis.sourceforge.io/Docs/AppendixI.html), los [términos de TkDND](https://github.com/petasis/tkdnd/blob/master/license.terms), las [licencias de LLVM](https://github.com/llvm/llvm-project/blob/main/libcxx/LICENSE.TXT) y la [documentación de Microsoft sobre UCRT](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment) respaldan los avisos y el filtrado del paquete.

La revisión comprueba las versiones y archivos actuales. Si cambian Python, las dependencias, el motor, el instalador o los recursos, se debe repetir el inventario antes de distribuir una nueva versión. No se ha publicado ningún archivo ni se ha hecho una revisión jurídica formal.
