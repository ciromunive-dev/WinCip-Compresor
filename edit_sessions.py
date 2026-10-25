"""External editor copies with explicit, conflict-checked writeback."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
from workspaces import archive_workspace

from archive_core import (ArchiveError, archive_version, checkpoint, collect_sources,
                          copy_stream, modify_archive)


def content_digest(path, cancel=None):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while True:
            checkpoint(cancel)
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.digest()


@dataclass
class EditCopy:
    archive: Path
    member: str
    path: Path
    source_version: tuple
    digest: bytes
    observed_version: tuple


class ExternalEdits:
    def __init__(self):
        self.copies = {}

    def track(self, archive, member, path, cancel=None):
        archive, path = Path(archive).absolute(), Path(path).absolute()
        key = (archive, member)
        if key not in self.copies:
            version = archive_version(path)
            digest = content_digest(path, cancel)
            if archive_version(path) != version:
                raise ArchiveError('La copia cambió durante la apertura. Vuelve a intentarlo.')
            self.copies[key] = EditCopy(archive, member, path, archive_version(archive), digest, version)

    def find(self, archive, member):
        copy = self.copies.get((Path(archive).absolute(), member))
        return copy.path if copy and copy.path.is_file() else None

    def needs_scan(self):
        for copy in self.copies.values():
            try:
                if archive_version(copy.path) != copy.observed_version:
                    return True
            except OSError:
                continue
        return False

    def changed(self, cancel=None):
        result = []
        for copy in self.copies.values():
            checkpoint(cancel)
            # Deleted copies cannot be committed, but must not silently erase
            # other pending documents from the same session.
            if not copy.path.exists():
                continue
            version = archive_version(copy.path)
            digest = content_digest(copy.path, cancel)
            if archive_version(copy.path) != version:
                raise ArchiveError('Un editor está guardando cambios. Espera y vuelve a intentarlo.')
            copy.observed_version = version
            if digest != copy.digest:
                result.append(copy)
        return result

    def commit(self, copies, cancel=None, progress=lambda *args: None, *, password=None, backup=True):
        copies = list(copies)
        if not copies:
            raise ArchiveError('No hay cambios pendientes.')
        source = copies[0].archive
        version = copies[0].source_version
        if any(copy.archive != source or copy.source_version != version for copy in copies):
            raise ArchiveError('Las copias pertenecen a versiones diferentes del comprimido. Conserva los documentos y vuelve a abrirlos.')
        snapshots, digests = [], []
        with archive_workspace(prefix='.wincip-edit-', dir=source.parent) as temp:
            for index, copy in enumerate(copies):
                collect_sources([copy.path], cancel)
                before = archive_version(copy.path)
                snapshot = Path(temp) / str(index)
                with copy.path.open('rb') as src, snapshot.open('xb') as dst:
                    copy_stream(src, dst, cancel, progress, 0, before[0], copy.member, before[0])
                if archive_version(copy.path) != before:
                    raise ArchiveError('El editor sigue guardando cambios. Espera y vuelve a intentarlo.')
                shutil.copystat(copy.path, snapshot)
                snapshots.append((copy.member, snapshot))
                digests.append(content_digest(snapshot, cancel))
            result = modify_archive(source, cancel, progress, password=password, replacements=snapshots,
                                    expected_version=version, backup=backup)
        new_version = archive_version(source)
        for copy in self.copies.values():
            if copy.archive == source and copy.source_version == version:
                copy.source_version = new_version
        for copy, digest in zip(copies, digests):
            copy.digest = digest
            # observed_version remains the last scan, so a save made while
            # compression ran is detected on return to the window.
        return result
