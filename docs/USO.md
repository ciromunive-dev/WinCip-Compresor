# Guía de uso de WinCip Compresor 3.2.0

[Volver al README](../README.md) · [Limitaciones](LIMITACIONES.md) · [Desarrollo](DESARROLLO.md)

## Abrir y explorar

Pulsa **Abrir**, usa `Ctrl+O` o arrastra un único comprimido a la ventana. El doble clic desde el Explorador lo abre con WinCip cuando Windows lo tiene seleccionado como aplicación para ese tipo de archivo. Arrastrar varios archivos prepara una lista para comprimir; para extraer varios utiliza la acción de lotes.

Dentro de un comprimido, haz doble clic en una carpeta para entrar. Puedes escribir una ruta interna en la barra de ubicación y pulsar `Enter`. Las flechas permiten retroceder y avanzar; **↑ Subir** vuelve a la carpeta superior. En la raíz, el botón cambia a **↗ Carpeta** y abre en el Explorador de Windows la carpeta donde está guardado el comprimido. La búsqueda recorre las rutas de todo el comprimido, no solo la carpeta visible.

Pulsa el encabezado de una columna para ordenar. **Comprimido** y **Ahorro** solo muestran datos cuando el formato los proporciona. En la vista normal, las carpetas muestran el tamaño acumulado de su contenido.

**··· → Propiedades** muestra los datos de un elemento si seleccionas uno; sin selección o con varios muestra los del comprimido. **Copiar ruta interna** copia los nombres seleccionados, no rutas de archivos ya extraídos en Windows.

## Vista previa y apertura de archivos internos

Selecciona un archivo y usa **··· → Vista previa**. Admite texto e imágenes de hasta 10 MiB; el texto se limita al primer MiB y las imágenes a 25 millones de píxeles. Los documentos HTML y SVG se muestran como texto. La vista previa no ejecuta su contenido.

El doble clic o `Enter` sobre un archivo interno tiene otro comportamiento: extrae una copia temporal de ese archivo y la abre con su aplicación predeterminada de Windows. WinCip pide confirmación para las extensiones que identifica como ejecutables o scripts.

Al guardar un documento en su editor y volver a WinCip, la app detecta cambios en la copia y ofrece actualizar el comprimido. También puedes usar **··· → Actualizar desde editores externos…**. Se conserva el respaldo si está activado y se verifica el resultado. Si el original cambió desde la apertura, se rechaza la actualización para evitar sobrescribir otra versión: guarda tu documento fuera del temporal y resuelve el conflicto.

Al cerrar, cambiar el comprimido o preparar otro archivo, los cambios pendientes se pueden guardar, descartar o dejar intactos cancelando la salida. Un error al guardar conserva las copias. No cierres forzadamente WinCip mientras estés editando: esta función requiere mantener abierta su sesión.

## Extraer

**Extraer** procesa todo el contenido. **Extraer selección** o `Ctrl+E` procesa los archivos y carpetas seleccionados.

Elige la carpeta de destino y si quieres una subcarpeta nueva o utilizar el destino existente. Una carpeta nueva recibe un nombre disponible. Al utilizar un destino existente, puedes elegir:

| Opción | Resultado |
| --- | --- |
| Renombrar | Conserva el archivo existente y da otro nombre al extraído. |
| Omitir | Conserva el existente y no extrae el archivo que coincide. |
| Reemplazar | Sustituye el archivo existente por el extraído. |

WinCip prepara y valida el contenido antes de incorporarlo al destino. Si una mezcla falla o se cancela, intenta revertir los cambios realizados por esa operación. Esto no sustituye a un respaldo ni garantiza recuperación ante un corte de energía o la terminación forzada del proceso.

Se conservan las fechas de modificación disponibles de los archivos. Consulta las [limitaciones de metadatos](LIMITACIONES.md) antes de usarlo para copias de seguridad.

## Crear un comprimido

1. Utiliza **+ Añadir** para escoger archivos o una carpeta. También puedes arrastrarlos a la ventana.
2. Revisa la lista; `Supr` quita los elementos seleccionados de esa lista.
3. Pulsa **Crear comprimido** y elige ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2 o TAR.XZ. RAR aparece si está instalado su codificador.
4. Configura el nivel, la protección y los volúmenes disponibles para ese formato.
5. Elige el destino, fuera de las carpetas que estás comprimiendo.

Los niveles son **Sin compresión**, **Rápida**, **Equilibrada** y **Máxima**. TAR almacena el contenido sin compresión; TAR.GZ sí permite elegir el nivel. Una compresión mayor puede tardar más y no reduce necesariamente todos los tipos de archivo.

**Verificar antes de guardar** está activado de forma predeterminada. Cuando está marcado, el resultado se comprueba antes de pasar a su nombre definitivo. Si el destino ya existe, la interfaz pide la confirmación habitual para reemplazarlo. Las carpetas de volúmenes existentes no se reemplazan: utiliza otro nombre.

### Filtros

En el diálogo de creación, **Elegir filtros de inclusión y exclusión…** permite escribir patrones separados por punto y coma:

```text
Incluir: *.pdf; *.txt
Excluir: cache; *.tmp
```

Deja **Incluir** vacío para incluirlo todo. Los patrones se comparan sin distinguir mayúsculas con la ruta relativa o sus componentes. Excluir una carpeta excluye su contenido. Estos filtros pertenecen a la creación; no son filtros de extracción.

### Contraseñas

Activa **Proteger con contraseña** y escribe la clave dos veces. El diálogo permite mostrarla para revisarla.

- ZIP se crea con AES-256; los nombres de sus archivos siguen visibles.
- 7Z y RAR permiten activar **Ocultar nombres de archivos** además del cifrado del contenido; escribir RAR necesita el codificador instalado.
- Los formatos TAR no ofrecen contraseña.

Al abrir, verificar o extraer un ZIP, RAR o 7Z cifrado, WinCip solicita la contraseña cuando la necesita. Si es incorrecta, permite reintentar. Las contraseñas de la sesión no se escriben en el archivo de preferencias. No hay recuperación de claves olvidadas.

WinCip admite claves ZIP en UTF-8 y prueba también codificaciones habituales de Windows al leer ZIP de otros programas. Para compartir ZIP entre aplicaciones, una clave con tildes, «ñ» u otros caracteres no ASCII puede producir incompatibilidades: utiliza una frase larga con letras sin acentos, números y símbolos, o elige 7Z si necesitas esos caracteres. WinCip sigue permitiendo crear ZIP con claves Unicode.

### Volúmenes

En ZIP, 7Z y RAR, **Volumen en MB** acepta `0` para un archivo único o un entero positivo para dividirlo. La unidad del campo equivale a 1 048 576 bytes, es decir, un MiB. RAR necesita su codificador instalado y usa nombres `partNN.rar`.

Por ejemplo, al crear `Fotos.7z` dividido, las partes se guardan en `Fotos.7z.parts`, con nombres como `Fotos.7z.001` y `Fotos.7z.002`. Los ZIP divididos creados por WinCip usan `.zip.001`, no el esquema `.z01` de otros programas.

Conserva todas las partes en la misma carpeta y no les cambies el nombre. Puedes seleccionar una parte posterior: WinCip busca la primera en conjuntos numerados, RAR `partNN` y conjuntos antiguos `.r00` o `.z01`. Detecta algunos huecos en la numeración, pero una última parte ausente puede manifestarse como archivo incompleto durante la lectura.

## Editar comprimidos

Las acciones de edición aparecen al abrir un ZIP, 7Z o TAR de un solo archivo, o un RAR si está instalado Rar.exe. Puedes añadir o actualizar archivos y carpetas, crear una carpeta interna, renombrar con `F2` o eliminar con `Supr`. Las adiciones se colocan en la carpeta interna actual.

Al actualizar, elige **Reemplazar**, **Omitir** o **Solo más recientes**. Esta última opción compara las fechas de modificación con una tolerancia de dos segundos.

Cada operación reconstruye el comprimido, verifica el resultado y después sustituye el original. Los cambios se aplican al finalizar cada operación; no existe una sesión de cambios pendientes que debas guardar con `Ctrl+S`. Necesitas espacio para el contenido descomprimido, el nuevo comprimido y, si está activado, el respaldo.

### Respaldos y restauración

**Crear respaldo antes de editar** está activado inicialmente en **Preferencias**. El original se conserva como `Datos.zip.bak`; los siguientes respaldos usan `.bak.2`, `.bak.3`, etc.

Para restaurar, usa **··· → Restaurar respaldo…** y elige una de las copias del comprimido abierto. Se verifica primero, solicita su contraseña si corresponde y conserva el estado actual en otro respaldo antes de reemplazarlo. Un error o una cancelación conserva el archivo actual.

### Cambiar o quitar la contraseña

Usa **··· → Cambiar o quitar contraseña…**. Para un comprimido protegido necesitas conocer su clave actual. Puedes establecer una nueva o elegir **Quitar contraseña**, que requiere confirmar que el resultado quedará sin protección. La operación reconstruye y verifica el archivo completo.

Los conjuntos divididos no se editan directamente. Conviértelos antes a un ZIP o 7Z de un solo archivo.

## Copiar y convertir

**Guardar como…** hace una copia completa del comprimido actual. Conserva formato y cifrado; escribir otra extensión no lo convierte. No reúne conjuntos divididos. La copia tampoco es un mecanismo para recuperar cambios de un editor externo.

**Convertir formato…** crea un ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2 o TAR.XZ nuevo, o un RAR si está instalado su codificador, y conserva el original. El destino debe tener un nombre que todavía no exista y el resultado se verifica antes de guardarlo.

**La protección del original no se hereda automáticamente en una conversión.** Para obtener una copia cifrada, elige ZIP o 7Z y activa **Proteger la nueva copia con contraseña**. Los destinos TAR quedan sin cifrar. RAR permite cifrado cuando está disponible su codificador.

## Lotes, verificación y cancelación

**··· → Extraer varios comprimidos…** permite elegir varios archivos y un destino común. Cada conjunto se procesa una vez y recibe una carpeta nueva. Solicita las contraseñas necesarias para cada comprimido.

Si uno falla, puedes **Reintentar**, **Omitir y continuar** o **Cancelar**. El resumen distingue los resultados completados, omitidos y pendientes. Cancelar no elimina los resultados de comprimidos que ya terminaron correctamente.

**··· → Verificar comprimido** intenta leer todo el contenido. En formatos con CRC o autenticación también comprueba esos datos. TAR por sí solo no aporta una comprobación de integridad del contenido de cada archivo.

Durante una operación puedes pulsar **Cancelar**. Espera a que finalice la cancelación antes de cerrar la ventana. Algunas fases del motor externo no proporcionan un porcentaje detallado; la velocidad y el tiempo restante son estimaciones cuando hay progreso en bytes.

## Preferencias y recientes

**··· → Preferencias…** permite configurar formato, nivel, verificación al crear, respaldo al editar, política de actualización, historial y presupuestos de entradas y GiB por operación. Escribe cero para quitar un tope numérico; las validaciones de rutas siguen activas. **Recientes** conserva hasta diez rutas y permite borrarlas. Desactivar el historial también borra la lista guardada.

Las preferencias se guardan en `%APPDATA%\WinCip\settings.json`. No contienen las contraseñas. También se recuerdan el último destino y las opciones de conflictos de extracción.

## Explorador de Windows

La integración clásica añade un submenú **WinCip Compresor** al Explorador de Windows 10 y 11; en Windows 11 aparece en **Mostrar más opciones**. La extensión moderna opcional para Windows 11 x64 muestra acciones en el menú principal y admite selecciones múltiples. Sobre comprimidos ofrece **Abrir con WinCip Compresor**, **Extraer archivos…**, **Extraer en…** y **Extraer aquí**. Sobre otros archivos y carpetas ofrece **Añadir a un comprimido…**.

**Extraer aquí** renombra los archivos que ya existen para conservarlos. **Extraer en…** crea una carpeta con un nombre disponible junto al comprimido. **Extraer archivos…** permite elegir el destino.

La integración se registra por separado y necesita conservar el ejecutable, la DLL y el manifiesto en una ubicación estable. La acción **Aplicación predeterminada y menú del Explorador…** registra WinCip y abre la configuración de Windows, donde eliges las asociaciones. No la uses como una acción de consulta: puede registrar o actualizar la extensión. El instalador ofrece la integración clásica y, de forma opcional, intenta registrar la moderna cuando Windows lo permite. Consulta [Instalación](INSTALACION.md).

## Atajos

| Atajo | Acción |
| --- | --- |
| `Ctrl+O` | Abrir un comprimido |
| `Ctrl+E` | Extraer selección |
| `Ctrl+A` | Seleccionar todos los elementos de la lista; en un campo de texto conserva su función habitual |
| `Enter` | Entrar en una carpeta o abrir el archivo interno seleccionado |
| `F2` | Renombrar un elemento en un comprimido editable |
| `Supr` | Eliminar del comprimido editable, o quitar de la lista de creación |
| `Alt+←` / `Alt+→` | Retroceder / avanzar por carpetas internas |
| `Alt+↑` | Subir una carpeta |
| `F1` | Abrir la ayuda |
