"""
sanest, sane nested dictionaries and lists
"""

import collections.abc


class Mapping(collections.abc.Mapping):
    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)


class MutableMapping(Mapping, collections.abc.MutableMapping):
    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        self._data[key] = value

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        del self._data[key]


class Dict(MutableMapping):
    def __init__(self):
        self._data = {}


dict = Dict
