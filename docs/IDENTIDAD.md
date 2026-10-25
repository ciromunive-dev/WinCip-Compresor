# Identidad de WinCip Compresor

El 22 de octubre de 2026, el usuario eligió **WinCip Compresor** como nombre visible de la aplicación. Se aplica a la ventana, diálogos, información del producto y etiquetas de integración. `WinCip.exe`, las rutas de preferencias, los identificadores de asociaciones y la identidad técnica del paquete se conservan para mantener la compatibilidad.

Las búsquedas siguientes se guardan como antecedentes. No constituyen una comprobación registral de marca y no se han reservado dominios ni creado cuentas.

## Hallazgos comprobados

| Fuente | Hallazgo | Alcance |
| --- | --- | --- |
| [Repositorio plerk/wincip](https://github.com/plerk/wincip) | Scripts Perl que generan, construyen y publican imágenes Docker de Windows con herramientas de desarrollo, especialmente Perl. La API del repositorio registra su última subida en diciembre de 2019. | No es un compresor. Un nombre de repositorio se asigna dentro de la cuenta de su propietario, no de forma exclusiva en todo GitHub. La coincidencia por sí sola no justifica descartar el nombre para este proyecto. |
| [Documento de Ingélux sobre iluminación de la Gioconda](https://www.ingelux.com/wp-content/uploads/2017/09/Lampe-Joconde-Toshiba-Ingelux-English.pdf) | Describe un software de configuración llamado WINCIP para un controlador de AELSYS. | Evidencia de uso anterior del nombre en software; no demuestra que ese producto continúe activo. |
| [Página del fabricante Winthrox](https://winthrox.com/wincip/) | Publica WinCip como nombre de un producto de otro sector. | El nombre tampoco es único fuera del software. |

La consulta de repositorios de la API de GitHub devolvió `plerk/wincip` al buscar `wincip in:name`. Los resultados de una búsqueda pública no son un registro completo de nombres o marcas. No se ha confirmado la disponibilidad del dominio `wincip.com` ni se ha completado una búsqueda de marcas registradas por territorio y clase.

No se encontró en las consultas realizadas un compresor claramente identificado como producto independiente bajo ese nombre. Algunas menciones antiguas en foros parecen errores al escribir WinZip o WinSCP; no se han contado como productos verificados.

## Alternativas revisadas

El usuario eligió buscar un nombre alternativo. Se hizo un primer filtro de coincidencias exactas en búsquedas públicas, repositorios públicos de GitHub y registros de dominios `.com` mediante RDAP de Verisign.

| Nombre | Software en las búsquedas realizadas | Repositorios públicos con el texto en el nombre | Consulta del dominio `.com` | Propuesta |
| --- | --- | --- | --- | --- |
| **NivZip** | Sin producto identificado con ese nombre exacto | 0 | HTTP 404, sin registro devuelto | Preferido: corto, escrito sin acentos y vinculado a la compresión |
| **TivZip** | Sin producto identificado con ese nombre exacto | 0 | HTTP 404, sin registro devuelto | Alternativa de seis letras, también sin acentos |

Las comprobaciones se realizaron el 22 de octubre de 2026, hora de Lima. Los resultados cambian con el tiempo. La ausencia de resultados y una respuesta RDAP 404 no garantizan que se pueda registrar un dominio o una marca, ni cubren proyectos privados o sin indexar. No se han comprobado todos los dominios, nombres de usuario o registros de marcas.

Fuentes directas de las consultas:

- NivZip: [API de repositorios de GitHub](https://api.github.com/search/repositories?q=nivzip%20in%3Aname&per_page=10) y [RDAP de nivzip.com](https://rdap.verisign.com/com/v1/domain/nivzip.com).
- TivZip: [API de repositorios de GitHub](https://api.github.com/search/repositories?q=tivzip%20in%3Aname&per_page=10) y [RDAP de tivzip.com](https://rdap.verisign.com/com/v1/domain/tivzip.com).

### Nombres descartados del primer filtro

- **BriZip:** ya hay una [aplicación de compresión en la App Store](https://apps.apple.com/jp/app/brizip/id6804677271?mt=12).
- **Zelzip:** existe el [proyecto ZELZIP](https://github.com/ZELZIP/ZELZIP).
- **Vezip:** la API de GitHub devolvió el repositorio `rohinomiya/VEZip`, además de coincidencias parciales, y [vezip.com tiene registro RDAP](https://rdap.verisign.com/com/v1/domain/vezip.com).
- **Cajip:** existen repositorios con ese texto y [cajip.com tiene registro RDAP](https://rdap.verisign.com/com/v1/domain/cajip.com).

Los informes detallados de las consultas están en `build/identity-candidates.json` y `build/identity-shortlist.json`; son evidencias locales y no archivos necesarios para usar la aplicación.

## Otras propuestas revisadas

El usuario propuso también **CinRar**. En la comprobación realizada, [cinrar.com](https://cinrar.com/) es una web activa de servicios de desarrollo web y comercio electrónico de Turquía, vinculada a la [cuenta cinrar-official de GitHub](https://github.com/cinrar-official). La consulta RDAP devuelve el dominio registrado. No se identificó un compresor llamado CinRar en las búsquedas realizadas; sí existe este uso comercial en servicios digitales. No se ha realizado una comprobación registral de marca para ese nombre.

La elección final para el producto es **WinCip Compresor**. No se aplicarán CinRar, NivZip ni TivZip.

El icono de libros morados se sustituyó por una ballena azul de perfil: la boca con dientes apunta hacia arriba y una pestaña blanca queda separada del ojo. `build_assets.py` genera el ICO, los PNG de la interfaz y la extensión, y los BMP del instalador. El instalador y el portable están en `release/`; la firma de distribución pública de la extensión moderna sigue pendiente.
