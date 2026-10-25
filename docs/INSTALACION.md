# Instalación de WinCip Compresor

## Instalador

En Windows 10/11 de 64 bits sobre Intel/AMD, ejecuta `WinCip-Compresor-3.2.0-Setup.exe` desde una publicación o desde `release/` si compilaste el proyecto. El asistente está en español y copia la aplicación y su documentación en `%LOCALAPPDATA%\Programs\WinCip` de forma predeterminada. Es una instalación para el usuario actual, sin necesidad de administrar el equipo.

El asistente permite seleccionar la integración del Explorador y un acceso directo en el escritorio. Crea accesos en Inicio y aparece en **Configuración → Aplicaciones → Aplicaciones instaladas**. No requiere Python ni una instalación separada de 7-Zip. Para actualizar, cierra WinCip y ejecuta el instalador sobre su carpeta existente.

El destino debe estar vacío o ser una carpeta creada por este instalador. No selecciones la carpeta del código fuente ni una carpeta de documentos. El instalador evita mezclar sus archivos con una carpeta ajena.

Si instalaste una edición x86 experimental anterior en la misma carpeta, desinstálala primero. El instalador impide mezclar sus binarios con la edición x64.

## Menú contextual y asociaciones

**Menú del Explorador y opción Abrir con** registra las capacidades de WinCip y un submenú clásico. En Windows 11 se encuentra en **Mostrar más opciones**. Conserva la aplicación predeterminada actual; para cambiarla utiliza la configuración de Windows.

**Menú moderno de Windows 11** aparece solo en el instalador x64 y es un componente opcional, desactivado inicialmente. Intenta registrar la extensión existente. Si Windows no permite registrar el paquete, informa del resultado y conserva las acciones clásicas. No activa el modo de desarrollador, no instala certificados y no cambia la seguridad del sistema. La integración moderna para distribución pública con firma sigue pendiente.

## Portable

Extrae `WinCip-Compresor-3.2.0-Portable.zip` en Windows 10/11 x64 y ejecuta `WinCip.exe`. Conserva el resto de los archivos si vas a registrar la extensión. Las preferencias se guardan en el perfil de usuario incluso usando el paquete portable.

## Desinstalar

Usa **Aplicaciones instaladas**, el acceso **Desinstalar** de Inicio o `Desinstalar.exe` dentro de la carpeta del programa. Cierra antes WinCip y cualquier archivo del programa que tengas abierto.

El desinstalador retira los archivos que instaló, sus accesos y las asociaciones que todavía apuntan a esa instalación. Conserva tus comprimidos, documentos y preferencias de `%APPDATA%\WinCip`. Tampoco borra otros archivos que hayas puesto en la carpeta de instalación. Un paquete del Explorador registrado desde otra ubicación no se retira.

## Automatización y pruebas

Instalación silenciosa: `/S`. Para una prueba aislada de archivos sin integración ni accesos: `/S /NOINTEGRATION /NOSTARTMENU /D=RUTA_ABSOLUTA`, con `/D=` como último argumento. La desinstalación silenciosa usa `Desinstalar.exe /S`.

Los binarios todavía no tienen firma de un editor certificado. Las sumas SHA-256 se generan en `release/SHA256SUMS.txt` y se adjuntan a la publicación junto con los paquetes; no equivalen a una firma digital.
