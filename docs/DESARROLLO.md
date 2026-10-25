# Desarrollo de WinCip Compresor 3.2.0

[Volver al README](../README.md) · [Guía de uso](USO.md) · [Limitaciones](LIMITACIONES.md)

Todos los comandos siguientes se ejecutan en PowerShell desde la raíz del proyecto. El paquete Windows 10/11 x64 se compila con Python 3.11. La extensión moderna del Explorador requiere Windows 11; trabajar en la aplicación Python no requiere registrarla.

## Preparar el entorno

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m tkinter
```

El último comando abre una ventana de comprobación de Tkinter; ciérrala para continuar. Se usa la ruta completa del intérprete del entorno para no depender de activar scripts de PowerShell.

Comprueba que están presentes `engine/7z.exe`, `engine/7z.dll`, `engine/License.txt`, `WinCip.ico`, `icon-ui.png`, `icon-small.png` e `icon-large.png`. El motor de 7-Zip también se necesita al ejecutar desde el código.

```powershell
.\.venv\Scripts\python.exe app.py
```

`requirements.txt` fija las versiones de las bibliotecas de ejecución. PyInstaller y el compilador nativo se preparan por separado; el proceso actual no garantiza compilaciones idénticas byte por byte.

Consulta [ARQUITECTURA.md](ARQUITECTURA.md) para los contratos de las capas, transacciones y sesiones de edición externa.

## Estructura

| Archivo o carpeta | Responsabilidad |
| --- | --- |
| `branding.py` | Nombre visible del producto, conservando los identificadores de Windows |
| `app.py` | Inicio, estado de la ventana, trabajos, eventos, cancelación y argumentos de inicio |
| `ui.py` | Ventana principal, menús y estilos |
| `features.py` | Preferencias, lista, selección, arrastrar y soltar y extracción |
| `workflows.py` | Creación, edición, conversión, lotes, vista previa, propiedades y ayuda |
| `dialogs.py` | Diálogos compartidos y contraseñas |
| `archive_formats.py` / `archive_policy.py` | Capacidades compartidas y presupuestos por operación |
| `rar_backend.py` | Escritura RAR opcional con codificador instalado |
| `edit_sessions.py` | Copias de editores externos, huellas, conflictos y actualización |
| `archive_core.py` | Lectura, validación, creación, extracción, verificación y reconstrucción |
| `archive_support.py` | Volúmenes, nombres de conjuntos, marcas de zona y mensajes de error |
| `temporary_files.py` | Sesiones de archivos abiertos, protección entre ventanas y limpieza |
| `workspaces.py` | Carpetas propias de operación y reintentos acotados de limpieza transitoria |
| `windows_integration.py` | Registro de asociaciones y menús por usuario |
| `diagnostics.py` | Comprobación dentro del ejecutable empaquetado |
| `shell_extension/` | Extensión C++, prueba nativa, manifiesto y scripts de registro |
| `engine/` | Motor de 7-Zip y licencia incluida |
| `test_*.py` | Pruebas automatizadas Python |
| `WinCip.spec` / `version_info.txt` | Configuración y metadatos de compilación del EXE x64 |
| `build_release.py` | Generación del paquete e inventario de licencias |
| `build_assets.py` | Generación de los recursos gráficos actuales con Pillow |

La versión visible se define en `workflows.py`; los metadatos del EXE están en `version_info.txt`. El paquete de la extensión tiene su versión en `shell_extension/AppxManifest.xml` y referencia una DLL con nombre versionado. Una actualización debe mantener estos archivos y la ruta usada por `windows_integration.py` e `Install.ps1` coherentes.

## Pruebas Python

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Ejecuta la suite en Windows con las dependencias y el motor presentes; las pruebas de interfaz necesitan una sesión gráfica. Cubre operaciones de archivos, contraseñas, volúmenes, edición, conversión, conflictos, cancelación, temporales y acciones de interfaz. No sustituye a probar visualmente los diálogos, las escalas de pantalla y el menú real del Explorador.

Algunas pruebas crean muestras RAR mediante una instalación local de WinRAR y se omiten si no la encuentran. Revisa los casos omitidos en el resultado de `unittest`; que la suite termine correctamente no significa que se hayan ejecutado todos los casos RAR. WinRAR no es una dependencia para el uso normal de WinCip.

Para una prueba concreta:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_advanced
```

Utiliza archivos de prueba y destinos aislados para las comprobaciones manuales. Los [casos de aceptación](HISTORIAS_USUARIO.md) y sus [resultados](RESULTADOS_66_CASOS.md) cubren contenido extraído, conservación del original, respaldos, contraseñas y cancelación.

## Compilar el ejecutable

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath release --workpath build WinCip.spec
```

El resultado es `release/WinCip.exe`. Utiliza el archivo `.spec`: incluye el motor, su licencia, los iconos y los recursos de tkinterdnd2 para Windows x64. Compila desde un entorno virtual limpio para evitar que PyInstaller recoja módulos ajenos instalados en el Python global. El EXE contiene la aplicación y sus dependencias; la extensión nativa y su manifiesto se distribuyen aparte. Esta compilación no firma ni instala el programa.

No sobrescribas una DLL que Windows esté utilizando. La compilación del EXE tampoco actualiza por sí sola un paquete ya registrado en el Explorador.

### Comprobación del EXE

`--self-test` crea sus propios archivos temporales, comprueba ZIP y 7Z con contraseña, claves ZIP en codificación de Windows, inicialización de Tk/arrastrar y soltar e imágenes, edición de 7Z con respaldo, cambio de clave, conversión, edición/restauración TAR comprimido, guardado externo y comentarios ZIP. Si existe el codificador RAR instalado, comprueba también su creación y edición cifradas. Es una comprobación breve; no valida toda la interfaz ni la instalación. Si falla, devuelve un código distinto de cero y escribe un JSON con `ok: false`, el error y su traza. El [informe de validación](PRUEBAS.md) registra resultados y pendientes de esta revisión.

El siguiente ejemplo espera a que termine el EXE y aísla sus preferencias:

```powershell
New-Item -ItemType Directory -Path .\build -Force | Out-Null
$checkExe = (Resolve-Path -LiteralPath .\release\WinCip.exe).Path
$checkReport = Join-Path (Get-Location).Path 'build\self-test.json'
$previousSettings = $env:WINCIP_SETTINGS
try {
    $env:WINCIP_SETTINGS = Join-Path (Get-Location).Path 'build\self-test-settings.json'
    $checkProcess = Start-Process -FilePath $checkExe -ArgumentList ('--self-test "{0}"' -f $checkReport) -WindowStyle Hidden -Wait -PassThru
    if ($checkProcess.ExitCode -ne 0) { throw 'Falló la comprobación del ejecutable.' }
    $checkResult = Get-Content -LiteralPath $checkReport -Raw -Encoding UTF8 | ConvertFrom-Json
    if (!$checkResult.ok) { throw 'El informe no confirma el resultado.' }
    $checkResult
} finally {
    $env:WINCIP_SETTINGS = $previousSettings
}
```

## Generar instalador y portable

Instala las dependencias de ejecución y `requirements-dev.txt`. Necesitas NSIS 3.13 y Zig 0.14.1 disponibles en el PATH, o indicar sus rutas:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe build_release.py --nsis "C:\Herramientas\NSIS\makensis.exe" --zig "C:\Herramientas\Zig\zig.exe"
```

El script exige un entorno virtual, genera los iconos, recopila licencias, compila la aplicación y la DLL, prepara una lista explícita de archivos instalados y crea `release/WinCip-Compresor-3.2.0-Setup.exe`, el portable y `SHA256SUMS.txt`. `--package-only` permite regenerar los paquetes a partir de un EXE y DLL ya compilados. Los compiladores descargados en `build/toolchain/` son herramientas locales y no forman parte del código ni del instalador.

`installer/WinCip.nsi` define el asistente en español. El desinstalador elimina una lista concreta de archivos y solo retira del registro las referencias que siguen apuntando a esa instalación. No elimina recursivamente la carpeta del programa. La [guía de instalación](INSTALACION.md) describe los componentes y los argumentos de automatización.

## Extensión del Explorador

`shell_extension/WinCipShell.cpp` implementa `IExplorerCommand`. El paquete se llama `WinCip.ShellExtension`; la versión actual del manifiesto es `3.2.0.0` y referencia `WinCipShell-3.2.dll`. El CLSID es `{D4E07230-5AF0-4E95-A8A0-80D732CC1791}`.

La compilación utilizada es Zig 0.14.1. Con `zig` disponible en `PATH`:

```powershell
zig c++ -target x86_64-windows-gnu -shared -O2 -std=c++17 -static shell_extension/WinCipShell.cpp -o WinCipShell-3.2.dll -lole32 -lshell32 -lshlwapi -luuid
```

### Prueba nativa sin registro

El ejecutable de pruebas puede cargar directamente una DLL. Compílalo sin desactivar las aserciones: actualmente algunas llamadas de comprobación están dentro de `assert`, por lo que no debe usarse `-DNDEBUG` ni una configuración que las elimine.

```powershell
New-Item -ItemType Directory -Path .\build -Force | Out-Null
zig c++ -target x86_64-windows-gnu -O0 -std=c++17 -static -municode shell_extension/test_shell.cpp -o build/test_shell.exe -lole32 -lshell32 -luuid
```

Crea un ZIP de muestra y una carpeta física cuyo nombre termine en `.zip`:

```powershell
@'
from pathlib import Path
from zipfile import ZipFile
root = Path('build/shell-check')
root.mkdir(parents=True, exist_ok=True)
with ZipFile(root / 'sample.zip', 'w') as archive:
    archive.writestr('sample.txt', 'sample')
(root / 'folder.zip').mkdir(exist_ok=True)
'@ | .\.venv\Scripts\python.exe -

$checkDll = (Resolve-Path -LiteralPath .\WinCipShell-3.2.dll).Path
$checkZip = (Resolve-Path -LiteralPath .\build\shell-check\sample.zip).Path
$checkFolder = (Resolve-Path -LiteralPath .\build\shell-check\folder.zip).Path
.\build\test_shell.exe $checkZip -1 $checkDll 1
.\build\test_shell.exe $checkFolder -1 $checkDll 0
```

La prueba comprueba títulos, estados y enumeración del submenú. `-1` evita invocar acciones; `1` espera un comprimido y `0` un elemento para comprimir. Pasar un índice entre `0` y `4` como segundo argumento sí ejecuta una acción de la extensión. Esta prueba directa no confirma que el paquete esté instalado ni que el menú aparezca en el Explorador.

### Registro opcional de desarrollo

Este apartado documenta los scripts existentes; la instalación definitiva se preparará al final de la revisión del proyecto. El registro modifica la integración de Windows para el usuario actual. Coloca estos archivos en una ubicación estable:

```text
WinCip.exe
WinCipShell-3.2.dll
shell_extension/
    AppxManifest.xml
    Install.ps1
    Uninstall.ps1
    Assets/
        StoreLogo.png
        Square150x150Logo.png
        Square44x44Logo.png
```

El manifiesto de desarrollo requiere que Windows permita registrar este tipo de paquetes. Los scripts no cambian esa configuración ni instalan certificados. Si el equipo no lo permite, el EXE sigue siendo utilizable sin la extensión; el empaquetado para distribución pública queda pendiente.

Para registrar el paquete desde esa ubicación:

```powershell
powershell -NoProfile -File .\shell_extension\Install.ps1
Get-AppxPackage -Name WinCip.ShellExtension | Select-Object Name, Version, Status, InstallLocation
```

`Install.ps1` comprueba versión, ubicación y estado antes de volver a registrar. No configura por sí solo todas las asociaciones de archivos ni el menú clásico. La acción **Aplicación predeterminada y menú del Explorador…** de WinCip registra esas capacidades, intenta registrar el paquete moderno si hay DLL y abre la configuración de Windows para que el usuario elija los valores predeterminados. No escribe la elección protegida `UserChoice` de Windows.

Si Windows devuelve `0x80073D02`, hay recursos del paquete en uso. No fuerces el cierre del Explorador ni reemplaces su DLL cargada; resuelve el uso del paquete y reintenta cuando deje de estar activo.

Para retirar el paquete y las claves del menú que gestiona el script:

```powershell
powershell -NoProfile -File .\shell_extension\Uninstall.ps1
```

Ese script no es un desinstalador completo: no borra los ejecutables, preferencias ni todos los registros de asociaciones creados por la aplicación. No muevas una carpeta con una extensión registrada sin retirar o actualizar antes su registro.

## Argumentos de inicio

Estos argumentos abren la interfaz; no son una API de consola sin interacción. En los ejemplos se puede sustituir `WinCip.exe` por `.\.venv\Scripts\python.exe app.py`.

| Argumento | Comportamiento |
| --- | --- |
| `"C:\Datos\archivo.zip"` | Abre el comprimido |
| `--compress "C:\Datos\uno.txt" "C:\Datos\carpeta"` | Prepara la lista y abre el diálogo de creación |
| `--extract "C:\Datos\archivo.zip"` | Abre el comprimido y pide las opciones de extracción |
| `--extract "C:\Datos\uno.zip" "C:\Datos\dos.7z"` | Pide un destino común y extrae cada conjunto a una carpeta nueva |
| `--extract-here "C:\Datos\archivo.zip"` | Extrae junto al comprimido y renombra conflictos |
| `--extract-folder "C:\Datos\archivo.zip"` | Extrae a una carpeta nueva junto al comprimido |
| `--self-test "C:\Datos\informe.json"` | Ejecuta la comprobación breve y escribe el informe; la carpeta del informe debe existir |

`--cleanup-temporaries` es un argumento interno para el auxiliar de limpieza; no es una acción de mantenimiento general para el usuario.

## Preferencias y API interna

La aplicación lee `%APPDATA%\WinCip\settings.json`. Para aislar pruebas o desarrollo, define `WINCIP_SETTINGS` con la ruta de otro archivo antes de iniciarla. No incluyas preferencias personales, datos de prueba privados ni herramientas descargadas en una distribución del código.

Las funciones de `archive_core.py` son una API interna. Reciben rutas, cancelación y callbacks de progreso según la operación. `create_archive()` tiene `verify=False` de forma predeterminada; la interfaz activa la verificación inicialmente y le pasa la elección del usuario. Un consumidor de la función debe pedir `verify=True` explícitamente si necesita esa comprobación. No confundir las opciones de la interfaz con los valores predeterminados de la API.

Las contraseñas se pasan en memoria a las operaciones y no se guardan en las preferencias. El motor externo puede recibirlas en su línea de comandos; consulta las [limitaciones](LIMITACIONES.md) para conocer el alcance de esa protección.
