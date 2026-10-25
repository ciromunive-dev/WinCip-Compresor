# Ejecución de los 66 casos de aceptación

25 de octubre de 2026 · Windows 11 x64 (`10.0.26300.0`)

Este registro corresponde a los [casos CP-01 a CP-66](HISTORIAS_USUARIO.md). Se ejecutaron pruebas con el motor Python, el EXE empaquetado, una instalación aislada y acciones visibles de la app. **FUNC** significa que el comportamiento se comprobó mediante pruebas automáticas o invocación controlada de la interfaz; no equivale a recorrer manualmente todo el diálogo. **PAR** indica que falta alguna variante o paso del caso. **GUI** indica que se ejecutó el flujo completo visible y se comprobaron los archivos resultantes. **PEND** indica que el entorno no permitió ejecutar ese caso.

Resumen: **4 GUI, 57 FUNC, 5 PAR y 0 PEND**. Los 66 casos tienen un resultado registrado; 5 aún requieren pasos de interfaz o una segunda versión de Windows.

## Evidencia de la ejecución

- La suite completa terminó correctamente: **147 pruebas**. Comando: `.\.venv\Scripts\python.exe -m unittest discover -q`. Las 17 pruebas de `test_acceptance_ui.py` operan controles Tk reales y verifican archivos, preferencias y mensajes; `test_interface.py` comprueba además el centrado, ajuste y escala de la ventana.
- `release/WinCip.exe`, el EXE instalado en una carpeta aislada y el portable extraído produjeron `ok: true` en el diagnóstico empaquetado. Tras el último cambio se repitió el diagnóstico del EXE reconstruido en `build/acceptance-66-final-smoke.json`. Informes previos: `build/acceptance-66-smoke.json`, `build/acceptance-66-installed-smoke.json` y `build/acceptance-66-portable-smoke.json`.
- Instalador aislado: instalación, actualización y desinstalación terminaron con código 0. El EXE y la documentación se copiaron; el registro de Aplicaciones instaladas apareció y luego se retiró; un archivo ajeno sobrevivió a la actualización y a la desinstalación. Se usaron `/NOINTEGRATION` y `/NOSTARTMENU` para no modificar las asociaciones ni los accesos del usuario.
- En la interfaz del EXE se abrió un 7Z y un ZIP mediante `Ctrl+O`. Se extrajo el ZIP completo a `build/acceptance-66-data/casos` y una carpeta seleccionada a `casos (2)`. Se comprobaron los bytes de cuatro archivos, una carpeta vacía, el ajuste del nombre `#859 Virales ` y la ausencia de archivos no seleccionados. También se abrió la ayuda con `F1`.
- La extensión `WinCip.ShellExtension` 3.2.0.0 quedó registrada con estado `Ok`. En el Explorador de Windows 11 se seleccionaron `dos.zip` y `uno.zip`, se abrió **WinCip Compresor → Extraer cada comprimido en su carpeta** desde el menú contextual moderno y se verificaron `dos/dos.txt` y `uno/uno.txt` con sus bytes esperados en `build/acceptance-66-modern/`.
- En **Mostrar más opciones → WinCip** se ejecutaron **Abrir con WinCip**, **Extraer en carpeta**, **Extraer aquí** y **Añadir a un comprimido**. Se comprobó la vista de `classic.zip`, los archivos de salida y los bytes de `from-menu.zip` en `build/acceptance-66-classic/`.
- El selector nativo de Windows mostró la confirmación al guardar sobre `from-menu.zip`. Se eligió **No** y se comprobaron los bytes originales; luego se eligió **Sí** y se verificó que el nuevo ZIP contiene el TXT actualizado.
- El equipo disponible es Windows 11. **No se ejecutó Windows 10 x64**; sus pasos de instalación e integración siguen pendientes de una máquina de esa versión.

## Resultado por caso

| Caso | Estado | Evidencia y alcance pendiente |
| --- | --- | --- |
| CP-01 | PAR | Instalación aislada y EXE instalado correctos; faltan asistente visible, acceso de Inicio y Windows 10. |
| CP-02 | PAR | Instalación sin integración y `test_windows_integration.py` correctos; falta instalar con integración y comprobar menús reales. |
| CP-03 | FUNC | Portable extraído y diagnóstico interno correcto con ZIP/7Z; falta recorrer apertura y extracción por sus botones. El motor va empaquetado en el EXE. |
| CP-04 | FUNC | Actualización aislada con código 0 y archivo ajeno intacto; falta comparar una preferencia modificada por el usuario. |
| CP-05 | FUNC | Desinstalador aislado retiró EXE y registro; conservó archivo ajeno. No se instalaron accesos por usar `/NOSTARTMENU`. |
| CP-06 | FUNC | Apertura visible de ZIP y 7Z con `Ctrl+O`; el botón **Abrir** de Tk cargó ZIP, 7Z, TAR y variantes GZ/BZ2/XZ, además de RAR cuando el codificador está disponible. Se comprobaron título y entrada. |
| CP-07 | PAR | `test_interface.py` simula soltar un archivo; falta arrastre físico de uno y varios archivos. |
| CP-08 | FUNC | Claves correctas e incorrectas en `test_complete.py`, `test_zip_passwords.py` y diagnóstico del EXE; falta diálogo visible para cada formato. |
| CP-09 | FUNC | Parte posterior y volumen ausente cubiertos por `test_advanced.py` y `test_complete.py`; falta abrirlo desde el selector visible. |
| CP-10 | FUNC | Controles Tk para abrir carpetas explícitas e implícitas, subir y recorrer historial; **↗ Carpeta** cubierto por `test_interface.py`. Falta recorrerlo físicamente en el EXE. |
| CP-11 | FUNC | Ruta válida y rechazo de `../` en `test_interface.py`; falta teclearla en el EXE. |
| CP-12 | FUNC | Retroceso y avance comprobados en `test_interface.py::test_history_selection_clipboard_and_properties`; falta uso visible de flechas y atajos. |
| CP-13 | FUNC | Búsqueda de una entrada de otra carpeta cubierta por `test_interface.py`; falta tecleo visible y limpieza del campo. |
| CP-14 | FUNC | `test_acceptance_ui.py` ejercita ambas direcciones de las cinco columnas y comprueba que la selección conserva las mismas entradas. Falta pulsar físicamente los encabezados en el EXE. |
| CP-15 | FUNC | `Ctrl+A` generado sobre la tabla seleccionó todas las filas; sobre Buscar seleccionó solo el texto y mantuvo las filas sin seleccionar. Selección múltiple cubierta por `test_interface.py`. |
| CP-16 | FUNC | Propiedades de una entrada mediante el control de la app y propiedades generales con dos entradas en `test_interface.py`; falta recorrido manual del EXE. |
| CP-17 | FUNC | Dos rutas internas verificadas en el portapapeles por `test_interface.py`; falta pegarlas en otra aplicación visible. |
| CP-18 | FUNC | Diálogo real de vista previa probado con TXT, PNG, HTML y SVG; se verificó el aviso por tamaño superior a 10 MB. Falta inspección visual del EXE. |
| CP-19 | PAR | Copias aisladas y nombres repetidos en `test_open_file.py`; no se abrió un editor externo real durante esta ejecución. |
| CP-20 | FUNC | Confirmación negativa bloquea la apertura en `test_interface.py`; no se ejecutó ningún archivo peligroso. |
| CP-21 | GUI | Extracción completa desde el EXE: archivos, bytes, estructura y carpeta vacía correctos en `build/acceptance-66-data/casos`. |
| CP-22 | FUNC | Dos archivos y una carpeta se extrajeron juntos desde **Extraer selección**; se comprobaron bytes, descendiente de carpeta y ausencia del archivo excluido. |
| CP-23 | FUNC | Dos subcarpetas nuevas visibles (`casos`, `casos (2)`) y opción de destino existente ejercitada desde el diálogo Tk. |
| CP-24 | FUNC | Se eligió **Renombrar** en el diálogo Tk; el existente conservó sus bytes y apareció `root (2).txt`. |
| CP-25 | FUNC | Se eligió **Omitir** en el diálogo Tk; el existente conservó sus bytes y se extrajo el archivo nuevo. |
| CP-26 | FUNC | Se eligió **Reemplazar** en el diálogo Tk y cambió el contenido; reversión ante fallo cubierta por `test_complete.py`. |
| CP-27 | FUNC | EXE extrajo `#859 Virales `; `test_archive_core.py` extrajo varios nombres del reporte original y rechazó una colisión antes de crear destino. Falta el lote completo desde el diálogo visible. |
| CP-28 | FUNC | Traversal, rutas absolutas y enlaces rechazados sin salida en `test_archive_core.py` y `test_seven.py`; falta comprobar mensaje visible. |
| CP-29 | FUNC | Cancelación sin destino parcial en `test_cancellation.py` y `test_archive_core.py`; falta pulsar **Cancelar** en una operación grande del EXE. |
| CP-30 | FUNC | Lote de dos archivos iniciado desde el menú Tk con resumen de dos resultados; además se ejecutó extracción de dos ZIP desde el menú de Windows 11. |
| CP-31 | FUNC | Reintento por contraseña y omisión de un ZIP dañado con continuación comprobados en `test_shell_actions.py`; falta recorrer los diálogos visibles. |
| CP-32 | FUNC | Verificación de archivos válidos y corruptos en `test_archive_core.py` y diagnóstico empaquetado; falta abrir el resultado desde el menú. |
| CP-33 | FUNC | Ruta enviada al Explorador comprobada con sustituto de `os.startfile` en `test_interface.py`; falta abrir una ventana real de Explorer. |
| CP-34 | FUNC | Menú **+ Añadir** ejercitado con selectores de archivos y carpeta; evitó duplicados y creó un ZIP con la estructura y bytes esperados. Arrastre simulado en `test_interface.py`; falta arrastre físico. |
| CP-35 | FUNC | Quitar y limpiar fuentes sin borrar archivos comprobado en `test_interface.py`; falta pulsar `Supr` y menú visibles. |
| CP-36 | FUNC | Creación/lectura de ZIP, 7Z, TAR y variantes, y RAR cuando existe codificador, en `test_advanced.py` y `test_architecture.py`; falta recorrer cada formato en el diálogo visible. |
| CP-37 | FUNC | Niveles de ZIP comprobados en `test_archive_core.py`; falta confirmar el control desactivado de TAR en pantalla. |
| CP-38 | FUNC | Filtros de inclusión y exclusión aplicados desde el diálogo Tk; el ZIP resultante solo contiene `keep.txt`. |
| CP-39 | FUNC | Casilla de verificación usada desde el diálogo Tk; conservación de destino ante fallo cubierta por `test_advanced.py`. |
| CP-40 | FUNC | ZIP/7Z cifrados y TAR sin contraseña comprobados en `test_complete.py`, `test_architecture.py` y EXE; falta recorrer sus diálogos visibles. |
| CP-41 | FUNC | Nombres ocultos en formatos cifrados comprobados en `test_complete.py` y `test_architecture.py`; falta la casilla visible. |
| CP-42 | FUNC | Volúmenes ZIP/7Z y lectura de parte posterior en `test_complete.py` y `test_advanced.py`; falta error visible de entrada negativa. |
| CP-43 | GUI | Confirmación nativa de Windows comprobada sobre un ZIP existente: **No** conservó el original y **Sí** lo reemplazó por uno válido con contenido actualizado. |
| CP-44 | FUNC | Adición/edición de formatos en `test_complete.py` y `test_architecture.py`; falta **+ Añadir** sobre cada formato en el EXE. |
| CP-45 | FUNC | Reemplazar, omitir y solo más recientes en `test_advanced.py`; falta el diálogo visible. |
| CP-46 | FUNC | Creación de carpeta interna mediante el control Tk y pruebas de nombre inseguro en el motor; falta el recorrido manual del EXE. |
| CP-47 | FUNC | Renombrado mediante el control Tk con contenido intacto; falta pulsar `F2` en el EXE. |
| CP-48 | FUNC | Eliminación de entrada desde el control Tk y de descendientes en `test_complete.py`; falta confirmar/cancelar en el EXE. |
| CP-49 | FUNC | Respaldos y numeración comprobados en `test_architecture.py`; falta activar/desactivar la opción en Preferencias visibles. |
| CP-50 | FUNC | Restauración desde el control Tk y rechazo de copia inválida en `test_architecture.py`; falta el selector visible del EXE. |
| CP-51 | FUNC | Establecer y quitar contraseña desde el diálogo Tk; cambio de clave y formatos adicionales en `test_advanced.py` y `test_architecture.py`. |
| CP-52 | FUNC | Comentario Unicode guardado desde el diálogo Tk y rechazo de más de 65 535 bytes UTF-8; archivos originales intactos. |
| CP-53 | FUNC | **Guardar como…** copió bytes idénticos; el diálogo Tk rechaza ruta igual y conjunto dividido. |
| CP-54 | FUNC | Conversión con original intacto y contraseña nueva explícita en `test_advanced.py` y `test_architecture.py`; falta el diálogo visible. |
| CP-55 | FUNC | Guardado de cambios externos con respaldo en `test_architecture.py` y diagnóstico empaquetado; falta edición con programa externo real. |
| CP-56 | FUNC | Sí/No/Cancelar antes de limpiar en `test_architecture.py`; faltan las variantes visibles de cerrar y cambiar de archivo. |
| CP-57 | FUNC | Rechazo cuando cambia el original y conservación de la copia en `test_architecture.py`; falta editar mediante una aplicación externa real. |
| CP-58 | FUNC | Se reabrió el primer ZIP desde **Recientes** del menú Tk y **Borrar historial** dejó la lista y el JSON vacíos. |
| CP-59 | FUNC | Formato, nivel, verificación, respaldo y política de actualización modificados en Preferencias; tras recrear la app se comprobaron valores y defaults del diálogo de creación. |
| CP-60 | FUNC | Se desactivó **Recordar comprimidos recientes** desde Preferencias; después de reiniciar seguía vacío. Al reactivarlo se registró el siguiente ZIP. |
| CP-61 | FUNC | Límites y rechazo sin salida parcial en `test_architecture.py`; Preferencias Tk rechazó `-1` y guardó límites válidos. |
| CP-62 | FUNC | Ayuda abierta con `F1` en el EXE; `test_acceptance_ui.py` comprobó también contenido de Ayuda y versión en **Acerca de**. |
| CP-63 | GUI | En Windows 11 se ejecutaron las cuatro acciones del menú clásico desde **Mostrar más opciones → WinCip** y se verificaron vista, archivos y contenido. Falta repetirlo en Windows 10 x64. |
| CP-64 | GUI | Paquete 3.2.0.0 registrado; desde el menú contextual moderno se seleccionaron dos ZIP y se ejecutó **Extraer cada comprimido en su carpeta**. Archivos y bytes correctos. |
| CP-65 | PAR | Ruta de configuración y protección de asociaciones cubiertas por `test_windows_integration.py`; no se cambió la aplicación predeterminada real. |
| CP-66 | FUNC | Limpieza de copia propia y conservación de la usada por otra ventana en `test_close_cleanup.py` y `test_temporary_files.py`; falta repetición manual con un visor abierto. |

## Criterio de publicación

La suite, el diagnóstico empaquetado y los menús contextuales clásico y moderno pasan en este Windows 11. **La matriz todavía no constituye una aprobación integral para Windows 10/11**: quedan los 5 casos PAR, variantes visuales indicadas en FUNC y una ejecución directa en Windows 10 x64. El registro distingue controles Tk automatizados de los recorridos manuales del EXE.
