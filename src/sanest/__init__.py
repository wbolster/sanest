"""
sanest, sane nested dictionaries and lists
"""

from .sanest import (  # noqa: F401
    dict,
    list,
    DataError,
    InvalidPathError,
    InvalidStructureError,
    InvalidTypeError,
    InvalidValueError,
)

# Pretend that all public API is defined at the package level,
# which changes the repr() of classes/functions to match intended use.
for x in locals().copy().values():
    if hasattr(x, '__module__'):
        x.__module__ = __name__
del x
