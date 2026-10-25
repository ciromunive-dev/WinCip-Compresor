# Historias de usuario y casos de prueba

WinCip Compresor 3.2.0 · 24 de octubre de 2026

Este catálogo describe lo que una persona puede hacer con la aplicación distribuida para **Windows 10 y 11 x64**. Cada historia `HU` tiene un caso `CP` con el mismo número. Son casos de aceptación: documentarlos no significa que todos se hayan ejecutado. La [evidencia de pruebas ya realizadas](PRUEBAS.md) distingue la suite automática de las comprobaciones manuales.

## Preparación común

- Usar una carpeta temporal fuera del código y conservar una copia de los originales. Preparar `uno.txt`, `dos.txt`, una carpeta con archivos y una subcarpeta vacía; también una imagen PNG pequeña.
- Preparar un ZIP normal, un ZIP cifrado, un 7Z, un TAR, un comprimido dividido y un ZIP con nombres de carpeta terminados en espacio. Para los casos de error, preparar por separado un archivo corrupto y otro con `../escape.txt`.
- Ejecutar los casos de interfaz con el EXE distribuido. Repetir instalación y menú clásico en Windows 10 y 11 x64; el menú moderno corresponde solo a Windows 11 y depende de que el sistema permita registrar el paquete.
- En los casos de sobrescritura, usar copias de prueba. Comprobar contenido y ubicación de los archivos, además del mensaje mostrado por la aplicación.

## Instalación e inicio

| Historia | Caso de prueba |
| --- | --- |
| **HU-01.** Como usuario, quiero instalar WinCip con el asistente para abrirlo sin instalar Python ni 7-Zip. | **CP-01.** En Windows 10/11 x64, ejecutar el instalador con la configuración básica. Comprobar acceso en Inicio, entrada en Aplicaciones instaladas y apertura de `WinCip.exe` sin Python ni 7-Zip externos. |
| **HU-02.** Como usuario, quiero elegir los componentes opcionales para integrar WinCip con el Explorador según mi sistema. | **CP-02.** Instalar con y sin la opción de integración. Comprobar que el menú clásico aparece solo cuando se eligió; en Windows 11, intentar la opción moderna y comprobar que el instalador informa si el registro no es posible. |
| **HU-03.** Como usuario, quiero ejecutar la edición portable para usar la app sin instalarla. | **CP-03.** Extraer el ZIP portable en una carpeta nueva y abrir su `WinCip.exe`. Abrir y extraer un ZIP; comprobar que el paquete trae el motor y que las preferencias quedan en el perfil del usuario. |
| **HU-04.** Como usuario, quiero actualizar una instalación propia para recibir una nueva compilación sin perder mis datos. | **CP-04.** Instalar una compilación en una carpeta de prueba, añadir allí un archivo ajeno y actualizar sobre la misma carpeta. Verificar que inicia la compilación nueva, conserva el archivo ajeno y no borra las preferencias. |
| **HU-05.** Como usuario, quiero desinstalar WinCip para retirar sus accesos y componentes sin borrar mis documentos. | **CP-05.** Desinstalar desde Aplicaciones instaladas o `Desinstalar.exe`. Verificar retirada de accesos y archivos instalados; comprobar que permanecen comprimidos, documentos, preferencias y archivos ajenos a la instalación. |

## Abrir y explorar comprimidos

| Historia | Caso de prueba |
| --- | --- |
| **HU-06.** Como usuario, quiero abrir un comprimido desde **Abrir** o `Ctrl+O` para ver su contenido. | **CP-06.** Abrir un ZIP válido por ambas vías. Verificar título, ruta, lista de entradas y tamaños; repetir con 7Z, RAR, TAR y variantes GZ/BZ2/XZ admitidas. |
| **HU-07.** Como usuario, quiero arrastrar un comprimido a la ventana para abrirlo directamente. | **CP-07.** Soltar un solo ZIP en la ventana. Verificar que aparece su contenido; soltar varios archivos normales y comprobar que se preparan como fuentes para crear un comprimido. |
| **HU-08.** Como usuario, quiero introducir la contraseña de un comprimido protegido para acceder a él. | **CP-08.** Abrir ZIP, 7Z y RAR cifrados. Probar una clave incorrecta y luego la correcta; comprobar que se puede leer y extraer, y que cancelar el diálogo no cambia el comprimido abierto previamente. |
| **HU-09.** Como usuario, quiero abrir cualquier parte de un conjunto dividido para ver su contenido sin buscar la primera parte. | **CP-09.** Abrir una parte posterior de un conjunto compatible con todas sus partes juntas; verificar que la app encuentra la primera y muestra el contenido. Retirar una parte y comprobar que informa del conjunto incompleto. |
| **HU-10.** Como usuario, quiero entrar y salir de carpetas internas para localizar archivos. | **CP-10.** Abrir un ZIP con carpetas explícitas e implícitas; entrar con doble clic o `Enter`, usar **↑ Subir** o `Alt+↑` y verificar la ruta y filas visibles. En la raíz, comprobar que **↗ Carpeta** abre en el Explorador la carpeta del comprimido. |
| **HU-11.** Como usuario, quiero escribir una ruta interna para llegar a una carpeta concreta. | **CP-11.** Escribir una ruta existente en la barra y pulsar `Enter`; verificar su contenido. Probar una ruta inexistente y `../`; comprobar que se informa del error sin salir del comprimido. |
| **HU-12.** Como usuario, quiero retroceder y avanzar por las carpetas visitadas para retomar mi recorrido. | **CP-12.** Visitar dos carpetas, usar flechas o `Alt+←` y `Alt+→`; comprobar que cada acción restaura la carpeta correspondiente. |
| **HU-13.** Como usuario, quiero buscar por nombre o ruta para encontrar entradas dentro del comprimido. | **CP-13.** Escribir parte del nombre de un archivo situado en otra carpeta; verificar que aparece en resultados y que borrar la búsqueda restaura la vista de la carpeta actual. |
| **HU-14.** Como usuario, quiero ordenar la lista por sus columnas para comparar archivos. | **CP-14.** Pulsar dos veces los encabezados Nombre, Tamaño, Tipo, Comprimido y Ahorro. Comprobar orden ascendente y descendente y que la selección sigue apuntando a la misma entrada. |
| **HU-15.** Como usuario, quiero seleccionar uno o varios elementos para operar sobre ellos. | **CP-15.** Seleccionar elementos con Ctrl/Mayús y después `Ctrl+A`; comprobar selección múltiple. Escribir `Ctrl+A` dentro de un campo de texto y verificar que selecciona su texto, no las filas. |
| **HU-16.** Como usuario, quiero consultar propiedades de una entrada o del comprimido para conocer tamaño, método y cifrado. | **CP-16.** Abrir **Propiedades** con una entrada seleccionada y verificar sus datos. Repetir sin selección y con varias entradas; verificar datos generales y número seleccionado. |
| **HU-17.** Como usuario, quiero copiar las rutas internas seleccionadas para pegarlas en otra aplicación. | **CP-17.** Seleccionar dos entradas, usar **Copiar ruta interna** y pegar en un editor. Verificar una ruta por línea y que no son rutas del destino de extracción. |
| **HU-18.** Como usuario, quiero previsualizar texto e imágenes para inspeccionarlos sin abrir su aplicación externa. | **CP-18.** Previsualizar un TXT y un PNG admitidos; verificar texto o imagen. Probar un archivo mayor al límite y comprobar el aviso. Un HTML o SVG debe mostrarse como texto. |
| **HU-19.** Como usuario, quiero abrir un archivo interno con su aplicación de Windows para trabajar con él. | **CP-19.** Abrir un archivo interno con doble clic. Verificar que se crea una copia temporal aislada y se abre con la asociación de Windows; abrir el mismo nombre desde otro comprimido y comprobar que las copias no se pisan. |
| **HU-20.** Como usuario, quiero decidir si abro un ejecutable interno para evitar iniciarlo por accidente. | **CP-20.** Intentar abrir un `.exe` o script interno. Verificar el diálogo de confirmación; elegir No y comprobar que no se inicia el archivo. |

## Extraer y verificar

| Historia | Caso de prueba |
| --- | --- |
| **HU-21.** Como usuario, quiero extraer todo el comprimido para recuperar sus archivos. | **CP-21.** Pulsar **Extraer**, elegir destino y subcarpeta nueva. Verificar nombres, contenido y estructura de todos los archivos, incluida una carpeta vacía. |
| **HU-22.** Como usuario, quiero extraer solo archivos o carpetas seleccionados para evitar contenido innecesario. | **CP-22.** Seleccionar dos archivos y una carpeta, usar **Extraer selección** o `Ctrl+E`. Verificar que aparecen solo esas entradas y los descendientes de la carpeta seleccionada. |
| **HU-23.** Como usuario, quiero elegir entre subcarpeta nueva y destino existente para organizar la extracción. | **CP-23.** Extraer dos veces con **Crear una subcarpeta nueva** y comprobar nombres disponibles distintos. Repetir sin esa opción y verificar que los archivos llegan al directorio elegido. |
| **HU-24.** Como usuario, quiero conservar archivos existentes al elegir **Renombrar** para no perderlos. | **CP-24.** Extraer en un destino que ya contiene `uno.txt` con **Renombrar**. Verificar el original intacto y una copia extraída con nombre alternativo. |
| **HU-25.** Como usuario, quiero omitir archivos que ya existen para mantener mi versión. | **CP-25.** Extraer con **Omitir** sobre `uno.txt` existente y otro archivo nuevo. Verificar que `uno.txt` conserva sus bytes y que el archivo nuevo sí se extrae. |
| **HU-26.** Como usuario, quiero reemplazar archivos existentes cuando necesito la versión del comprimido. | **CP-26.** Extraer con **Reemplazar** sobre una copia de prueba de `uno.txt`. Verificar que sus bytes coinciden con el comprimido; provocar un fallo controlado y comprobar la reversión documentada de esa operación. |
| **HU-27.** Como usuario, quiero extraer archivos con espacios o puntos finales en nombres internos para poder usarlos en Windows. | **CP-27.** Extraer juntos `#859 Virales /uno.txt`, `637 [ PacksVirales.com ] /dos.txt` y `tercero. `. Verificar que aparecen sin el espacio o punto final, con el contenido correcto. Probar una colisión tras ajustar nombres y comprobar que se detiene antes de crear el destino. |
| **HU-28.** Como usuario, quiero recibir un error seguro cuando un comprimido contiene rutas peligrosas para proteger el destino. | **CP-28.** Intentar extraer un ZIP con `../escape.txt`, un enlace o una ruta absoluta. Comprobar que no aparece nada fuera del destino ni queda una carpeta de extracción parcial. |
| **HU-29.** Como usuario, quiero cancelar una operación en curso para detenerla sin dejar un resultado incompleto. | **CP-29.** Iniciar una extracción grande y pulsar **Cancelar**. Esperar el fin del trabajo; verificar que no aparece un destino parcial y que la interfaz vuelve a aceptar acciones. |
| **HU-30.** Como usuario, quiero extraer varios comprimidos en un lote para no repetir la operación manualmente. | **CP-30.** Usar **Extraer varios comprimidos…** con dos ZIP y un destino. Verificar una carpeta nueva por comprimido, contenido correcto y resumen con dos completados. |
| **HU-31.** Como usuario, quiero reintentar u omitir un comprimido fallido para continuar el lote. | **CP-31.** Crear un lote con uno válido, uno cifrado y uno defectuoso. Verificar solicitud de clave, conservación del resultado ya terminado, opciones **Reintentar** y **Omitir y continuar**, y conteos del resumen. |
| **HU-32.** Como usuario, quiero verificar la lectura de un comprimido para detectar daños antes de usarlo. | **CP-32.** Usar **Verificar comprimido** con uno válido y otro corrupto. Comprobar confirmación en el primero y error en el segundo; comprobar que ninguno se modifica. |
| **HU-33.** Como usuario, quiero abrir la carpeta del resultado para encontrar lo que acabo de crear o extraer. | **CP-33.** Completar una extracción y pulsar **Abrir carpeta ↗**. Verificar que el Explorador muestra la carpeta correcta. Repetir tras crear un comprimido. |

## Preparar y crear comprimidos

| Historia | Caso de prueba |
| --- | --- |
| **HU-34.** Como usuario, quiero añadir archivos o carpetas para preparar un comprimido nuevo. | **CP-34.** Usar **+ Añadir** para agregar archivos y una carpeta; probar también arrastrar archivos. Verificar la lista, evitar duplicados y mantener la estructura de la carpeta al crear el resultado. |
| **HU-35.** Como usuario, quiero quitar elementos de la lista o limpiarla para corregir la selección antes de comprimir. | **CP-35.** Seleccionar una fuente y usar `Supr` o **Quitar selección**; verificar que desaparece de la lista sin borrarse del disco. Usar **Limpiar lista** y comprobar el estado inicial. |
| **HU-36.** Como usuario, quiero elegir el formato de salida para compartirlo con otras aplicaciones. | **CP-36.** Crear resultados ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2 y TAR.XZ con el mismo archivo. Abrirlos de nuevo y verificar contenido. Comprobar que RAR solo se ofrece cuando existe un codificador compatible instalado. |
| **HU-37.** Como usuario, quiero elegir nivel de compresión para ajustar tamaño y tiempo. | **CP-37.** Crear dos ZIP con niveles **Sin compresión** y **Máxima** a partir de datos repetitivos. Comprobar que ambos se leen y que se aplican los métodos o tamaños esperados. En TAR sin compresión, comprobar que el selector queda desactivado. |
| **HU-38.** Como usuario, quiero filtrar archivos al crear un comprimido para incluir solo lo necesario. | **CP-38.** Crear desde una carpeta con `*.txt`, `*.pdf` y `*.tmp`; incluir `*.txt; *.pdf` y excluir `*.tmp`. Abrir el resultado y comprobar que contiene únicamente las coincidencias permitidas. |
| **HU-39.** Como usuario, quiero verificar antes de guardar para evitar sustituir un resultado bueno por uno defectuoso. | **CP-39.** Activar **Verificar antes de guardar**, crear un ZIP y volver a abrirlo. Simular un fallo de verificación en una prueba automática y comprobar que el destino previo permanece intacto. |
| **HU-40.** Como usuario, quiero proteger un ZIP o 7Z con contraseña para limitar su lectura. | **CP-40.** Activar protección, confirmar la clave y crear ambos formatos. Reabrir con clave incorrecta y correcta; verificar los datos. Comprobar que TAR no ofrece contraseña. |
| **HU-41.** Como usuario, quiero ocultar los nombres en 7Z o RAR cifrado para reducir la información visible sin clave. | **CP-41.** Crear un 7Z cifrado con **Ocultar nombres** y probar su listado sin clave y con ella. Repetir en RAR si está disponible el codificador. |
| **HU-42.** Como usuario, quiero dividir un comprimido en volúmenes para transportarlo por partes. | **CP-42.** Crear un ZIP o 7Z con volumen positivo. Verificar varias partes, reunirlas y extraer desde una parte posterior; probar un valor negativo y comprobar el aviso antes de crear. |
| **HU-43.** Como usuario, quiero decidir si reemplazo un comprimido de salida existente para controlar versiones. | **CP-43.** Guardar un comprimido con un nombre ya usado. Verificar la confirmación del selector de archivos; cancelar y comprobar el original intacto, o confirmar y comprobar que el nuevo se puede abrir. |

## Editar, copiar y convertir

| Historia | Caso de prueba |
| --- | --- |
| **HU-44.** Como usuario, quiero añadir archivos o carpetas a un comprimido editable para actualizar su contenido. | **CP-44.** Abrir ZIP, 7Z o TAR de un solo archivo y usar **+ Añadir** dentro de una carpeta interna. Verificar la ruta final y que el resultado se abre. Repetir en RAR solo si hay codificador. |
| **HU-45.** Como usuario, quiero elegir cómo tratar entradas ya presentes al actualizar un comprimido. | **CP-45.** Añadir un archivo con el mismo nombre usando, en copias separadas, **Reemplazar**, **Omitir** y **Solo más recientes**. Verificar los bytes y fechas esperados en cada copia. |
| **HU-46.** Como usuario, quiero crear una carpeta interna para ordenar el contenido del comprimido. | **CP-46.** Usar **Nueva carpeta interna…**, escribir un nombre válido y verificar que aparece y puede abrirse. Intentar un nombre inseguro y comprobar que el original se conserva. |
| **HU-47.** Como usuario, quiero renombrar una entrada para corregir su nombre sin extraerla. | **CP-47.** Seleccionar un archivo y usar `F2` o **Renombrar selección…**. Verificar el nuevo nombre, contenido intacto y respaldo si está activado. |
| **HU-48.** Como usuario, quiero eliminar entradas del comprimido para reducir su contenido. | **CP-48.** Seleccionar un archivo y una carpeta, pulsar `Supr` y confirmar. Verificar que ambos y los descendientes de la carpeta desaparecen; cancelar en otra copia y comprobar que no cambia. |
| **HU-49.** Como usuario, quiero conservar un respaldo antes de editar para poder volver atrás. | **CP-49.** Activar respaldo, editar dos veces y verificar `.bak` y el siguiente respaldo numerado. Desactivar la opción en una copia de prueba y comprobar que no se crea respaldo nuevo. |
| **HU-50.** Como usuario, quiero restaurar un respaldo para recuperar una versión anterior. | **CP-50.** Usar **Restaurar respaldo…**, elegir una copia y confirmar. Verificar que se restaura el contenido anterior y se guarda el estado desplazado; probar una copia dañada y comprobar que el actual permanece intacto. |
| **HU-51.** Como usuario, quiero establecer, cambiar o quitar la contraseña de un comprimido compatible. | **CP-51.** En copias ZIP y 7Z, establecer una clave, cambiarla y quitarla. Comprobar acceso con la clave vigente en cada etapa y que una clave incorrecta no altera el original. Repetir en RAR si hay codificador. |
| **HU-52.** Como usuario, quiero editar el comentario general de un ZIP para añadir una nota al archivo. | **CP-52.** Escribir un comentario en **Comentario ZIP…**, guardar y volver a abrir. Verificar el texto y los archivos; probar más de 65 535 bytes UTF-8 y comprobar el rechazo. |
| **HU-53.** Como usuario, quiero guardar una copia del comprimido para conservar el original. | **CP-53.** Usar **Guardar como…** con otro nombre. Comparar bytes de original y copia; intentar usar la misma ruta y comprobar el error. Con un conjunto dividido, verificar que se indica usar conversión. |
| **HU-54.** Como usuario, quiero convertir un comprimido a otro formato para compartirlo sin perder el original. | **CP-54.** Convertir un ZIP a 7Z y TAR.GZ. Verificar contenido de resultados y original intacto. Comprobar que la contraseña del nuevo archivo solo se aplica si se marca explícitamente. |

## Archivos abiertos en editores externos

| Historia | Caso de prueba |
| --- | --- |
| **HU-55.** Como usuario, quiero guardar en el comprimido los cambios hechos a una copia abierta en un editor. | **CP-55.** Abrir un TXT interno, modificarlo en su editor y volver a WinCip. Confirmar **Actualizar** y verificar el nuevo contenido en el comprimido y el respaldo configurado. |
| **HU-56.** Como usuario, quiero decidir qué hacer con cambios externos antes de cerrar, limpiar o abrir otro comprimido. | **CP-56.** Con una copia modificada, intentar cada acción. Probar **Sí**, **No** y **Cancelar** en copias separadas; verificar respectivamente guardado y continuación, descarte y continuación, o permanencia en el estado actual. |
| **HU-57.** Como usuario, quiero que la app rechace un guardado externo si el comprimido original cambió mientras editaba. | **CP-57.** Abrir un TXT interno, modificar la copia y sustituir el comprimido por otra versión antes de confirmar. Verificar el rechazo, el original nuevo intacto y la copia editada disponible para recuperarla. |

## Preferencias, ayuda e integración con Windows

| Historia | Caso de prueba |
| --- | --- |
| **HU-58.** Como usuario, quiero reabrir un comprimido reciente para continuar mi trabajo. | **CP-58.** Abrir dos comprimidos, entrar en **Recientes** y reabrir el primero. Verificar que carga correctamente; usar **Borrar historial** y comprobar que la lista queda vacía. |
| **HU-59.** Como usuario, quiero configurar formato, nivel, verificación, respaldos y política de actualización como valores iniciales. | **CP-59.** Cambiar cada opción en **Preferencias…**, guardar y reiniciar la app. Abrir los diálogos de creación y actualización; verificar que toman los valores guardados. |
| **HU-60.** Como usuario, quiero controlar el historial de recientes para no conservar rutas que no deseo. | **CP-60.** Desactivar **Recordar comprimidos recientes**, abrir un archivo y reiniciar. Verificar que la lista sigue vacía; activarlo y comprobar que se registra el siguiente archivo. |
| **HU-61.** Como usuario, quiero ajustar los límites de entradas y tamaño para procesar archivos acordes con mis recursos. | **CP-61.** Establecer límites pequeños y abrir o extraer un archivo que los exceda; verificar el error y que no queda salida parcial. Escribir un valor negativo y comprobar el rechazo; usar `0` solo en una prueba controlada. |
| **HU-62.** Como usuario, quiero consultar ayuda y versión para entender las operaciones y el producto. | **CP-62.** Abrir **Ayuda** o `F1` y **Acerca de**. Verificar que se muestran instrucciones y versión, y que cerrar los diálogos devuelve el foco a la app. |
| **HU-63.** Como usuario, quiero usar el menú clásico del Explorador para abrir, comprimir o extraer desde archivos seleccionados. | **CP-63.** Con la integración instalada, seleccionar un ZIP y después archivos normales en el Explorador. Probar abrir, extraer en carpeta, extraer aquí y añadir a un comprimido; verificar archivos y rutas finales. En Windows 11, buscar el menú clásico en **Mostrar más opciones**. |
| **HU-64.** Como usuario de Windows 11, quiero usar el menú moderno opcional para ejecutar acciones sobre una selección múltiple. | **CP-64.** En un Windows 11 que permita registrar la extensión, habilitarla y seleccionar dos comprimidos. Comprobar las acciones disponibles y ejecutar una extracción; verificar ambos resultados. Registrar como pendiente si el sistema impide activar el paquete. |
| **HU-65.** Como usuario, quiero elegir WinCip como aplicación predeterminada desde Windows sin perder una elección anterior inesperadamente. | **CP-65.** Abrir **Aplicación predeterminada y menú del Explorador…**. Verificar que se abre Configuración de aplicaciones predeterminadas y que registrar WinCip no cambia por sí solo las asociaciones protegidas; elegir una extensión manualmente y abrir un archivo desde el Explorador. |
| **HU-66.** Como usuario, quiero que las copias temporales se limpien al terminar para no acumular archivos abiertos. | **CP-66.** Abrir un archivo interno, cerrar el comprimido y comprobar que se limpia su copia cuando el visor la libera. Mantener otra ventana usando una copia y verificar que esa sesión permanece hasta cerrarla. |

## Relación con la automatización existente

La suite Python cubre principalmente el motor y partes de la interfaz: `test_archive_core.py`, `test_complete.py`, `test_advanced.py`, `test_architecture.py`, `test_interface.py`, `test_shell_actions.py`, `test_open_file.py`, `test_windows_integration.py` y `test_close_cleanup.py`. Estos casos **no sustituyen** la ejecución visual de los casos de aceptación anteriores ni una prueba directa en Windows 10. El [informe de pruebas](PRUEBAS.md) recoge lo que ya se comprobó y lo que sigue pendiente.

La [matriz de ejecución de los 66 casos](RESULTADOS_66_CASOS.md) registra la evidencia y el alcance pendiente de cada caso.

Para ejecutar la suite desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -q
```
