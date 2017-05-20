"""
sanest, sane nested dictionaries and lists
"""

import collections.abc

TYPES = [bool, float, int, str]


def parse_key(key):
    # basic lookup, e.g. d['a']
    if isinstance(key, str):
        path = [key]
        value_type = None

    # typed lookup, e.g. d['a':str]
    elif isinstance(key, slice):
        if key.step is not None:
            raise TypeError("invalid key: slice cannot contain step value")
        path = [key.start]
        value_type = key.stop

    # nested lookup and typed nested lookup,
    # e.g. d['a','b'] and  d['a','b':str]
    elif isinstance(key, tuple):
        if not key:
            raise TypeError("empty path")
        *heads, tail = key
        if any(not isinstance(h, (str, int)) for h in heads):
            raise TypeError("invalid key: {!r}".format(key))
        # todo: maybe include full key in error when recursive parse_key
        # raises an exception?
        tail_path, value_type = parse_key(tail)
        path = heads + tail_path
    else:
        raise TypeError("invalid key: {!r}".format(key))
    return path, value_type


def lookup(obj, *, path, value_type):
    if not path:
        raise ValueError("empty path")
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
    if value_type is not None and not isinstance(obj, value_type):
        raise ValueError(
            "requested {.__name__}, got {.__name__}: {!r}"
            .format(value_type, type(obj), obj))
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
        if type is not None:
            raise NotImplementedError
        return super().get(key, default)

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
