"""
sanest, sane nested dictionaries and lists
"""

import builtins
import collections.abc

MARKER = object()
CONTAINER_TYPES = (dict, list)
ATOMIC_TYPES = (bool, float, int, str)
TYPES = CONTAINER_TYPES + ATOMIC_TYPES


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


def validate_path(path):
    if not path:
        raise InvalidKeyError(
            "empty path or path component: {!r}".format(path))
    for k in path:
        # explicitly check for booleans, since bool is a subclass of int.
        if isinstance(k, bool) or not isinstance(k, (int, str)):
            raise InvalidKeyError(
                "path must contain only str or int: {!r}".format(path))


def validate_type(type):
    if type not in TYPES:
        raise InvalidValueTypeError(
            "type must be one of {}: {!r}"
            .format(', '.join(t.__name__ for t in TYPES), type))


def parse_slice(sl, pathspec, *, allow_list):
    if sl.step is not None:
        raise InvalidKeyError(
            "slice cannot contain step value: {!r}".format(pathspec))
    if isinstance(sl.start, str):
        # e.g. d['a':str]
        return sl.start, [sl.start], sl.stop
    if isinstance(sl.start, int) and not isinstance(sl.start, bool):
        # e.g. d[2:str]
        return sl.start, [sl.start], sl.stop
    if isinstance(sl.start, (tuple, list)):
        # e.g. d[path:str]
        if not allow_list:
            raise InvalidKeyError(
                "mixed path syntaxes: {!r}".format(pathspec))
        return None, sl.start, sl.stop
    raise InvalidKeyError(
        "path must contain only str or int: {!r}".format(pathspec))


def parse_pathspec(pathspec, *, allow_type, allow_empty_string=False):
    type = None
    if isinstance(pathspec, str):
        # e.g. d['a']
        simple_key = pathspec
        path = [pathspec]
    elif isinstance(pathspec, int) and not isinstance(pathspec, bool):
        # e.g. d[2]
        simple_key = pathspec
        path = [pathspec]
    elif isinstance(pathspec, slice):
        # e.g. d['a':str] and d[path:str]
        simple_key, path, type = parse_slice(
            pathspec, pathspec, allow_list=True)
    elif isinstance(pathspec, (tuple, list)):
        # e.g. d['a', 'b'] and  d['a', 'b':str]
        simple_key = None
        path = list(pathspec)
        if path and isinstance(path[-1], slice):
            # e.g. d['a', 'b':str]
            key_from_slice, _, type = parse_slice(
                path[-1], pathspec, allow_list=False)
            path[-1] = key_from_slice
    else:
        raise InvalidKeyError(
            "path must contain only str or int: {!r}".format(pathspec))
    if '' in path and not (simple_key == '' and allow_empty_string):
        raise InvalidKeyError(
            "empty path or path component: {!r}".format(pathspec))
    validate_path(path)
    if type is not None:
        if not allow_type:
            raise InvalidKeyError(
                "path must contain only str or int: {!r}".format(pathspec))
        validate_type(type)
    return simple_key, path, type


def check_type(x, *, type, path):
    if type is dict:
        real_type = Mapping
    elif type is list:
        real_type = Sequence
    else:
        real_type = type
    if not isinstance(x, real_type):
        raise InvalidValueError(
            "expected {.__name__}, got {.__name__} at path {}: {!r}"
            .format(type, builtins.type(x), path, x))


def resolve_path(obj, path, *, create=False):
    for n, key_or_index in enumerate(path):
        if isinstance(key_or_index, str) and not isinstance(obj, Mapping):
            raise InvalidValueError(
                "expected dict, got {.__name__} at subpath {!r} of {!r}"
                .format(type(obj), path[:n], path))
        if isinstance(key_or_index, int) and not isinstance(obj, Sequence):
            raise InvalidValueError(
                "expected list, got {.__name__} at subpath {!r} of {!r}"
                .format(type(obj), path[:n], path))
        if len(path) - 1 == n:
            break
        try:
            obj = obj[key_or_index]
        except KeyError:
            if create and isinstance(obj, Mapping):
                obj[key_or_index] = obj = MutableMapping()  # autovivification
            else:
                raise
    tail = path[-1]
    return obj, tail


class Mapping(collections.abc.Mapping):
    __slots__ = ('_data',)

    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        if isinstance(key, str):  # fast path
            return self._data[key]
        simple_key, path, type = parse_pathspec(
            key, allow_type=True, allow_empty_string=True)
        try:
            obj, tail = resolve_path(self, path)
            value = obj[tail]
        except KeyError:
            raise KeyError(path if simple_key is None else simple_key)
        if type is not None:
            check_type(value, type=type, path=path)
        return value

    def get(self, key, default=None, *, type=None):
        if isinstance(key, str) and type is None:  # fast path
            return self._data.get(key, default)
        if type is not None:
            validate_type(type)
        _, path, _ = parse_pathspec(key, allow_type=False)
        try:
            obj, tail = resolve_path(self, path)
            value = obj[tail]
        except KeyError:
            return default
        if type is not None:
            check_type(value, type=type, path=path)
        return value

    def contains(self, key, type=None):
        try:
            value = self.get(key, MARKER, type=type)
        except InvalidValueError:
            return False
        else:
            return value is not MARKER

    def __contains__(self, key):
        if isinstance(key, str):  # fast path
            # e.g. 'a' in d
            return key in self._data
        if isinstance(key, (tuple, list)) and key and key[-1] in TYPES:
            # e.g. ['a', 'b', int] in d
            *key, type = key
        else:
            # e.g. ['a', 'b'] in d
            type = None
        return self.contains(key, type=type)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def copy(self):
        return self  # immutable

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        return self.copy()

    # todo: type checking views? (how?)
    # todo: __str__() and __repr__()


class MutableMapping(Mapping, collections.abc.MutableMapping):
    __slots__ = ()

    def set(self, key, value, *, type=None):
        # todo: convert dict/list values into own mapping types
        # todo: disallow None values. "d['x'] = None" means "del d['x']"?
        if isinstance(key, str) and key and type is None:  # fast path
            self._data[key] = value
            return
        if type is not None:
            validate_type(type)
        _, path, _ = parse_pathspec(key, allow_type=False)
        if type is not None:
            check_type(value, type=type, path=path)
        obj, tail = resolve_path(self, path, create=True)
        obj._data[tail] = value

    def setdefault(self, key, default=None, type=None):
        value = self.get(key, MARKER, type=type)
        if value is MARKER:
            self.set(key, default, type=type)
            value = default
        return value

    def __setitem__(self, key, value):
        simple_key, path, type = parse_pathspec(key, allow_type=True)
        self.set(
            path if simple_key is None else simple_key,
            value,
            type=type)

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise InvalidKeyError("invalid key: {!r}".format(key))
        # todo: nested delitem
        # todo: typed delitem
        del self._data[key]

    def clear(self):
        self._data.clear()

    # todo: clean api for building nested structures
    # todo: .setdefault() with type= arg
    # todo: .pop() with type= arg
    # todo: .popitem() with type= arg
    # todo: support for copy.copy() and copy.deepcopy()
    # todo: .copy(deep=True)
    # todo: pickle support


# todo: support for lists

class Sequence(collections.Sequence):
    # todo: implement

    def __getitem__(self, index):
        if isinstance(index, int):
            return self._data[index]
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


class MutableSequence(Sequence, collections.abc.MutableSequence):
    # todo: implement

    def __setitem__(self, index, value):
        raise NotImplementedError

    def insert(self, index, value):
        raise NotImplementedError

    def __delitem__(self, index):
        raise NotImplementedError


# friendly names
# todo: lowercase names? must not mask built-names 'dict' and
# 'list' since those are used elsewhere in this module.
Dict = MutableMapping
List = MutableSequence
