"""Format capabilities shared by the domain layer and desktop workflows."""
from dataclasses import dataclass
from pathlib import Path
import re
from rar_backend import rar_encoder


@dataclass(frozen=True)
class Format:
    name: str
    suffixes: tuple[str, ...]
    password: bool = False
    volumes: bool = False


FORMATS = (
    Format('zip', ('.zip',), True, True),
    Format('7z', ('.7z',), True, True),
    Format('tar', ('.tar',)),
    Format('tar.gz', ('.tar.gz', '.tgz')),
    Format('tar.bz2', ('.tar.bz2', '.tbz2', '.tbz')),
    Format('tar.xz', ('.tar.xz', '.txz')),
    Format('rar', ('.rar',), True, True),
)
CREATE_FORMATS = tuple(fmt.name for fmt in FORMATS)
TAR_MODES = {'tar': 'w', 'tar.gz': 'w:gz', 'tar.bz2': 'w:bz2', 'tar.xz': 'w:xz'}


def available_create_formats():
    return tuple(name for name in CREATE_FORMATS if name != 'rar' or rar_encoder() is not None)


def can_edit(path):
    fmt = format_for_path(path)
    return bool(fmt and (fmt.name != 'rar' or rar_encoder() is not None))


def format_for_path(path):
    path = Path(path)
    name = path.name.lower()
    for fmt in sorted(FORMATS, key=lambda f: max(map(len, f.suffixes)), reverse=True):
        if name.endswith(fmt.suffixes):
            if fmt.name == 'zip' and path.with_suffix('.z01').exists():
                return None
            if fmt.name == 'rar' and (re.search(r'\.part\d+\.rar$', name, re.I) or path.with_suffix('.r00').exists()):
                return None
            return fmt
    return None
