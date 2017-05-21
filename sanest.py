"""
sanest, sane nested dictionaries and lists
"""

import collections.abc

TYPES = [bool, float, int, str]


class InvalidKeyError(TypeError):
    """
    Exception indicating that an invalid key is passed.

    This is a subclass of the built-in ``TypeError``, since this
    indicates problematic code that uses an incorrect API.

    Despite the name, it does not indicate absence of an item in a
    dictionary (which is what ``KeyError``) would indicate.
    """
    pass


class InvalidValueTypeError(TypeError):
    """
    Exception indicating that the requested type is invalid.

    This is a subclass of the built-in ``TypeError``, since this
    indicates problematic code that uses an incorrect API.
    """
    pass


class InvalidValueError(ValueError):
    """
    Exception indicating that the data structure does not match what the
    code expects.

    This is a subclass of the built-in ``ValueError``, since this
    indicates malformed data.
    """
    pass


def parse(key):
    path = []
    if isinstance(key, (tuple, list)):
        # nested lookup and typed nested lookup,
        # e.g. d['a','b'] and  d['a','b':str]
        if not key:
            raise InvalidKeyError("empty path: {!r}".format(key))
        *path, tail = key
        if any(not isinstance(h, (str, int)) for h in path):
            raise InvalidKeyError(
                "path must contain only str or int: {!r}".format(key))
        key = tail
    if isinstance(key, str):
        # basic lookup, e.g. d['a']
        value_type = None
    elif isinstance(key, slice):
        # typed lookup, e.g. d['a':str]
        if key.step is not None:
            raise InvalidKeyError(
                "slice cannot contain step value: {!r}".format(key))
        if not key.start:
            raise InvalidKeyError("key is empty: {!r}".format(key))
        value_type = key.stop
        key = key.start
    else:
        raise InvalidKeyError("unknown type: {!r}".format(key))
    return key, path, value_type


def check_type(x, expected_type):
    if not isinstance(x, expected_type):
        raise InvalidValueError(
            "requested {.__name__}, got {.__name__}: {!r}"
            .format(expected_type, type(x), x))


def lookup(obj, *, key, path, value_type):
    if value_type is not None and value_type not in TYPES:
        raise InvalidValueTypeError(
            "type must be one of {}"
            .format(', '.join(t.__name__ for t in TYPES)))
    for component in path + [key]:
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
        key, path, value_type = parse(key)
        return lookup(self, key=key, path=path, value_type=value_type)

    def get(self, key, default=None, *, type=None):
        value = super().get(key, default)
        if type is not None and value is not default:
            check_type(value, type)
        return value

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    # todo: typed __contains__(). maybe .contains() with type= arg?
    #       maybe something like "('a', 'b', str) in d"?
    # todo: type checking views? (how?)


class MutableMapping(Mapping, collections.abc.MutableMapping):
    __slots__ = ()

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise InvalidKeyError("invalid key: {!r}".format(key))
        # todo: convert dict/list values into own mapping types
        # todo: nested setitem
        # todo: typed setitem
        self._data[key] = value

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise InvalidKeyError("invalid key: {!r}".format(key))
        # todo: nested delitem
        # todo: typed delitem
        del self._data[key]

    def clear(self):
        self._data.clear()

    # todo: clean api for building nested structures
    # todo: autovivification
    # todo: .setdefault() with type= arg
    # todo: .pop() with type= arg
    # todo: .popitem() with type= arg
    # todo: support for copy.copy() and copy.deepcopy()
    # todo: .copy(deep=True)
    # todo: pickle support
    # todo: disallow None values. "d['x'] = None" means "del d['x']"?


dict = MutableMapping

# todo: list/Sequence/MutableSequence support
