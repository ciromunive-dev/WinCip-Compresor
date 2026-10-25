# Cambios

## 3.2.0

Versión de trabajo con instalador por usuario, desinstalador, paquete portable e icono propio. Quedan las validaciones en otro equipo y la firma de la integración moderna para distribución pública.

Se adoptó el icono de la ballena azul con la boca orientada hacia arriba, manteniendo la pestaña blanca separada del ojo. Se regeneraron los recursos de la app, la extensión del Explorador y el instalador.

La ventana principal ahora se abre centrada en el área útil del monitor, en lugar de quedar junto a un borde.

El logo de la interfaz se genera desde una imagen de 512 px y se ajusta al escalado de Windows; botones y espacios principales siguen la misma escala. La ventana inicial se limita al área disponible del monitor.

Se delimitó la distribución a Windows 10 y 11 x64. El menú moderno del Explorador se ofrece solo en Windows 11; Windows 10 utiliza el menú clásico y su pantalla de aplicaciones predeterminadas. Se reforzó la limpieza de temporales ante archivos que desaparecen durante la operación.

En la raíz de un comprimido, el botón de navegación ahora abre la carpeta que contiene el archivo en el Explorador de Windows; dentro del comprimido sigue subiendo a la carpeta interna superior.

La navegación interna ya permite abrir carpetas presentes en el comprimido aunque su nombre no pueda guardarse directamente en Windows, por ejemplo si termina en un espacio. La extracción ajusta los espacios y puntos finales de esos nombres antes de escribirlos, y conserva las comprobaciones contra rutas inseguras y colisiones.

### Funciones añadidas

- Capacidades compartidas entre interfaz y motor; arquitectura en `docs/ARQUITECTURA.md`.
- Creación y edición de TAR.BZ2/TAR.XZ y edición de TAR/TAR.GZ, incluidos alias.
- Creación, conversión y edición de RAR usando el codificador instalado, con claves, nombres ocultos y creación de volúmenes. El codificador no se redistribuye.
- Restauración verificada de respaldos desde la interfaz, conservando el estado actual.
- Detección y guardado confirmado de cambios de editores externos, versiones del original y protección antes de cerrar o cambiar de comprimido.
- Presupuestos de entradas y tamaño ajustables, con opción sin tope numérico por operación.
- Comentarios ZIP editables y conservación de comentarios y atributos de sus entradas al reconstruir.

- Instalador NSIS en español, componentes opcionales, accesos, registro de Aplicaciones instaladas y desinstalación que conserva archivos del usuario.
- Icono azul propio, licencia MIT y recopilación de avisos de terceros.
- Documento `ALCANCE.md` y generación conjunta de instalador, portable y hashes con `build_release.py`.

- Edición de 7Z, además de ZIP: añadir y actualizar contenido, renombrar, eliminar y crear carpetas internas.
- Cambio y eliminación de contraseñas en ZIP y 7Z conociendo la clave actual.
- Respaldos numerados antes de editar y políticas de actualización: reemplazar, omitir o añadir solo versiones más recientes.
- Creación de TAR y TAR.GZ, filtros de inclusión/exclusión y verificación opcional antes de guardar.
- Conversión a ZIP, 7Z, TAR y TAR.GZ conservando el original, y copia completa mediante **Guardar como…**.
- Vista previa de texto e imágenes, propiedades, copia de rutas internas e historial de navegación.
- Preferencias para verificación, respaldos e historial de recientes.
- Recuperación de errores en lotes mediante reintento, omisión o cancelación, con resumen de resultados.

### Correcciones y comportamiento

- Los diálogos ajustan su ancho y el texto al área útil del monitor; en escalas altas mantienen accesibles los controles mediante desplazamiento vertical y, para vistas previas anchas, horizontal.
- Limpieza de carpetas de operación con reintentos acotados para bloqueos y WinError 145; regresiones con bloqueos reales y creación concurrente.
- Lectura, verificación y edición de ZIP con contraseñas en codificaciones habituales de Windows, incluidos los ZIP probados de WinRAR con «ñ» y tildes; consejo de compatibilidad al crear una clave ZIP.
- Informe JSON con detalle del error cuando falla la comprobación del ejecutable.
- Búsqueda de la primera parte de conjuntos divididos, detección de huecos y agrupación de partes para evitar procesarlas repetidamente.
- Distinción en la extensión nativa entre carpetas físicas con extensión `.zip` y archivos ZIP virtuales del Explorador.
- Nombres de carpetas de extracción ajustados para conjuntos multipartes.
- Propagación del identificador de zona disponible de archivos descargados a los resultados compatibles.
- Diálogos con contenido desplazable para pantallas pequeñas y estilos compartidos.
- DLL de la extensión versionada como `WinCipShell-3.2.dll` y manifiesto actualizado a `3.2.0.0`.
- Registro de desarrollo que evita repetir innecesariamente el alta de un paquete con la misma versión, ubicación y estado correcto.

### Documentación

- Nombre visible elegido: **WinCip Compresor**. Se conservan el ejecutable `WinCip.exe` y los identificadores de Windows existentes.

- README actualizado a 3.2.0 y texto dañado corregido.
- Guías de uso, desarrollo, limitaciones y solución de problemas.
- Aclaraciones sobre cifrado en conversiones, copias temporales, respaldos, metadatos y alcance de los scripts de la extensión.
