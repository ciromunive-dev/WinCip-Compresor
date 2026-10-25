"""Per-operation resource budgets; separate from mandatory path validation."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceLimits:
    max_entries: int = 100_000
    max_bytes: int = 50 * 1024**3

    def __post_init__(self):
        for value in (self.max_entries, self.max_bytes):
            if type(value) is not int or value < 0:
                raise ValueError('Los límites deben ser enteros mayores o iguales a cero.')


_current = ContextVar('wincip_resource_limits', default=ResourceLimits())


def current_limits():
    return _current.get()


@contextmanager
def operation_limits(limits):
    token = _current.set(limits)
    try:
        yield limits
    finally:
        _current.reset(token)
