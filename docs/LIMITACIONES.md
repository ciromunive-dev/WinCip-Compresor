# Limitaciones y solución de problemas

[Volver al README](../README.md) · [Guía de uso](USO.md) · [Desarrollo](DESARROLLO.md)

## Alcance de esta versión

La versión 3.2.0 se distribuye para Windows 10 y 11 x64 sobre Intel/AMD con Python 3.11 y 7-Zip x64. La extensión moderna del Explorador requiere Windows 11. El paquete se probó en Windows 11; la prueba directa en Windows 10 sigue pendiente.

Los iconos y espacios principales se adaptan al escalado de Windows y la ventana inicial se limita al área disponible. Se inspeccionó visualmente en Windows 11 con escala del 175 %. Las resoluciones muy bajas combinadas con escala alta pueden dejar poco espacio para todo el contenido y no se han validado en un monitor físico.

Existe un instalador NSIS en español con desinstalador y una distribución portable. El icono es propio y el código del proyecto usa MIT. El ejecutable, el instalador y la DLL aún no tienen firma de un editor certificado. La extensión moderna usa un manifiesto de desarrollo; su distribución general firmada sigue pendiente. El menú clásico funciona sin ese paquete.

## Formatos y metadatos

WinCip crea y edita ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2 y TAR.XZ de un solo archivo. También crea y edita RAR cuando detecta el codificador Rar.exe de una instalación de WinRAR; ese codificador no se incluye en la distribución. Detecta cambios en copias de editores externos y ofrece actualizarlos con confirmación. No edita directamente conjuntos de volúmenes ni recupera contraseñas olvidadas.

La compatibilidad con métodos de compresión o cifrado particulares depende de las bibliotecas y del motor incluido. Un formato reconocido no garantiza que todas sus variantes puedan procesarse.

ZIP no identifica de forma uniforme la codificación de las contraseñas. WinCip crea sus claves ZIP en UTF-8 y, al leer, prueba también codificaciones habituales de Windows. Esto corrige los ZIP probados de WinRAR con tildes o «ñ», pero no cubre todas las codificaciones regionales posibles. En las pruebas, 7-Zip para Windows rechazó un ZIP UTF-8 de WinCip con clave no ASCII que WinRAR sí pudo abrir. Para compartir entre programas, utiliza una clave ZIP sin acentos o el formato 7Z. El [autor de 7-Zip explica esta limitación de las claves ZIP](https://sourceforge.net/p/sevenzip/discussion/45798/thread/845dc7c001/).

La reconstrucción al editar o convertir puede cambiar el método o nivel de compresión y no conserva necesariamente campos adicionales ni todos los metadatos propios del programa de origen. Al editar ZIP se conservan el comentario general, comentarios de entradas, sistema creador y atributos de entradas; el comentario general se puede editar desde el menú. No mantiene contraseñas diferentes por archivo; el resultado utiliza la contraseña elegida para el conjunto. Los ZIP cifrados reconstruidos utilizan AES. Los nombres de un ZIP siguen siendo visibles.

La extracción conserva las fechas de modificación disponibles de los archivos. No restaura ACL ni permisos de Windows. En extracciones a carpetas nuevas puede restaurar fechas de directorios disponibles; al mezclar con un destino existente no restaura todas las fechas de directorios. Tampoco se garantiza conservar todos los atributos o flujos alternativos del original.

## Validaciones y límites

WinCip permite explorar las rutas internas de un comprimido aunque una carpeta tenga un nombre incompatible con Windows. Al extraer, quita los espacios y puntos finales de los componentes del nombre para poder guardar los archivos en Windows; el nombre dentro del comprimido no cambia. Si dos rutas terminan con el mismo nombre tras este ajuste, la extracción se detiene antes de escribir el destino. Siguen rechazándose las rutas que escapen del destino, otros nombres incompatibles con Windows, enlaces, puntos de reanálisis, entradas especiales y rutas duplicadas sin distinguir mayúsculas. La edición conserva los nombres originales y exige que sean válidos para Windows.

Los presupuestos predeterminados son 100 000 entradas y 50 GiB de contenido descomprimido por operación. Se pueden aumentar en Preferencias o establecer en cero para quitar el tope numérico; esto no elimina las validaciones de rutas ni tamaños. Las comprobaciones también vigilan los bytes leídos; los tamaños declarados en un comprimido no se consideran suficientes por sí solos. Las rutas largas continúan dependiendo de Windows y de los componentes utilizados.

La vista previa admite archivos de hasta 10 MiB, texto limitado al primer MiB e imágenes de hasta 25 millones de píxeles. GIF y otros formatos con varias imágenes no se reproducen como animaciones.

Las operaciones de edición y conversión necesitan espacio para el contenido sin comprimir y un resultado nuevo. Un respaldo aumenta el espacio necesario. Las comprobaciones previas de espacio no garantizan que otra aplicación no lo consuma durante la operación.

Los RAR y 7Z sólidos pueden tardar más porque algunas operaciones extraen entradas por separado. Ciertas fases de 7-Zip no ofrecen progreso detallado. Una barra indeterminada no significa por sí sola que el programa esté bloqueado.

## Archivos descargados, contraseñas y temporales

El procesamiento es local. Las preferencias guardan rutas y opciones, no contraseñas. Las claves se mantienen para las operaciones de la sesión; cuando se usa el motor externo, se le pasan como argumento de su proceso. No debe interpretarse como una garantía de que otros procesos con permisos suficientes no puedan observarlas.

Cuando el archivo de origen tiene una marca de zona de Internet o de sitios restringidos, WinCip intenta propagar su identificador de zona a los archivos extraídos en sistemas que admiten flujos alternativos. No conserva todos los datos de procedencia ni sustituye a un antivirus. Abrir un archivo interno con su aplicación de Windows puede ejecutar funciones propias de esa aplicación; la vista previa de WinCip se limita a texto e imágenes.

Las copias abiertas y las vistas previas usan carpetas aisladas bajo `%TEMP%\ArchivoFacil\Opened`. Ese nombre interno procede de una versión anterior. Se limpian al cerrar el comprimido, cambiarlo o cerrar la ventana, respetando las sesiones de otras ventanas y los comprimidos anidados abiertos.

Si una aplicación bloquea una copia, un auxiliar sin ventana vuelve a intentar borrarla cuando queda disponible. Al iniciar, WinCip intenta limpiar sesiones abandonadas de más de una hora. No es una limpieza general de la carpeta temporal de Windows ni un temporizador que borre archivos activos cada hora. El borrado de temporales no equivale a un borrado seguro del disco.

## Problemas frecuentes

| Síntoma | Qué revisar |
| --- | --- |
| Contraseña incorrecta | Revisa mayúsculas, distribución del teclado y espacios. Reintenta mostrando la clave si lo necesitas. Un archivo dañado también puede impedir leer contenido cifrado. |
| Falta un volumen o archivo incompleto | Reúne todas las partes, conserva sus nombres y vuelve a descargar la que falte. WinCip puede identificar huecos, pero no siempre conoce el nombre de una última parte ausente. |
| No aparecen opciones de edición | Comprueba que abriste un archivo único editable. Para editar RAR se necesita Rar.exe instalado; para un conjunto dividido, crea antes una conversión a un archivo único. |
| El destino de conversión ya existe | Elige un nombre nuevo. La conversión conserva el original y no reemplaza otro archivo. |
| Ya existe la carpeta `.parts` | Usa otro nombre para el conjunto nuevo. No mezcles sus partes con las de una creación anterior. |
| Archivo en uso o acceso denegado | Cierra el visor/editor que lo mantiene abierto y comprueba permisos del destino. No fuerces la eliminación de copias que aún estás editando. |
| Falta de espacio | Libera espacio tanto en el destino como en la ubicación temporal. Ten en cuenta el contenido descomprimido y el respaldo. |
| Nombre o ruta no admitidos | Revisa los límites anteriores. Utiliza un destino más corto si el problema es la longitud de ruta. |
| El editor cambió el documento pero el comprimido sigue igual | Vuelve a WinCip y acepta la actualización, o usa Actualizar desde editores externos. Si el comprimido cambió desde la apertura, conserva el documento fuera del temporal para resolver el conflicto. |
| No aparece el menú de Windows 11 | Comprueba el registro y la ubicación de la extensión según la guía de desarrollo. Copiar solo el EXE no registra la extensión. |

Ante un error o una cancelación, espera a que la operación termine antes de reintentar. Los resultados anteriores de un lote permanecen en el destino. La reversión de una mezcla cubre los errores manejados y la cancelación normal; un cierre forzado o fallo del sistema puede requerir revisar el destino y restaurar un respaldo.
