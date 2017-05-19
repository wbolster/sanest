"""
sanest, sane nested dictionaries and lists
"""

import collections.abc

TYPES = [bool, float, int, str]


def normalise_path(path):
    if isinstance(path, str):
        return [path]
    if isinstance(path, (tuple, list)):
        return path
    raise TypeError("invalid path")


def lookup(obj, *, path, value_type=None):
    path = normalise_path(path)
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
    def __getitem__(self, key):
        if isinstance(key, str):  # basic lookup
            return self._data[key]
        if isinstance(key, slice):  # typed lookup
            if key.step is not None:
                raise TypeError("invalid key: slice cannot contain step value")
            value_type = key.stop
            key = key.start
            return lookup(
                self, path=normalise_path(key), value_type=value_type)
        if isinstance(key, tuple):  # nested lookup
            return lookup(self, path=key)
        # todo: factor out slice parsing and path normalisation so that
        # things like d['a','b','c':str] do not depend on recursive
        # lookup() calls.
        raise TypeError("invalid key: {!r}".format(key))

    def get(self, key, default=None, *, type=None):
        if type is not None:
            raise NotImplementedError
        return super().get(key, default)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class MutableMapping(Mapping, collections.abc.MutableMapping):
    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("invalid key: {!r}".format(key))
        self._data[key] = value

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("invalid key: {!r}".format(key))
        del self._data[key]


class Dict(MutableMapping):
    def __init__(self):
        self._data = {}


dict = Dict
