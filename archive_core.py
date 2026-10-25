"""Local archive operations using Python libraries and the bundled 7-Zip engine."""
from __future__ import annotations

from dataclasses import dataclass, replace
from contextlib import contextmanager
from functools import wraps
import inspect
from pathlib import Path, PurePosixPath
import os
import re
import shutil
import stat
import subprocess
import gzip
import bz2
import lzma
import tarfile
import tempfile
import zipfile
import zlib
import sys
import datetime
import pyzipper
import io
import fnmatch
from archive_support import resolve_volume, propagate_zone, MissingVolumeError
from temporary_files import temporary_root
from archive_formats import CREATE_FORMATS, TAR_MODES, format_for_path
from archive_policy import current_limits
from rar_backend import create_rar, rar_encoder
from workspaces import archive_workspace, cleanup_owned_directory


class ArchiveError(Exception):
    pass


class Cancelled(ArchiveError):
    pass


class PasswordRequired(ArchiveError):
    pass


@dataclass(frozen=True)
class Entry:
    name: str
    size: int
    packed: int | None
    directory: bool
    link: bool = False
    mtime: float | None = None
    encrypted: bool = False
    method: str | None = None


def check_resources(entries=0, size=0):
    limits = current_limits()
    if limits.max_entries and entries > limits.max_entries:
        raise ArchiveError(f'La operación supera el límite configurado de {limits.max_entries:,} entradas. Puedes ajustarlo en Preferencias.')
    if limits.max_bytes and size > limits.max_bytes:
        raise ArchiveError(f'La operación supera el tamaño descomprimido configurado ({limits.max_bytes:,} bytes). Puedes ajustarlo en Preferencias.')


def seven_zip():
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'engine' / '7z.exe'
    if bundled.is_file():
        return str(bundled)
    for folder in (os.environ.get('ProgramFiles', r'C:\Program Files'), os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')):
        executable = Path(folder) / '7-Zip' / '7z.exe'
        if executable.is_file():
            return str(executable)
    raise ArchiveError('Este formato necesita 7-Zip instalado en el equipo.')


def run_seven(arguments, cancel=None, output=None, expected=None, *, password=None, cwd=None):
    checkpoint(cancel)
    with tempfile.TemporaryFile() as log, tempfile.TemporaryFile() as result:
        sink = output if output is not None else result
        args = list(arguments)
        if password is not None or args[0] in ('l', 'e', 't'):
            args.insert(1, '-p' + (password if password is not None else '__WinCip_no_password__'))
        process = subprocess.Popen([seven_zip(), *args], cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=sink, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            while True:
                checkpoint(cancel)
                if expected is not None and os.fstat(sink.fileno()).st_size > expected:
                    raise ArchiveError('El archivo contiene más datos de los declarados.')
                try:
                    process.wait(timeout=.1)
                    break
                except subprocess.TimeoutExpired:
                    pass
            if process.returncode:
                log.seek(0)
                result.seek(0)
                diagnostic = (log.read() + (result.read() if output is None else b'')).decode('utf-8', errors='replace').lower()
                if any(word in diagnostic for word in ('missing volume', 'cannot find volume', 'unexpected end of archive')):
                    raise MissingVolumeError('El comprimido está incompleto o falta un volumen. Comprueba todas las partes en la misma carpeta.')
                if any(word in diagnostic for word in ('wrong password', 'password is incorrect', 'can not open encrypted', 'contraseña')):
                    raise PasswordRequired('Contraseña necesaria o incorrecta. Inténtalo de nuevo.')
                raise ArchiveError('No se pudo procesar el comprimido. Puede estar dañado o faltarle un volumen.')
            if expected is not None and os.fstat(sink.fileno()).st_size != expected:
                raise ArchiveError('El tamaño extraído no coincide con el contenido declarado.')
            result.seek(0)
            return result.read().decode('utf-8', errors='strict') if output is None else None
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def list_seven(path, cancel=None, password=None):
    listing = run_seven(['l', '-slt', '-ba', '-sccUTF-8', '--', str(Path(path).absolute())], cancel, password=password)
    entries = []
    for block in listing.replace('\r\n', '\n').strip('\n').split('\n\n'):
        checkpoint(cancel)
        fields = {}
        for line in block.splitlines():
            if ' = ' not in line:
                if line.strip():
                    raise ArchiveError('El comprimido contiene nombres no compatibles.')
                continue
            key, value = line.split(' = ', 1)
            if key in fields:
                raise ArchiveError('El comprimido contiene metadatos ambiguos.')
            fields[key] = value
        if 'Path' not in fields:
            continue
        if fields.get('Encrypted') == '+' and password is None:
            raise PasswordRequired('Introduce la contraseña del comprimido.')
        modified = None
        try:
            modified = datetime.datetime.fromisoformat(fields.get('Modified', '')).timestamp()
        except (ValueError, OverflowError, OSError):
            pass
        attributes = fields.get('Attributes', '')
        entries.append(Entry(fields['Path'].replace('\\', '/'), int(fields.get('Size', '0') or 0),
                             int(fields['Packed Size']) if fields.get('Packed Size') else None,
                             fields.get('Folder') == '+' or attributes.startswith('D'),
                             bool(fields.get('Symbolic Link') or fields.get('Hard Link') or fields.get('Copy Link')) or 'l' in attributes, modified,
                             fields.get('Encrypted') == '+', fields.get('Method')))
        check_resources(entries=len(entries))
    return entries


STREAM_OPENERS = {'gz': gzip.open, 'bz2': bz2.open, 'xz': lzma.open}


def stream_entry(path, kind, cancel=None):
    size = 0
    checkpoint(cancel)
    with STREAM_OPENERS[kind](path, 'rb') as stream:
        while True:
            checkpoint(cancel)
            block = stream.read(1024 * 1024)
            checkpoint(cancel)
            if not block:
                break
            size += len(block)
            check_resources(size=size)
    return Entry(Path(path).stem, size, Path(path).stat().st_size, False)


def checkpoint(cancel):
    if cancel and cancel.is_set():
        raise Cancelled('Operación cancelada. No se guardaron resultados parciales.')


class CancellableReader:
    def __init__(self, stream, cancel):
        self.stream, self.cancel = stream, cancel

    def read(self, size=-1):
        checkpoint(self.cancel)
        value = self.stream.read(size)
        checkpoint(self.cancel)
        return value

    def readinto(self, target):
        checkpoint(self.cancel)
        value = self.stream.readinto(target)
        checkpoint(self.cancel)
        return value

    def seek(self, offset, whence=0):
        checkpoint(self.cancel)
        return self.stream.seek(offset, whence)

    def __getattr__(self, name):
        return getattr(self.stream, name)


@contextmanager
def archive_reader(path, cancel):
    checkpoint(cancel)
    if str(path).lower().endswith('.zip.001'):
        with JoinedVolumes(path, cancel) as stream:
            yield CancellableReader(stream, cancel)
        return
    with open(path, 'rb') as stream:
        yield CancellableReader(stream, cancel)


class JoinedVolumes(io.RawIOBase):
    """Seekable ZIP volume stream; no joined copy is written to disk."""
    def __init__(self, first, cancel):
        self.paths, self.ends = [], []
        self.position, self.cancel = 0, cancel
        prefix = str(first)[:-3]
        size, number = 0, 1
        while Path(prefix + f'{number:03}').is_file():
            checkpoint(cancel)
            path = Path(prefix + f'{number:03}')
            size += path.stat().st_size
            self.paths.append(path)
            self.ends.append(size)
            number += 1
        self.size = size

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset + (self.position if whence == 1 else self.size if whence == 2 else 0)
        if position < 0:
            raise ValueError('Posición no válida')
        self.position = position
        return position

    def read(self, size=-1):
        import bisect
        remaining = max(0, self.size - self.position) if size < 0 else min(size, max(0, self.size - self.position))
        chunks = []
        while remaining:
            checkpoint(self.cancel)
            index = bisect.bisect_right(self.ends, self.position)
            start = self.ends[index - 1] if index else 0
            count = min(remaining, self.ends[index] - self.position)
            with self.paths[index].open('rb') as stream:
                stream.seek(self.position - start)
                block = stream.read(count)
            if len(block) != count:
                raise ArchiveError('Un volumen cambió o está incompleto.')
            chunks.append(block)
            self.position += count
            remaining -= count
        return b''.join(chunks)


@contextmanager
def open_container(path, kind, cancel, password=None):
    with archive_reader(path, cancel) as source:
        opener = ((pyzipper.AESZipFile(source) if password is not None else zipfile.ZipFile(source))
                  if kind == 'zip' else tarfile.open(fileobj=source))
        with opener as archive:
            checkpoint(cancel)
            if kind == 'zip' and password is not None:
                archive.setpassword(password if isinstance(password, bytes) else password.encode('utf-8'))
            try:
                yield archive
            except RuntimeError as exc:
                if 'password' in str(exc).lower():
                    raise PasswordRequired('Contraseña incorrecta. Inténtalo de nuevo.') from None
                raise


def compatible_zip_password(operation):
    signature = inspect.signature(operation)
    @wraps(operation)
    def attempt(source, *args, password=None, **kwargs):
        try:
            return operation(source, *args, password=password, **kwargs)
        except (PasswordRequired, zipfile.BadZipFile, pyzipper.BadZipFile, zlib.error) as original:
            if not isinstance(password, str) or password.isascii():
                raise
            cancel = signature.bind_partial(source, *args, password=password, **kwargs).arguments.get('cancel')
            checkpoint(cancel)
            if archive_kind(source, cancel) != 'zip':
                raise
            # ZIP passwords have no encoding marker. Retry the supplied key in
            # common Windows encodings; extraction rolls back each failed attempt.
            tried = {password.encode('utf-8')}
            for encoding in ('mbcs', 'oem', 'cp1252', 'cp437'):
                try:
                    encoded = password.encode(encoding)
                except (UnicodeError, LookupError):
                    continue
                if encoded in tried:
                    continue
                tried.add(encoded)
                try:
                    return operation(source, *args, password=encoded, **kwargs)
                except (PasswordRequired, zipfile.BadZipFile, pyzipper.BadZipFile, zlib.error):
                    continue
            raise original
    return attempt


def archive_kind(path, cancel=None):
    path = resolve_volume(path)
    if path.suffix.lower() == '.zip' and path.with_suffix('.z01').exists():
        return 'seven'
    if re.search(r'\.(?:\d{3}|z\d\d)$', str(path), re.I) and not str(path).lower().endswith('.zip.001'):
        return 'seven'
    with archive_reader(path, cancel) as source:
        signature = source.read(8)
        if signature.startswith((b'7z\xbc\xaf\x27\x1c', b'Rar!\x1a\x07')):
            return 'seven'
        source.seek(0)
        if zipfile.is_zipfile(source):
            return 'zip'
        if str(path).lower().endswith('.zip.001'):
            raise MissingVolumeError('El conjunto ZIP está incompleto o dañado. Comprueba el último volumen y que todas las partes estén juntas.')
        source.seek(0)
        if tarfile.is_tarfile(source):
            return 'tar'
    for magic, kind in [(b'\x1f\x8b', 'gz'), (b'BZh', 'bz2'), (b'\xfd7zXZ\x00', 'xz')]:
        if signature.startswith(magic):
            return kind
    raise ArchiveError('Formato no compatible. Abre ZIP, RAR, 7Z, TAR, GZ, BZ2 o XZ.')


def list_archive(path, cancel=None, password=None):
    checkpoint(cancel)
    path = resolve_volume(path)
    kind = archive_kind(path, cancel)
    if kind == 'seven':
        return list_seven(path, cancel, password)
    if kind in STREAM_OPENERS:
        return [stream_entry(path, kind, cancel)]
    entries = []
    with open_container(path, kind, cancel) as archive:
        for info in archive.infolist() if kind == 'zip' else archive:
            checkpoint(cancel)
            if kind == 'zip' and info.flag_bits & 1:
                if password is None:
                    raise PasswordRequired('Introduce la contraseña del ZIP.')
            entry = (Entry(info.filename, info.file_size, info.compress_size, info.is_dir(),
                           stat.S_ISLNK(info.external_attr >> 16), datetime.datetime(*info.date_time).timestamp(), bool(info.flag_bits & 1),
                           {0: 'Sin compresión', 8: 'Deflate', 12: 'BZIP2', 14: 'LZMA', 99: 'AES'}.get(info.compress_type, str(info.compress_type))) if kind == 'zip'
                     else Entry(info.name, info.size, None, info.isdir(), not (info.isfile() or info.isdir()), info.mtime))
            entries.append(entry)
            check_resources(entries=len(entries))
    checkpoint(cancel)
    return entries


def safe_name(name):
    name = name.replace('\\', '/')
    if name.startswith('/') or re.match(r'^[A-Za-z]:', name):
        raise ArchiveError(f'Ruta no segura: {name}')
    parts = name.rstrip('/').split('/')
    # A leading ./ is common in tar archives; internal dot segments are rejected.
    while parts and parts[0] == '.':
        parts.pop(0)
    if not parts:
        return None
    for part in parts:
        stem = part.split('.')[0].upper()
        if (part in ('', '.', '..') or part.endswith((' ', '.'))
                or any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                or stem in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
                or re.fullmatch(r'(COM|LPT)[1-9¹²³]', stem)):
            raise ArchiveError(f'Nombre no seguro para Windows: {name}')
    return PurePosixPath(*parts)


def extraction_name(name):
    """Adapt trailing Windows-incompatible punctuation without changing archive lookup."""
    parts = name.replace('\\', '/').split('/')
    normalized = '/'.join(part if part in ('.', '..') else part.rstrip(' .') for part in parts)
    return safe_name(normalized)


def temporary_member_name(name):
    """Normalize Windows-incompatible trailing punctuation for a single copy.

    Validate the complete path before discarding its parent folders, so absolute
    paths and traversal remain rejected. Keep the original name for archive reads.
    """
    relative = extraction_name(name)
    if relative is None:
        raise ArchiveError('Nombre de archivo vacío.')
    return relative.name


def validate_entries(entries):
    check_resources(len(entries), sum(e.size for e in entries))
    seen = {}
    for entry in entries:
        if entry.link:
            raise ArchiveError(f'No se extraen enlaces ni archivos especiales: {entry.name}')
        path = safe_name(entry.name)
        if path is None:
            if not entry.directory:
                raise ArchiveError('Nombre de archivo vacío.')
            continue
        key = str(path).casefold()
        if key in seen:
            raise ArchiveError(f'Nombres duplicados: {entry.name}')
        seen[key] = entry.directory
    for key in seen:
        for parent in PurePosixPath(key).parents:
            if str(parent) in seen and not seen[str(parent)]:
                raise ArchiveError(f'Una ruta de archivo también se usa como carpeta: {key}')


def copy_stream(source, target, cancel, progress, done, total, label, expected):
    copied = 0
    while True:
        checkpoint(cancel)
        block = source.read(1024 * 1024)
        if not block:
            break
        copied += len(block)
        if copied > expected:
            raise ArchiveError(f'El tamaño cambió durante la operación: {label}')
        target.write(block)
        progress(done + copied, total, label)
    if copied != expected:
        raise ArchiveError(f'Tamaño de archivo inesperado: {label}')
    return copied


@compatible_zip_password
def extract_archive(source, destination, cancel=None, progress=lambda *args: None, *, member_name=None, temporary_file=False, password=None, members=None):
    checkpoint(cancel)
    source, destination = resolve_volume(source), Path(destination)
    if destination.exists():
        raise ArchiveError('La carpeta de destino ya existe. Elige una carpeta nueva.')
    indexed_entries = list(enumerate(list_archive(source, cancel, password)))
    if members is not None:
        wanted = [name.replace('\\', '/').rstrip('/') for name in members]
        indexed_entries = [(i, e) for i, e in indexed_entries if any(e.name.replace('\\', '/').rstrip('/') == n or e.name.replace('\\', '/').startswith(n + '/') for n in wanted)]
        if not indexed_entries:
            raise ArchiveError('Selecciona archivos o carpetas para extraer.')
    if member_name is not None:
        indexed_entries = [(index, entry) for index, entry in indexed_entries if entry.name == member_name]
        if len(indexed_entries) != 1:
            raise ArchiveError('No se puede identificar el archivo seleccionado de forma única.')
        if indexed_entries[0][1].directory:
            raise ArchiveError('Selecciona un archivo, no una carpeta.')
    entries = [entry for _, entry in indexed_entries]
    if temporary_file:
        if member_name is None:
            raise ArchiveError('Selecciona un archivo para abrir.')
        temporary_name = temporary_member_name(entries[0].name)
        validate_entries([replace(entries[0], name=temporary_name)])
    else:
        # Archive names are kept intact for reads; only the output paths are
        # adapted. Validate the complete mapped set before writing anything.
        output_names = {id(entry): extraction_name(entry.name) for entry in entries}
        validate_entries([replace(entry, name=str(output_names[id(entry)]) if output_names[id(entry)] is not None else '')
                          for entry in entries])
    def output_relative(entry):
        return PurePosixPath(temporary_name) if temporary_file else output_names[id(entry)]
    total = sum(e.size for e in entries)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(destination.parent).free < total + 16 * 1024**2:
        raise ArchiveError('No hay espacio suficiente en el disco de destino.')
    staging = Path(tempfile.mkdtemp(prefix='.archivofacil-', dir=destination.parent))
    owned_staging = staging.resolve(strict=True)
    try:
        kind = archive_kind(source, cancel)
        if kind in STREAM_OPENERS:
            entry = entries[0]
            target = staging.joinpath(*output_relative(entry).parts)
            with STREAM_OPENERS[kind](source, 'rb') as src, target.open('xb') as dst:
                copy_stream(src, dst, cancel, progress, 0, total, entry.name, entry.size)
            propagate_zone(source, target)
            checkpoint(cancel)
            staging.rename(destination)
            progress(total, total, 'Extracción completada')
            return destination
        if kind == 'seven':
            done = 0
            for entry in entries:
                checkpoint(cancel)
                relative = output_relative(entry)
                if relative is None:
                    continue
                target = staging.joinpath(*relative.parts)
                if entry.directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                progress(done, total, entry.name)
                # Stream one exact entry to our own validated file handle. The external
                # engine never receives an output directory or writes archive paths.
                with target.open('xb') as output:
                    run_seven(['e', '-so', '-spd', '-y', '--', str(source.absolute()), entry.name],
                              cancel, output=output, expected=entry.size, password=password)
                if entry.mtime is not None:
                    os.utime(target, (entry.mtime, entry.mtime))
                propagate_zone(source, target)
                done += entry.size
                progress(done, total, entry.name)
            for entry in reversed(entries):
                relative = output_relative(entry)
                if entry.directory and entry.mtime is not None and relative is not None:
                    os.utime(staging.joinpath(*relative.parts), (entry.mtime, entry.mtime))
            checkpoint(cancel)
            staging.rename(destination)
            progress(total, total, 'Extracción completada')
            return destination
        done = 0
        with open_container(source, kind, cancel, password) as archive:
            members = archive.infolist() if kind == 'zip' else archive.getmembers()
            for index, entry in indexed_entries:
                member = members[index]
                checkpoint(cancel)
                relative = output_relative(entry)
                if relative is None:
                    continue
                target = staging.joinpath(*relative.parts)
                if entry.directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.open(member) if kind == 'zip' else archive.extractfile(member)
                with stream as src, target.open('xb') as dst:
                    done += copy_stream(src, dst, cancel, progress, done, total, entry.name, entry.size)
                if entry.mtime is not None:
                    os.utime(target, (entry.mtime, entry.mtime))
                propagate_zone(source, target)
        for entry in reversed(entries):
            relative = output_relative(entry)
            if entry.directory and entry.mtime is not None and relative is not None:
                os.utime(staging.joinpath(*relative.parts), (entry.mtime, entry.mtime))
        checkpoint(cancel)
        staging.rename(destination)
        progress(total, total, 'Extracción completada')
        return destination
    finally:
        if staging.exists():
            cleanup_owned_directory(staging, owned=owned_staging)


def prepare_file_to_open(source, member_name, cancel=None, progress=lambda *args: None, *, cache_root=None, password=None):
    """Extract only the selected entry; keep it available after the viewer exits.

    Each request gets an isolated directory, including when two archives contain
    the same name. The caller opens this copy using the Windows file association.
    """
    checkpoint(cancel)
    root = Path(cache_root) if cache_root is not None else temporary_root()
    root.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix='open-', dir=root))
    owned_session = session.resolve(strict=True)
    try:
        destination = extract_archive(source, session / 'content', cancel, progress,
                                      member_name=member_name, temporary_file=True, password=password)
        result = destination / temporary_member_name(member_name)
        checkpoint(cancel)
        return result
    except BaseException:
        cleanup_owned_directory(session, owned=owned_session)
        raise


def collect_sources(paths, cancel=None, *, include=(), exclude=()):
    result = []
    def walk_error(error):
        raise error
    for raw in paths:
        checkpoint(cancel)
        root = Path(raw).absolute()
        if not root.exists():
            raise ArchiveError(f'Ya no existe: {root}')
        candidates = [root]
        if root.is_symlink() or getattr(root.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ArchiveError(f'No se incluyen enlaces ni uniones de carpetas: {root}')
        if root.is_dir():
            for base, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
                checkpoint(cancel)
                for name in dirs:
                    child = Path(base) / name
                    if child.is_symlink() or getattr(child.lstat(), 'st_file_attributes', 0) & 0x400:
                        raise ArchiveError(f'No se incluyen enlaces ni uniones de carpetas: {child}')
                candidates.extend(Path(base) / name for name in dirs + files)
                check_resources(entries=len(candidates))
        for path in candidates:
            checkpoint(cancel)
            info = path.lstat()
            if path.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ArchiveError(f'No se incluyen enlaces ni uniones de carpetas: {path}')
            if not path.is_dir() and not path.is_file():
                raise ArchiveError(f'Archivo especial no compatible: {path}')
            name = path.relative_to(root.parent).as_posix()
            entry = Entry(name + ('/' if path.is_dir() else ''),
                          0 if path.is_dir() else info.st_size, None, path.is_dir())
            result.append((path, entry))
    if include or exclude:
        def matches(name, patterns):
            parts = name.rstrip('/').split('/')
            return any(fnmatch.fnmatchcase(name.casefold(), pattern.casefold()) or
                       any(fnmatch.fnmatchcase(part.casefold(), pattern.casefold()) for part in parts)
                       for pattern in patterns)
        selected = [(path, entry) for path, entry in result if not entry.directory and
                    (not include or matches(entry.name, include)) and not matches(entry.name, exclude)]
        names = [entry.name for _, entry in selected]
        selected += [(path, entry) for path, entry in result if entry.directory and not matches(entry.name, exclude) and
                     (not include or any(name.startswith(entry.name) for name in names))]
        result = selected
    validate_entries([entry for _, entry in result])
    return result


def create_zip(paths, destination, level=6, cancel=None, progress=lambda *args: None, *, password=None, include=(), exclude=()):
    destination = Path(destination).absolute()
    if destination.exists():
        raise ArchiveError('El archivo de destino ya existe. Elige otro nombre.')
    sources = collect_sources(paths, cancel, include=include, exclude=exclude)
    if not sources:
        raise ArchiveError('Añade al menos un archivo o una carpeta.')
    for path in map(lambda item: item[0], sources):
        if path.is_dir() and destination.is_relative_to(path):
            raise ArchiveError('Guarda el ZIP fuera de las carpetas que estás comprimiendo.')
    total = sum(entry.size for _, entry in sources)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix='.archivofacil-', suffix='.zip', dir=destination.parent)
    os.close(handle)
    try:
        done = 0
        factory = pyzipper.AESZipFile if password else zipfile.ZipFile
        compression = zipfile.ZIP_STORED if level == 0 else zipfile.ZIP_DEFLATED
        with factory(temp, 'w', compression=compression,
                             compresslevel=level, allowZip64=True) as archive:
            if password:
                archive.setpassword(password.encode('utf-8'))
                archive.setencryption(pyzipper.WZ_AES, nbits=256)
            for path, entry in sources:
                checkpoint(cancel)
                if entry.directory:
                    info = (archive.zipinfo_cls if password else zipfile.ZipInfo).from_file(path, entry.name)
                    archive.writestr(info, b'')
                else:
                    info = (archive.zipinfo_cls if password else zipfile.ZipInfo).from_file(path, entry.name)
                    info.compress_type = compression
                    info._compresslevel = level
                    with path.open('rb') as src, archive.open(info, 'w', force_zip64=True) as dst:
                        done += copy_stream(src, dst, cancel, progress, done, total, entry.name, entry.size)
        checkpoint(cancel)
        # Windows rename refuses existing targets, preserving the original file.
        Path(temp).rename(destination)
        progress(total, total, 'Compresión completada')
        return destination
    finally:
        Path(temp).unlink(missing_ok=True)


@compatible_zip_password
def verify_archive(source, cancel=None, progress=lambda *args: None, *, password=None):
    checkpoint(cancel)
    source = resolve_volume(source)
    kind = archive_kind(source, cancel)
    if kind in STREAM_OPENERS:
        done = 0
        with STREAM_OPENERS[kind](source, 'rb') as stream:
            while True:
                checkpoint(cancel)
                block = stream.read(1024 * 1024)
                if not block:
                    break
                done += len(block)
                check_resources(size=done)
        return 'Comprobación completada. No se encontraron errores.'
    if kind == 'seven':
        entries = list_archive(source, cancel, password)
        check_resources(len(entries), sum(e.size for e in entries))
        run_seven(['t', '-y', '-sccUTF-8', '--', str(Path(source).absolute())], cancel, password=password)
        return 'Comprobación completada. No se encontraron errores.'
    entries = list_archive(source, cancel, password)
    check_resources(len(entries), sum(e.size for e in entries))
    total = sum(e.size for e in entries)
    kind = archive_kind(source, cancel)
    done = 0
    with open_container(source, kind, cancel, password) as archive:
        members = archive.infolist() if kind == 'zip' else archive.getmembers()
        for member, entry in zip(members, entries):
            checkpoint(cancel)
            if entry.directory or entry.link:
                continue
            stream = archive.open(member) if kind == 'zip' else archive.extractfile(member)
            with stream:
                while True:
                    checkpoint(cancel)
                    block = stream.read(1024 * 1024)
                    if not block:
                        break
                    done += len(block)
                    progress(done, total, entry.name)
    return 'Lectura completada sin errores. Los ZIP también se verifican mediante su CRC.'

def _create_archive(paths, destination, level=6, cancel=None, progress=lambda *args: None,
                   *, format='zip', password=None, hide_names=True, volume_mb=0, include=(), exclude=()):
    if format not in ('zip', '7z', 'rar'):
        raise ArchiveError('Elige ZIP, 7Z o RAR.')
    if format == 'zip' and not volume_mb:
        return create_zip(paths, destination, level, cancel, progress, password=password, include=include, exclude=exclude)
    if type(volume_mb) is not int or volume_mb < 0:
        raise ArchiveError('El tamaño de volumen debe ser un entero mayor o igual a cero.')
    destination = Path(destination).absolute()
    target = destination.with_name(destination.name + '.parts') if volume_mb else destination
    if target.exists():
        raise ArchiveError('El destino ya existe. Elige otro nombre.')
    sources = collect_sources(paths, cancel, include=include, exclude=exclude)
    if not sources:
        raise ArchiveError('Añade archivos o carpetas.')
    if any(p.is_dir() and target.is_relative_to(p) for p, _ in sources):
        raise ArchiveError('Guarda el comprimido fuera de las carpetas de origen.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = sum(e.size for _, e in sources)
    if shutil.disk_usage(destination.parent).free < total + 16 * 1024**2:
        raise ArchiveError('No hay espacio suficiente para preparar el comprimido.')
    with archive_workspace(prefix='.archivofacil-', dir=destination.parent) as temp:
        work = Path(temp)
        content = work / 'content'
        content.mkdir()
        done = 0
        for path, entry in sources:
            checkpoint(cancel)
            output = content.joinpath(*safe_name(entry.name).parts)
            if entry.directory:
                output.mkdir(parents=True, exist_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                with path.open('rb') as src, output.open('xb') as dst:
                    done += copy_stream(src, dst, cancel, progress, done, total, entry.name, entry.size)
                shutil.copystat(path, output)
        result_dir = work / 'result'
        result_dir.mkdir()
        result = result_dir / destination.name
        if format == 'rar':
            create_rar(content, result, level, cancel, progress, password=password, hide_names=hide_names, volume_mb=volume_mb)
            checkpoint(cancel)
            if volume_mb:
                result_dir.rename(target)
            else:
                result.rename(target)
            return target
        if format == 'zip' and volume_mb:
            joined = create_zip(list(content.iterdir()), work / 'joined.zip', level, cancel, progress, password=password)
            with joined.open('rb') as stream:
                index = 1
                while True:
                    checkpoint(cancel)
                    if stream.tell() == joined.stat().st_size:
                        break
                    remaining = min(volume_mb * 1024**2, joined.stat().st_size - stream.tell())
                    with (result_dir / (destination.name + f'.{index:03}')).open('xb') as part:
                        while remaining:
                            checkpoint(cancel)
                            block = stream.read(min(1024**2, remaining))
                            if not block:
                                raise ArchiveError('El archivo preparado cambió de tamaño.')
                            part.write(block)
                            remaining -= len(block)
                    index += 1
            checkpoint(cancel)
            result_dir.rename(target)
            return target
        args = ['a', '-t' + format, '-mx=' + str(level), '-y', '-sccUTF-8']
        if password:
            args += ['-mhe=on'] if format == '7z' and hide_names else []
            args += ['-mem=AES256'] if format == 'zip' else []
        if volume_mb:
            args += ['-v' + str(volume_mb) + 'm']
        progress(0, 0, 'Comprimiendo con 7-Zip…')
        run_seven([*args, '--', str(result), *[p.name for p in content.iterdir()]], cancel,
                  password=password, cwd=content)
        checkpoint(cancel)
        if volume_mb:
            result_dir.rename(target)
        else:
            result.rename(target)
    progress(total, total, 'Compresión completada')
    return target


def extract_into(source, destination, cancel=None, progress=lambda *args: None, *,
                 password=None, members=None, conflict='rename'):
    """Extract and validate first, then merge with a rollback journal."""
    if conflict not in ('rename', 'skip', 'replace'):
        raise ArchiveError('Política de archivos existentes no válida.')
    destination = Path(destination).absolute()
    destination.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or getattr(destination.lstat(), 'st_file_attributes', 0) & 0x400:
        raise ArchiveError('El destino no puede ser un enlace o unión.')
    with archive_workspace(prefix='.archivofacil-', dir=destination.parent) as temp:
        work = Path(temp)
        staged = extract_archive(source, work / 'content', cancel, progress, password=password, members=members)
        journal, made = [], []
        try:
            for folder, dirs, files in os.walk(staged):
                checkpoint(cancel)
                relative = Path(folder).relative_to(staged)
                outdir = destination / relative
                # Every ancestor is checked before writing; never follow reparse points.
                for part in [outdir, *outdir.parents]:
                    if part == destination.parent:
                        break
                    if part.exists() and (part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & 0x400):
                        raise ArchiveError('El destino contiene un enlace o unión.')
                if not outdir.exists():
                    outdir.mkdir()
                    made.append(outdir)
                for name in files:
                    checkpoint(cancel)
                    incoming = Path(folder) / name
                    target = outdir / name
                    backup = None
                    if target.exists():
                        if conflict == 'skip':
                            continue
                        if target.is_dir() or target.is_symlink() or getattr(target.lstat(), 'st_file_attributes', 0) & 0x400:
                            raise ArchiveError('Conflicto con una carpeta o enlace: ' + str(target))
                        if conflict == 'rename':
                            index = 2
                            while target.exists():
                                target = outdir / f'{Path(name).stem} ({index}){Path(name).suffix}'
                                index += 1
                        else:
                            backup = work / ('backup-' + str(len(journal)))
                            target.rename(backup)
                    journal.append((target, backup))
                    incoming.rename(target)
            checkpoint(cancel)
        except BaseException:
            for target, backup in reversed(journal):
                if target.exists():
                    target.unlink()
                if backup is not None:
                    backup.rename(target)
            for path in reversed(made):
                path.rmdir()
            raise
    return destination


def create_tar(paths, destination, format, level=6, cancel=None, progress=lambda *args: None, *, include=(), exclude=()):
    sources = collect_sources(paths, cancel, include=include, exclude=exclude)
    if not sources:
        raise ArchiveError('Ningún archivo coincide con la selección y los filtros.')
    total = sum(entry.size for _, entry in sources)
    done = 0
    options = ({'compresslevel': level} if format == 'tar.gz' else
               {'compresslevel': max(1, level)} if format == 'tar.bz2' else
               {'preset': level} if format == 'tar.xz' else {})
    with tarfile.open(destination, TAR_MODES[format], **options) as archive:
        for path, entry in sources:
            checkpoint(cancel)
            info = archive.gettarinfo(str(path), arcname=entry.name)
            if entry.directory:
                archive.addfile(info)
            else:
                class Reader(CancellableReader):
                    def read(self, size=-1):
                        nonlocal done
                        block = super().read(size)
                        done += len(block)
                        progress(done, total, entry.name)
                        return block
                with path.open('rb') as src:
                    archive.addfile(info, Reader(src, cancel))
    return Path(destination)


def create_archive(paths, destination, level=6, cancel=None, progress=lambda *args: None, *,
                   format='zip', password=None, hide_names=True, volume_mb=0, verify=False,
                   overwrite=False, include=(), exclude=()):
    destination = Path(destination).absolute()
    paths = [Path(path).absolute() for path in paths]
    if format not in CREATE_FORMATS:
        raise ArchiveError('Elige un formato de creación compatible.')
    if format == 'rar' and rar_encoder() is None:
        raise ArchiveError('Crear RAR requiere Rar.exe de una instalación de WinRAR. Elige ZIP o 7Z para usar el motor incluido.')
    if type(volume_mb) is not int or volume_mb < 0:
        raise ArchiveError('El tamaño de volumen debe ser un entero mayor o igual a cero.')
    if format.startswith('tar') and (password or volume_mb):
        raise ArchiveError('Los formatos TAR no admiten contraseña ni volúmenes.')
    if level not in (0, 1, 6, 9):
        raise ArchiveError('Nivel de compresión no válido.')
    if any(path.is_dir() and destination.is_relative_to(path) for path in paths):
        raise ArchiveError('Guarda el comprimido fuera de las carpetas de origen.')
    if destination in paths:
        raise ArchiveError('El destino no puede reemplazar un archivo de origen.')
    target = destination.with_name(destination.name + '.parts') if volume_mb else destination
    if target.exists() and (not overwrite or volume_mb or target.is_dir()):
        raise ArchiveError('El destino ya existe. Elige otro nombre o permite reemplazarlo.')
    before = (target.stat().st_mtime_ns, target.stat().st_size) if target.exists() else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive_workspace(prefix='.archivofacil-', dir=destination.parent) as temp:
        prepared = Path(temp) / destination.name
        if format.startswith('tar'):
            result = create_tar(paths, prepared, format, level, cancel, progress, include=include, exclude=exclude)
        else:
            result = _create_archive(paths, prepared, level, cancel, progress, format=format, password=password,
                                     hide_names=hide_names, volume_mb=volume_mb, include=include, exclude=exclude)
        if verify:
            progress(0, 0, 'Verificando el resultado…')
            first = next(iter(sorted(result.glob('*.001'))), None) if result.is_dir() else result
            if first is None and result.is_dir() and format == 'rar':
                first = next(iter(sorted(result.glob('*.rar'))), None)
            if first is None:
                raise ArchiveError('No se encontró el primer volumen creado.')
            verify_archive(first, cancel, lambda *_: None, password=password)
        checkpoint(cancel)
        if before:
            if not target.exists() or (target.stat().st_mtime_ns, target.stat().st_size) != before:
                raise ArchiveError('El destino cambió durante la operación. Elige otro nombre.')
            os.replace(result, target)
        else:
            result.rename(target)
    progress(1, 1, 'Comprimido guardado' + (' y verificado' if verify else ''))
    return target


_UNCHANGED = object()


def archive_version(path):
    info = Path(path).stat()
    return info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino


def list_backups(source):
    source = Path(source)
    pattern = re.compile(re.escape(source.name) + r'\.bak(?:\.[2-9]\d*|\.1\d+)?\Z', re.I)
    return sorted((path for path in source.parent.iterdir()
                   if pattern.fullmatch(path.name) and path.is_file() and not path.is_symlink()),
                  key=lambda path: path.stat().st_mtime_ns, reverse=True)


def save_backup(source, workspace, cancel=None):
    source, workspace = Path(source), Path(workspace)
    version = archive_version(source)
    target, index = source.with_name(source.name + '.bak'), 2
    while target.exists():
        target = source.with_name(source.name + f'.bak.{index}')
        index += 1
    staged = workspace / 'original-backup'
    with source.open('rb') as src, staged.open('xb') as dst:
        copy_stream(src, dst, cancel, lambda *_: None, 0, version[0], source.name, version[0])
    if archive_version(source) != version:
        raise ArchiveError('El original cambió mientras se preparaba el respaldo.')
    propagate_zone(source, staged)
    checkpoint(cancel)
    staged.rename(target)
    return target


def restore_backup(source, backup, cancel=None, progress=lambda *args: None, *, password=None):
    """Verify a staged backup, preserve the current file, then replace atomically."""
    source, backup = Path(source).absolute(), Path(backup).absolute()
    if source == backup:
        raise ArchiveError('Selecciona un respaldo distinto del comprimido actual.')
    version, saved_version = archive_version(source), archive_version(backup)
    with archive_workspace(prefix='.wincip-restore-', dir=source.parent) as temp:
        root = Path(temp)
        staged = root / source.name
        with backup.open('rb') as src, staged.open('xb') as dst:
            copy_stream(src, dst, cancel, progress, 0, saved_version[0], backup.name, saved_version[0])
        if archive_version(backup) != saved_version:
            raise ArchiveError('El respaldo cambió durante la lectura.')
        verify_archive(staged, cancel, progress, password=password)
        propagate_zone(backup, staged)
        checkpoint(cancel)
        if archive_version(source) != version:
            raise ArchiveError('El comprimido actual cambió. No se ha reemplazado.')
        save_backup(source, root, cancel)
        checkpoint(cancel)
        if archive_version(source) != version:
            raise ArchiveError('El comprimido actual cambió. No se ha reemplazado.')
        os.replace(staged, source)
    return source


def zip_comment(source):
    with zipfile.ZipFile(source) as archive:
        return archive.comment


def preserve_zip_metadata(source, rebuilt, rename=None, comment=_UNCHANGED):
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(rebuilt, 'a') as result:
        metadata = {}
        for info in original.infolist():
            name = info.filename
            if rename:
                old, new = (value.rstrip('/') for value in rename)
                if name.rstrip('/') == old or name.startswith(old + '/'):
                    name = new + name[len(old):]
            metadata[name] = info
        result.comment = original.comment if comment is _UNCHANGED else comment
        for info in result.infolist():
            previous = metadata.get(info.filename)
            if previous is not None:
                info.comment = previous.comment
                info.external_attr = previous.external_attr
                info.internal_attr = previous.internal_attr
                info.create_system = previous.create_system


def modify_archive(source, cancel=None, progress=lambda *args: None, *, password=None,
                   additions=(), remove=(), rename=None, folder='', new_folder=None,
                   conflict='error', destination=None, backup=False, new_password=_UNCHANGED,
                   replacements=(), expected_version=None, comment=_UNCHANGED):
    source = Path(source).absolute()
    fmt = format_for_path(source)
    if fmt is None:
        raise ArchiveError('Convierte este comprimido a ZIP, 7Z o TAR antes de editarlo.')
    if fmt.name == 'rar' and rar_encoder() is None:
        raise ArchiveError('Modificar RAR requiere Rar.exe de una instalación de WinRAR. También puedes convertirlo a ZIP o 7Z.')
    if comment is not _UNCHANGED:
        if fmt.name != 'zip' or not isinstance(comment, bytes) or len(comment) > 65535:
            raise ArchiveError('Los comentarios ZIP admiten hasta 65 535 bytes.')
    if expected_version is not None and archive_version(source) != expected_version:
        raise ArchiveError('El comprimido cambió desde que abriste la copia. Conserva tus cambios fuera del temporal y vuelve a abrirlo.')
    if conflict not in ('error', 'skip', 'replace', 'newer'):
        raise ArchiveError('Elige reemplazar, omitir o actualizar archivos recientes.')
    target = Path(destination).absolute() if destination else source
    if format_for_path(target) != fmt:
        raise ArchiveError('Para cambiar de formato utiliza Convertir.')
    if target != source and target.exists():
        raise ArchiveError('El destino ya existe. Elige otro nombre.')
    before = source.stat()
    before_version = archive_version(source)
    if expected_version is not None and before_version != expected_version:
        raise ArchiveError('El comprimido cambió desde que abriste la copia. No se ha actualizado.')
    list_archive(source, cancel, password)
    secret = password if new_password is _UNCHANGED else new_password
    if not fmt.password and secret:
        raise ArchiveError('Este formato TAR no admite contraseña. Utiliza ZIP o 7Z.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive_workspace(prefix='.archivofacil-', dir=target.parent) as temp:
        root = Path(temp)
        progress(0, 0, 'Preparando la edición…')
        content = extract_archive(source, root / 'content', cancel, lambda *_: None, password=password)
        for name in remove:
            checkpoint(cancel)
            relative = safe_name(name)
            if relative is None:
                raise ArchiveError('No se puede eliminar la raíz.')
            path = content.joinpath(*relative.parts)
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        if rename:
            old, new = rename
            oldpath, newpath = safe_name(old), safe_name(new)
            if oldpath is None or newpath is None:
                raise ArchiveError('Nombre no válido.')
            oldpath, newpath = content.joinpath(*oldpath.parts), content.joinpath(*newpath.parts)
            if newpath.exists():
                raise ArchiveError('Ese nombre ya existe.')
            newpath.parent.mkdir(parents=True, exist_ok=True)
            oldpath.rename(newpath)
        prefix = safe_name(folder) if folder else None
        base = content.joinpath(*prefix.parts) if prefix else content
        if new_folder:
            relative = safe_name(new_folder)
            if relative is None:
                raise ArchiveError('Escribe el nombre de la carpeta.')
            base.joinpath(*relative.parts).mkdir(parents=True, exist_ok=False)
        for path, entry in collect_sources(additions, cancel):
            checkpoint(cancel)
            output = base.joinpath(*safe_name(entry.name).parts)
            if output.exists() and not (output.is_dir() and entry.directory):
                if output.is_dir() or entry.directory:
                    raise ArchiveError('Conflicto entre archivo y carpeta: ' + entry.name)
                if conflict == 'skip' or (conflict == 'newer' and path.stat().st_mtime <= output.stat().st_mtime + 2):
                    continue
                if conflict == 'error':
                    raise ArchiveError('Ya existe dentro del comprimido: ' + entry.name)
            if entry.directory:
                output.mkdir(parents=True, exist_ok=True)
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                with path.open('rb') as src, output.open('wb') as dst:
                    copy_stream(src, dst, cancel, progress, 0, entry.size, entry.name, entry.size)
                shutil.copystat(path, output)
        for name, path in replacements:
            relative = safe_name(name)
            if relative is None:
                raise ArchiveError('No se puede reemplazar la raíz del comprimido.')
            output = content.joinpath(*relative.parts)
            if not output.is_file():
                raise ArchiveError('El archivo que quieres actualizar ya no existe: ' + name)
            path = Path(path)
            collect_sources([path], cancel)  # Reject links and special files.
            version = archive_version(path)
            with path.open('rb') as src, output.open('wb') as dst:
                copy_stream(src, dst, cancel, progress, 0, version[0], name, version[0])
            if archive_version(path) != version:
                raise ArchiveError('El editor sigue guardando el archivo. Espera y vuelve a intentarlo.')
            shutil.copystat(path, output)
        rebuilt = root / ('rebuilt.' + fmt.name)
        children = list(content.iterdir())
        if children:
            create_archive(children, rebuilt, cancel=cancel, progress=progress, format=fmt.name, password=secret, verify=fmt.name != 'zip')
        elif secret:
            raise ArchiveError('Un comprimido vacío no puede protegerse con contraseña. Añade al menos un archivo o carpeta.')
        elif source.suffix.lower() == '.zip':
            with zipfile.ZipFile(rebuilt, 'w'):
                pass
        elif fmt.name in TAR_MODES:
            with tarfile.open(rebuilt, TAR_MODES[fmt.name]):
                pass
        else:
            raise ArchiveError('Este formato necesita al menos una carpeta o un archivo.')
        if fmt.name == 'zip':
            preserve_zip_metadata(source, rebuilt, rename, comment)
            verify_archive(rebuilt, cancel, lambda *_: None, password=secret)
        propagate_zone(source, rebuilt)
        checkpoint(cancel)
        if archive_version(source) != before_version:
            raise ArchiveError('El comprimido cambió durante la edición. Vuelve a abrirlo.')
        if backup and target == source:
            save_backup(source, root, cancel)
        checkpoint(cancel)
        if target == source:
            if archive_version(source) != before_version:
                raise ArchiveError('El comprimido cambió durante la edición. El original se ha conservado.')
            os.replace(rebuilt, source)
        else:
            rebuilt.rename(target)
    return target


def modify_zip(source, cancel=None, progress=lambda *args: None, **options):
    return modify_archive(source, cancel, progress, **options)


def convert_archive(source, destination, cancel=None, progress=lambda *args: None, *, password=None,
                    format='zip', new_password=None, level=6, verify=True):
    source = resolve_volume(source)
    destination = Path(destination).absolute()
    if destination == source:
        raise ArchiveError('Guarda la conversión con un nombre distinto.')
    if destination.exists():
        raise ArchiveError('El destino ya existe. Elige otro nombre para la conversión.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive_workspace(prefix='.archivofacil-', dir=destination.parent) as temp:
        progress(0, 0, 'Preparando la conversión…')
        content = extract_archive(source, Path(temp) / 'content', cancel, lambda *_: None, password=password)
        staged = Path(temp) / destination.name
        result = create_archive(list(content.iterdir()), staged, level, cancel, progress,
                                format=format, password=new_password, verify=verify)
        propagate_zone(source, result)
        checkpoint(cancel)
        result.rename(destination)
        return destination
