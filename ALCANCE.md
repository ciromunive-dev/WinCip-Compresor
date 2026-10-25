# Alcance de WinCip Compresor 3.2.0

Documento de referencia del producto. Actualizado el 25 de octubre de 2026.

## Objetivo

Aplicación gratuita de escritorio, en español, para comprimir, explorar y extraer archivos localmente en Windows 10 y 11 x64 sobre Intel/AMD. El nombre del producto es **WinCip Compresor** y el ejecutable se llama `WinCip.exe`. No requiere instalar Python ni 7-Zip por separado.

El instalador exige Windows 10 o posterior sobre Intel/AMD x64. La validación ejecutada corresponde a Windows 11; aún falta una prueba directa en Windows 10. ARM64 no está validado.

## Entregables

Los paquetes de `release/` se generan localmente con `build_release.py` y se adjuntan a las publicaciones; no se incluyen en el historial Git.

| Entregable | Ubicación | Uso |
| --- | --- | --- |
| Instalador con asistente y desinstalador | `release/WinCip-Compresor-3.2.0-Setup.exe` | Instalación por usuario, componentes opcionales y registro en Aplicaciones instaladas |
| Paquete portable | `release/WinCip-Compresor-3.2.0-Portable.zip` | Carpeta completa con programa, extensión, documentación y licencias |
| Paquete de código fuente | `release/WinCip-Compresor-3.2.0-Source.zip` | Código, pruebas, recursos y scripts de compilación; sin herramientas descargadas ni archivos privados de pruebas |
| Ejecutable | `release/WinCip.exe` | Inicio directo de la aplicación |
| Icono propio | `WinCip.ico`, `icon-preview.png` | Ballena azul de perfil con la boca y los dientes orientados hacia arriba |
| Código y compilación | Archivos Python, `shell_extension/`, `installer/`, `build_release.py` | Mantenimiento y generación de entregables |
| Licencias | `LICENSE`, `THIRD_PARTY_NOTICES.md`, `licenses/` | MIT para código propio; avisos específicos para dependencias |

## Funciones implementadas

| Área | Alcance |
| --- | --- |
| Abrir y explorar | ZIP, RAR, 7Z, TAR y variantes comprimidas, GZ/BZ2/XZ; búsqueda, navegación, ordenación y propiedades |
| Crear | ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2 y TAR.XZ; RAR mediante codificador instalado; niveles, filtros de inclusión/exclusión y verificación antes de guardar |
| Contraseñas | Leer ZIP/RAR/7Z cifrados; crear ZIP AES-256 y 7Z cifrado; ocultar nombres en 7Z; cambiar o quitar clave de ZIP/7Z, y de RAR con codificador instalado, conociendo la actual |
| Compatibilidad de claves ZIP | UTF-8 y alternativas habituales de Windows; pruebas con claves acentuadas creadas por WinRAR |
| Extraer | Todo o selección; destino nuevo o existente; renombrar, omitir o reemplazar; cancelación y reversión de mezclas ante errores manejados |
| Lotes | Cola de comprimidos, carpetas separadas, reintento, omisión y resumen; conserva resultados ya completados |
| Volúmenes | Leer conjuntos ZIP/7Z/RAR compatibles; localizar primera parte y algunos huecos; crear ZIP/7Z divididos |
| Editar | ZIP, 7Z y TAR únicos, y RAR con codificador instalado: añadir, actualizar, renombrar, eliminar y crear carpetas; reconstrucción verificada y respaldo `.bak` opcional; restauración verificada desde la interfaz |
| Copiar y convertir | Guardar copia idéntica; convertir a ZIP/7Z/TAR/TAR.GZ/TAR.BZ2/TAR.XZ y a RAR si hay codificador conservando el original; contraseña del destino elegida por separado |
| Vista previa | Texto e imágenes con límites; HTML/SVG como texto; apertura externa mediante copia temporal, detección de cambios y actualización confirmada del comprimido |
| Preferencias | Recientes, nivel, formato, verificación, respaldo, límites ajustables y políticas de conflicto; contraseñas no guardadas en preferencias |
| Windows | Abrir con, menú contextual clásico y extensión moderna opcional; no reemplaza la elección protegida de aplicación predeterminada |
| Instalación | Para usuario actual; accesos directos; actualizar una carpeta propia; desinstalar sin borrar preferencias ni archivos ajenos |

## Límites explícitos

- Crear y editar RAR requiere el codificador de una instalación de WinRAR; la lectura usa el motor incluido. No recupera contraseñas olvidadas.
- No edita directamente conjuntos divididos; primero se convierten a un archivo único editable.
- Conserva comentarios generales y por entrada y atributos de entradas ZIP al editar. No conserva todos los campos adicionales, ACL o permisos del archivo original al reconstruir.
- Rechaza enlaces, entradas especiales y rutas inseguras. Al extraer, ajusta espacios y puntos finales de nombres incompatibles con Windows; rechaza otros nombres incompatibles y colisiones tras el ajuste. Presupuesto inicial de 100 000 entradas y 50 GiB descomprimidos, ajustable en Preferencias; cero quita el tope numérico.
- Vista previa: hasta 10 MiB por archivo, primer MiB de texto y 25 millones de píxeles por imagen.
- ZIP con clave no ASCII puede tener incompatibilidades entre aplicaciones. Para compartir, usa una frase larga sin acentos o elige 7Z.
- Los cambios del editor externo se incorporan tras confirmación y comprobación de la versión del original. Las copias no constituyen almacenamiento permanente, recuperación tras cierre forzado ni borrado seguro.
- La reversión normal no garantiza recuperación ante corte de energía o terminación forzada.
- La extensión moderna necesita que Windows permita registrar su paquete. La distribución general de esa integración sigue necesitando una identidad y firma aceptadas por Windows. El menú clásico está disponible sin ese paquete.

## Identidad, licencia y distribución

Se eligió **WinCip Compresor**. El icono anterior de libros morados se sustituyó por un diseño dibujado en código. La investigación de nombres es preliminar y no equivale a una comprobación registral de marca.

El código propio usa [MIT](LICENSE). Las dependencias mantienen sus licencias y se distribuyen con sus avisos; véase [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). El repositorio está en [GitHub](https://github.com/ciromunive-dev/WinCip-Compresor).

El instalador y el ejecutable aún no tienen firma de un editor certificado. No se instalan certificados ni se modifican opciones de seguridad de Windows.

## Validación y pendientes reales

El [informe de pruebas](docs/PRUEBAS.md) registra los resultados disponibles y su alcance. Las pruebas incluyen formatos, claves, corrupción, rutas inseguras, cancelación, temporales y aislamiento del registro durante instalación/desinstalación.

Antes de anunciar una versión estable faltan pruebas en un equipo limpio y otras escalas de pantalla y firma/empaquetado definitivo de la extensión moderna. El fallo de limpieza temporal se localizó y se cubrió con reintentos acotados y pruebas de regresión; véase el informe. Los pendientes externos no se presentan como funciones terminadas.

## Documentos complementarios

- [Arquitectura implementada](docs/ARQUITECTURA.md).
- [Uso](docs/USO.md).
- [Instalación y desinstalación](docs/INSTALACION.md).
- [Limitaciones y solución de problemas](docs/LIMITACIONES.md).
- [Desarrollo y compilación](docs/DESARROLLO.md).
- [Identidad](docs/IDENTIDAD.md).
- [Cambios](CHANGELOG.md).
