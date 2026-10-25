"""Volume names, downloaded-file provenance and user-facing operation errors."""
from pathlib import Path
import errno
import re
import zipfile

class MissingVolumeError(ValueError):
    pass


def resolve_volume(path):
    path = Path(path).absolute()
    name = path.name
    numeric = re.match(r'^(.*\.)(\d{3,})$', name)
    rar = re.match(r'^(.*\.part)(\d+)(\.rar)$', name, re.I)
    if numeric or rar:
        match = numeric or rar
        prefix, digits = match.group(1), match.group(2)
        suffix = '' if numeric else match.group(3)
        width = len(digits)
        first = path.with_name(prefix + str(1).zfill(width) + suffix)
        if not first.is_file():
            raise MissingVolumeError('Falta la primera parte: ' + first.name + '. Coloca todas las partes en la misma carpeta.')
        numbers = []
        pattern = re.compile(re.escape(prefix) + r'(\d+)' + re.escape(suffix) + '$', re.I)
        for item in path.parent.iterdir():
            found = pattern.fullmatch(item.name)
            if found and item.is_file():
                numbers.append(int(found.group(1)))
        for index in range(1, max(numbers, default=1) + 1):
            if index not in numbers:
                raise MissingVolumeError('Falta el volumen: ' + prefix + str(index).zfill(width) + suffix)
        return first
    if re.search(r'\.(?:r\d\d|z\d\d)$', name, re.I):
        first = path.with_suffix('.rar' if name.lower()[-3] == 'r' else '.zip')
        if not first.exists():
            raise MissingVolumeError('Falta la primera parte: ' + first.name)
        return first
    return path


def volume_key(path):
    path = Path(path).absolute()
    name = re.sub(r'(\.part)\d+(\.rar)$', r'\g<1>1\2', path.name, flags=re.I)
    name = re.sub(r'\.\d{3,}$', '.001', name)
    if re.search(r'\.r\d\d$', name, re.I):
        name = name[:-4] + '.rar'
    if re.search(r'\.z\d\d$', name, re.I):
        name = name[:-4] + '.zip'
    return str(path.with_name(name)).casefold()


def archive_stem(path):
    name = Path(path).name
    name = re.sub(r'\.(?:\d{3,}|r\d\d|z\d\d)$', '', name, flags=re.I)
    for suffix in ('.tar.gz', '.tar.bz2', '.tar.xz', '.zip', '.7z', '.rar', '.tgz', '.tbz2', '.txz', '.tar', '.gz', '.bz2', '.xz'):
        if name.lower().endswith(suffix):
            name = name[:-len(suffix)]
            break
    return re.sub(r'\.part\d+$', '', name, flags=re.I) or 'Extraído'


def downloaded_zone(path):
    try:
        data = Path(str(path) + ':Zone.Identifier').read_bytes()[:8192]
        match = re.search(rb'(?im)^ZoneId\s*=\s*([34])\s*$', data)
        return int(match.group(1)) if match else None
    except OSError:
        return None


def propagate_zone(source, target):
    zone = downloaded_zone(source)
    if zone:
        try:
            Path(str(target) + ':Zone.Identifier').write_bytes(f'[ZoneTransfer]\r\nZoneId={zone}\r\n'.encode('ascii'))
        except OSError as exc:
            # Filesystems without named streams cannot store Windows provenance.
            if getattr(exc, 'winerror', None) not in (1, 50, 123) and exc.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise


DANGEROUS_EXTENSIONS = {'.exe', '.com', '.scr', '.msi', '.msp', '.bat', '.cmd', '.ps1', '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh', '.hta', '.lnk', '.url', '.reg', '.cpl', '.chm', '.pif', '.appref-ms', '.jar', '.py', '.pl', '.rb', '.sh', '.scf'}


def error_text(error):
    if isinstance(error, MissingVolumeError):
        return str(error)
    if isinstance(error, PermissionError):
        return 'Windows no permite acceder al archivo o a la carpeta. Comprueba los permisos y si otro programa lo está usando.'
    if isinstance(error, FileNotFoundError):
        return 'No se encuentra el archivo o la carpeta: ' + str(error.filename or error)
    if isinstance(error, OSError):
        if error.errno == errno.ENOSPC or getattr(error, 'winerror', None) in (39, 112):
            return 'No hay espacio suficiente en el disco. Libera espacio en el destino y vuelve a intentarlo.'
        if getattr(error, 'winerror', None) in (32, 33):
            return 'Otro programa está usando el archivo. Ciérralo y vuelve a intentarlo.'
    if isinstance(error, NotImplementedError):
        return 'Este método de compresión o cifrado no está admitido. Convierte el archivo con el programa que lo creó.'
    if isinstance(error, zipfile.BadZipFile):
        return 'El ZIP está dañado, incompleto o falta una de sus partes. Comprueba que has descargado todos los volúmenes.'
    return str(error) or type(error).__name__
