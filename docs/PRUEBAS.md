# Validación de WinCip Compresor 3.2.0

Revisión del 25 de octubre de 2026. [Desarrollo](DESARROLLO.md) contiene los comandos para repetir las comprobaciones.

## Entorno y resultado

Windows 11 x64, versión del sistema `10.0.26300.0`, Python 3.11.9 x64, PyInstaller 6.22.2 y 7-Zip 26.03 x64. Falta una prueba directa en Windows 10.

| Comprobación | Resultado |
| --- | --- |
| Suite Python | 147 pruebas correctas en Python 3.11 x64; incluye edición TAR comprimido, restauración, editores externos, extracción múltiple, colisiones de nombres, navegación, centrado y ajuste de la ventana principal, recursos a escala DPI, limpieza transitoria, registro aislado y 17 pruebas de aceptación con controles Tk |
| Comprobación del EXE reconstruido | `build/dpi-ui-smoke.json` con `ok: true`: ZIP/7Z con contraseña, clave ZIP en codificación de Windows, Tk, arrastrar y soltar, imágenes, edición 7Z, respaldo y conversión TAR.GZ |
| Interfaz al 175 % de escala | Inspección visual del inicio; el logo usa 84 px en la cabecera y 224 px en la bienvenida a partir del recurso de 512 px. El caso de una pantalla pequeña se comprobó por geometría, sin cambiar la resolución física del equipo |
| Interoperabilidad con el motor externo | Correcta para ZIP normal y AES con clave ASCII, 7Z normal y cifrado con clave Unicode, TAR y TAR.GZ |
| ZIP Unicode entre WinCip y WinRAR | WinRAR leyó un ZIP UTF-8 de WinCip; WinCip verificó y extrajo un ZIP generado por WinRAR tras la corrección de compatibilidad |
| Extensión nativa por carga directa de DLL | Correcta para ZIP real, carpeta física llamada `.zip` y nombre de extracción de RAR dividido |
| Instalación y actualización | Instalador silencioso en una carpeta aislada; registro en Aplicaciones instaladas; actualización sin borrar un archivo añadido por el usuario; diagnóstico del EXE instalado correcto |
| Desinstalación | Retiró sus archivos y el registro de Aplicaciones instaladas, conservando el documento añadido; registro de asociaciones probado por separado en un subárbol aislado |
| Icono e instalador | Inspección visual de la bienvenida en español y del icono azul propio |
| Menús de Windows 11 | Paquete `WinCip.ShellExtension` 3.2.0.0 registrado y operativo; dos ZIP extraídos desde el menú moderno. Desde el clásico se abrieron archivos, extrajo en carpeta y aquí, y se creó un ZIP a partir de un TXT. Contenido comprobado |
| Confirmación de reemplazo | El selector nativo conservó el ZIP anterior tras elegir **No** y guardó el nuevo tras elegir **Sí**; se comparó el contenido en ambos pasos |
| Documentación | Enlaces locales, codificación UTF-8 y sintaxis de los bloques PowerShell revisados |
| Revisión de licencias y paquete | 7-Zip contrastado con los binarios oficiales; 21 archivos de licencias y atribuciones incluidos; EXE compilado desde `.venv` sin módulos globales ajenos ni DLL del JDK |

Las pruebas comprueban contenido extraído y conservación de originales, no solo que el programa termine sin error. La suite también cubre rutas inseguras, enlaces, conflictos, reversión ante errores, cancelación, archivos temporales y varias ventanas.

La [matriz de los 66 casos de aceptación](RESULTADOS_66_CASOS.md) registra las comprobaciones realizadas en esta revisión y distingue los resultados funcionales de las interacciones visuales todavía pendientes.

## Fallos encontrados durante la revisión

Un ZIP de WinRAR con contraseña no ASCII no se abría con su clave correcta. Se añadió lectura alternativa de las codificaciones habituales de Windows conservando UTF-8 como primera opción. Las nuevas pruebas cubren extracción, verificación, copia temporal, edición con respaldo, contraseña incorrecta y contenido cifrado dañado. Los intentos fallidos de extracción conservan la limpieza del destino temporal.

Se confirmó una limitación externa: 7-Zip para Windows no aceptó la clave no ASCII de un ZIP UTF-8 de WinCip que WinRAR sí pudo leer. La interfaz y la documentación explican cómo elegir una clave ZIP compatible o utilizar 7Z. No se ha declarado compatibilidad con todas las codificaciones o programas.

El diagnóstico empaquetado reprodujo el error de directorio temporal no vacío durante la limpieza de la carpeta de una edición RAR, después de generar el resultado. La traza permitió localizarlo en la salida de `TemporaryDirectory`. Se centralizó la limpieza en `workspaces.py`, con reintentos acotados para errores transitorios de directorio no vacío o bloqueo, validando la propiedad de la ruta antes de cada intento. Se añadieron regresiones con un archivo bloqueado real de Windows y con una creación concurrente que provoca WinError 145. Los errores permanentes siguen notificándose y un fallo de limpieza no oculta el error original de una operación fallida. No se ha atribuido la causa externa del bloqueo a ningún programa concreto.

## Alcance pendiente

La inspección visual confirmó la ventana principal, ayuda, menú con las acciones nuevas y Preferencias con los presupuestos configurables. El control automatizado del selector de archivos falló en una revisión anterior de la herramienta, por lo que esa interacción no se cuenta como validada manualmente. Las pruebas de interfaz Python cubren guardar, descartar o cancelar cambios externos antes de cerrar el comprimido, pero no reemplazan la revisión visual de todos los diálogos y escalas de pantalla.

Se inspeccionó de nuevo Preferencias a la escala actual y se añadió una prueba de disposición que simula un área útil de 800 × 600 píxeles con escala de interfaz de 200 %. Comprueba que el diálogo cabe, activa el desplazamiento vertical, adapta el ancho del texto y ofrece desplazamiento horizontal para una imagen ancha. Sigue pendiente la comprobación en monitores físicos con otras escalas.

La extensión 3.2.0.0 se registró y se probó en el Explorador de este Windows 11. La instalación, actualización y desinstalación del programa se probaron en una carpeta aislada. Queda pendiente ejecutar el instalador y repetir la integración en Windows 10 x64, además de probar el programa en un equipo sin el entorno de desarrollo.

Los informes y registros de esta revisión están en `build/validation-*` y no forman parte de la distribución de código. Son evidencias locales; no deben ser necesarios para ejecutar las pruebas documentadas.

El nombre visible **WinCip Compresor** también se comprobó en los metadatos del EXE y en los títulos devueltos por la DLL. La comprobación interna se amplió a edición/restauración TAR/GZ/BZ2/XZ, guardado externo, comentarios ZIP y escritura RAR cuando existe el codificador instalado. La integración anterior del Explorador no se reemplazó en las pruebas aisladas. El instalador normal ofrece su registro clásico y un intento opcional de registro moderno.

## Ejecutable validado

`WinCip.exe` y `release/WinCip.exe` contienen la misma compilación. SHA-256:

```text
78A581816543C542177688F9335AFD5F2F8A538BC79230C7113733756BB45272
```

Este identificador corresponde a esta revisión. Debe renovarse después de cualquier recompilación y no sustituye a una firma digital.
