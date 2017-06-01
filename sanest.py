"""
sanest, sane nested dictionaries and lists
"""

import builtins
import copy
import collections.abc

ATOMIC_TYPES = (bool, float, int, str)
CONTAINER_TYPES = (builtins.dict, builtins.list)
TYPES = CONTAINER_TYPES + ATOMIC_TYPES
PATH_SYNTAX_TYPES = (builtins.tuple, builtins.list)


class Missing:
    def __repr__(self):
        return '<missing>'


MISSING = Missing()


class InvalidKeyError(TypeError):
    """
    Exception raised when a key is invalid.

    This is a subclass of the built-in ``TypeError``, since this
    indicates problematic code that uses an incorrect API.

    Despite the name, it does not indicate absence of an item in a
    dictionary, which is what ``KeyError`` would indicate.
    """
    pass


class InvalidTypeError(TypeError):
    """
    Exception raised when a specified type is invalid.

    This is a subclass of the built-in ``TypeError``, since this
    indicates problematic code that uses an incorrect API.
    """
    pass


class DataError(ValueError):
    """
    Exception raised for data errors, such as invalid values and
    unexpected nesting structures.

    This is the base class for ``InvalidStructureError`` and
    ``InvalidValueError``.

    This is a subclass of the built-in ``ValueError``.
    """


class InvalidStructureError(ValueError):
    """
    Exception raised when a nested structure does not match the request.

    This is a subclass of ``DataError`` and the built-in ``ValueError``,
    since this indicates malformed data.
    """
    pass


class InvalidValueError(ValueError):
    """
    Exception raised when requesting or providing an invalid value.

    This is a subclass of ``DataError`` and the built-in ``ValueError``,
    since this indicates malformed data.
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
        raise InvalidTypeError(
            "type must be one of {}: {!r}"
            .format(', '.join(t.__name__ for t in TYPES), type))


def wrap(value):
    """
    Wrap a container (dict or list) without making a copy.
    """
    if isinstance(value, builtins.dict):
        return sanest_dict.wrap(value)
    if isinstance(value, builtins.list):
        return sanest_list.wrap(value)
    raise TypeError("not a dict or list: {!r}".format(value))


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
    if isinstance(sl.start, PATH_SYNTAX_TYPES):
        # e.g. d[path:str]
        if not allow_list:
            raise InvalidKeyError(
                "mixed path syntaxes: {!r}".format(pathspec))
        return None, sl.start, sl.stop
    raise InvalidKeyError(
        "path must contain only str or int: {!r}".format(pathspec))


def parse_pathspec(pathspec, *, allow_type, allow_empty_string):
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
    elif isinstance(pathspec, PATH_SYNTAX_TYPES):
        # e.g. d['a', 'b'] and  d['a', 'b':str]
        simple_key = None
        path = builtins.list(pathspec)
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


def check_type(value, *, type, path):
    if not isinstance(value, TYPES):
        raise InvalidValueError(
            "cannot use values of type {.__name__}: {!r}"
            .format(builtins.type(value), value))
    if type is not None and not isinstance(value, type):
        raise InvalidValueError(
            "expected {.__name__}, got {.__name__} at path {}: {!r}"
            .format(type, builtins.type(value), path, value))


def resolve_path(obj, path, *, create=False):
    for n, key_or_index in enumerate(path):
        if isinstance(key_or_index, str) and not isinstance(
                obj, builtins.dict):
            raise InvalidStructureError(
                "expected dict, got {.__name__} at subpath {!r} of {!r}"
                .format(type(obj), path[:n], path))
        if isinstance(key_or_index, int) and not isinstance(
                obj, builtins.list):
            raise InvalidStructureError(
                "expected list, got {.__name__} at subpath {!r} of {!r}"
                .format(type(obj), path[:n], path))
        if len(path) - 1 == n:
            break
        try:
            obj = obj[key_or_index]
        except KeyError:
            if create and isinstance(obj, builtins.dict):
                obj[key_or_index] = obj = {}  # autovivification
            else:
                raise
    tail = path[-1]
    return obj, tail


class rodict(collections.abc.Mapping):
    __slots__ = ('_data',)

    def __init__(self, *args, **kwargs):
        self._data = {}
        if args or kwargs:
            self.update(*args, **kwargs)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        return cls((key, value) for key in iterable)

    @classmethod
    def wrap(cls, d):
        if isinstance(d, cls):
            return d
        if not isinstance(d, builtins.dict):
            raise TypeError("not a dict")
        # todo: check validity, maybe add check=True arg
        obj = cls()
        obj._data = d
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):  # fast path
            value = self._data[key]
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value)
            return value
        simple_key, path, type = parse_pathspec(
            key, allow_type=True, allow_empty_string=True)
        key = path if simple_key is None else simple_key
        value = self.get(key, MISSING, type=type)
        if value is MISSING:
            raise KeyError(key)
        return value

    def get(self, key, default=None, *, type=None):
        if isinstance(key, str) and type is None:  # fast path
            value = self._data.get(key, MISSING)
            if value is MISSING:
                return default
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value)
            return value
        if type is not None:
            validate_type(type)
        _, path, _ = parse_pathspec(
            key, allow_type=False, allow_empty_string=True)
        try:
            obj, tail = resolve_path(self._data, path)
            value = obj[tail]
        except KeyError:
            return default
        if type is not None:
            check_type(value, type=type, path=path)
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value)
        return value

    def contains(self, key, *, type=None):
        try:
            value = self.get(key, MISSING, type=type)
        except (InvalidStructureError, InvalidValueError):
            return False
        else:
            return value is not MISSING

    def __contains__(self, key):
        if isinstance(key, str):  # fast path
            # e.g. 'a' in d
            return key in self._data
        if (isinstance(key, PATH_SYNTAX_TYPES) and key and key[-1] in TYPES):
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
        return self  # immutable

    def __deepcopy__(self, memo):
        return self  # immutable

    def unwrap(self):
        """Return a regular (nested) dict/list structure."""
        return self._data

    def __repr__(self):
        return '{}.{.__name__}({!r})'.format(
            __name__, type(self), self._data)


class dict(rodict, collections.abc.MutableMapping):
    """
    dict-like container with support for nested lookups and type checking.
    """
    __slots__ = ()

    def set(self, key, value, *, type=None):
        if isinstance(value, (sanest_read_only_dict, sanest_read_only_list)):
            value = value._data  # same as .unwrap(), but faster
        if isinstance(key, str) and key and value is not None and type is None:
            # fast path
            check_type(value, type=type, path=[key])
            self._data[key] = value
            return
        if type is not None:
            validate_type(type)
        _, path, _ = parse_pathspec(
            key, allow_type=False, allow_empty_string=False)
        if value is not None:
            check_type(value, type=type, path=path)
        obj, tail = resolve_path(self._data, path, create=True)
        if value is None:
            obj.pop(tail, None)
        else:
            obj[tail] = value

    def setdefault(self, key, default=None, *, type=None):
        value = self.get(key, MISSING, type=type)
        if value is MISSING:
            self.set(key, default, type=type)
            value = default
        return value

    def __setitem__(self, key, value):
        simple_key, path, type = parse_pathspec(
            key, allow_type=True, allow_empty_string=False)
        self.set(
            path if simple_key is None else simple_key,
            value,
            type=type)

    def pop(self, key, default=MISSING, *, type=None):
        if isinstance(key, str) and type is None:  # fast path
            value = self._data.pop(key, MISSING)
            if value is MISSING:
                if default is MISSING:
                    raise KeyError(key)
                return default
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value)
            return value
        value = self.get(key, MISSING, type=type)
        if type is not None:
            validate_type(type)
        simple_key, path, _ = parse_pathspec(
            key, allow_type=False, allow_empty_string=True)
        try:
            obj, tail = resolve_path(self._data, path)
            value = obj[tail]
        except KeyError:
            if default is MISSING:
                raise KeyError(path if simple_key is None else simple_key)
            return default
        else:
            if type is not None:
                check_type(value, type=type, path=path)
            del obj[tail]
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value)
            return value

    def popitem(self, *, type=None):
        try:
            key = next(iter(self._data))
        except StopIteration:
            raise KeyError("dictionary is empty") from None
        value = self.get(key, type=type)
        del self._data[key]
        return key, value

    def __delitem__(self, key):
        if isinstance(key, str):  # fast path
            del self._data[key]
            return
        simple_key, path, type = parse_pathspec(
            key, allow_type=True, allow_empty_string=False)
        self.pop(path if simple_key is None else simple_key, type=type)

    def clear(self):
        self._data.clear()

    def copy(self, *, deep=False):
        fn = copy.deepcopy if deep else copy.copy
        return fn(self)

    def __copy__(self):
        cls = type(self)
        obj = cls.__new__(cls)
        obj._data = self._data.copy()
        return obj

    def __deepcopy__(self, memo):
        cls = type(self)
        obj = cls.__new__(cls)
        obj._data = copy.deepcopy(self._data, memo)
        return obj


# todo: support for lists

class rolist(collections.abc.Sequence):
    # todo: implement

    @classmethod
    def wrap(cls, l):
        raise NotImplementedError

    def __getitem__(self, index):
        if isinstance(index, int):
            return self._data[index]
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def unwrap(self):
        """Return a regular (nested) list/dict structure."""
        return self._data

    def __repr__(self):
        return '{}.{.__name__}({!r})'.format(
            __name__, type(self), self._data)


class list(rolist, collections.abc.MutableSequence):
    """
    list-like container with support for nested lookups and type checking.
    """
    # todo: implement

    def __setitem__(self, index, value):
        raise NotImplementedError

    def insert(self, index, value):
        raise NotImplementedError

    def __delitem__(self, index):
        raise NotImplementedError


# internal aliases to make the code above less confusing
sanest_dict = dict
sanest_read_only_dict = rodict
sanest_list = list
sanest_read_only_list = rolist
