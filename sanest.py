"""
sanest, sane nested dictionaries and lists
"""

import collections.abc

TYPES = [bool, float, int, str]


def parse_key(key):
    path = []
    if isinstance(key, (tuple, list)):
        # nested lookup and typed nested lookup,
        # e.g. d['a','b'] and  d['a','b':str]
        if not key:
            raise TypeError("invalid key: empty path")
        *path, tail = key
        if any(not isinstance(h, (str, int)) for h in path):
            raise TypeError("invalid key: {!r}".format(key))
        key = tail
    if isinstance(key, str):
        # basic lookup, e.g. d['a']
        value_type = None
    elif isinstance(key, slice):
        # typed lookup, e.g. d['a':str]
        if key.step is not None:
            raise TypeError("invalid key: slice cannot contain step value")
        value_type = key.stop
        key = key.start
    else:
        raise TypeError("invalid key: {!r}".format(key))
    path.append(key)
    return path, value_type


def check_type(x, expected_type):
    if not isinstance(x, expected_type):
        raise ValueError(
            "requested {.__name__}, got {.__name__}: {!r}"
            .format(expected_type, type(x), x))


def lookup(obj, *, path, value_type):
    if value_type is not None and value_type not in TYPES:
        raise TypeError(
            "type must be one of {}"
            .format(', '.join(t.__name__ for t in TYPES)))
    for component in path:
        if isinstance(component, str):
            if not isinstance(obj, Mapping):
                raise NotImplementedError
        elif isinstance(component, int):
            raise NotImplementedError('lists')
        obj = obj[component]
    if value_type is not None:
        check_type(obj, value_type)
    return obj


class Mapping(collections.abc.Mapping):
    __slots__ = ('_data',)

    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        if isinstance(key, str):  # trivial lookup
            return self._data[key]
        path, value_type = parse_key(key)
        return lookup(self, path=path, value_type=value_type)

    def get(self, key, default=None, *, type=None):
        value = super().get(key, default)
        if type is not None and value is not default:
            check_type(value, type)
        return value

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class MutableMapping(Mapping, collections.abc.MutableMapping):
    __slots__ = ()

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("invalid key: {!r}".format(key))
        self._data[key] = value

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("invalid key: {!r}".format(key))
        del self._data[key]


dict = MutableMapping
