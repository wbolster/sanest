"""
sanest, sane nested dictionaries and lists
"""

import abc
import builtins
import collections
import collections.abc
import copy

try:
    # Python 3.6+
    from collections.abc import Collection as BaseCollection
except ImportError:
    # Python 3.5 and earlier
    class BaseCollection(
            collections.abc.Sized,
            collections.abc.Iterable,
            collections.abc.Container):
        pass

ATOMIC_TYPES = (bool, float, int, str)
CONTAINER_TYPES = (builtins.dict, builtins.list)
TYPES = CONTAINER_TYPES + ATOMIC_TYPES
PATH_SYNTAX_TYPES = (builtins.tuple, builtins.list)


class Missing:
    def __repr__(self):
        return '<missing>'


MISSING = Missing()


class InvalidPathError(TypeError):
    """
    Exception raised when a path is invalid.

    This is a subclass of the built-in ``TypeError``, since this
    indicates problematic code that uses an incorrect API.
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
    ``InvalidValueError``, and can be caught instead of the more
    specific exception types.

    This is a subclass of the built-in ``ValueError``.
    """


class InvalidStructureError(DataError):
    """
    Exception raised when a nested structure does not match the request.

    This is a subclass of ``DataError`` and the built-in ``ValueError``,
    since this indicates malformed data.
    """
    pass


class InvalidValueError(DataError):
    """
    Exception raised when requesting or providing an invalid value.

    This is a subclass of ``DataError`` and the built-in ``ValueError``.
    """
    pass


def validate_path(path):
    if not path:
        raise InvalidPathError(
            "empty path or path component: {!r}".format(path))
    for k in path:
        # explicitly check for booleans, since bool is a subclass of int.
        if isinstance(k, bool) or not isinstance(k, (int, str)):
            raise InvalidPathError(
                "path must contain only str or int: {!r}".format(path))
        if k == '':
            raise InvalidPathError(
                "empty path or path component: {!r}".format(path))


def validate_type(type):
    if type not in TYPES:
        raise InvalidTypeError(
            "type must be one of {}: {!r}"
            .format(', '.join(t.__name__ for t in TYPES), type))


def validate_value(value):
    if not isinstance(value, TYPES):
        raise InvalidValueError(
            "invalid value of type {.__name__}: {!r}"
            .format(builtins.type(value), value))
    if isinstance(value, builtins.dict):
        collections.deque(validated_items(value.items()), 0)  # fast looping
    elif isinstance(value, builtins.list):
        validate_list(value)


def validated_items(iterable):
    for key, value in iterable:
        if not isinstance(key, str) or not key:
            raise InvalidPathError("invalid dict key: {!r}".format(key))
        if value is not None:
            validate_value(value)
        yield key, value


def validate_list(l):
    for value in l:
        if value is not None:
            validate_value(value)


def pairs(*args, **kwargs):
    """
    Yield key/value pairs, handling args like the ``dict()`` does.

    Checks that keys are sane.
    """
    if args:
        other, *rest = args
        if rest:
            raise TypeError(
                "expected at most 1 argument, got {0:d}".format(len(args)))
        if isinstance(other, collections.abc.Mapping):
            yield from other.items()
        elif hasattr(other, "keys"):  # dict-like
            for key in other.keys():
                yield key, other[key]
        else:
            yield from other  # sequence of pairs
    yield from kwargs.items()


def wrap(value, *, check=True):
    """
    Wrap a container (dict or list) without making a copy.
    """
    if isinstance(value, builtins.dict):
        return sanest_dict.wrap(value, check=check)
    if isinstance(value, builtins.list):
        return sanest_list.wrap(value, check=check)
    raise TypeError("not a dict or list: {!r}".format(value))


def parse_slice(sl, pathspec, *, allow_list):
    if sl.step is not None:
        raise InvalidPathError(
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
            raise InvalidPathError(
                "mixed path syntaxes: {!r}".format(pathspec))
        return None, sl.start, sl.stop
    raise InvalidPathError(
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
        raise InvalidPathError(
            "path must contain only str or int: {!r}".format(pathspec))
    if simple_key == '' and allow_empty_string:
        pass
    else:
        validate_path(path)
    if type is not None:
        if not allow_type:
            raise InvalidPathError(
                "path must contain only str or int: {!r}".format(pathspec))
        validate_type(type)
    return simple_key, path, type


def check_type(value, *, type, path):
    if not isinstance(value, type):
        raise InvalidValueError(
            "expected {.__name__}, got {.__name__} at path {}: {!r}"
            .format(type, builtins.type(value), path, value))


def resolve_path(obj, path, *, partial=False, create=False):
    assert isinstance(obj, CONTAINER_TYPES)
    if isinstance(path[0], int) and isinstance(obj, builtins.dict):
        raise InvalidPathError(
            "dict path did not start with str: {!r}".format(path))
    elif isinstance(path[0], str) and isinstance(obj, builtins.list):
        raise InvalidPathError(
            "list path did not start with int: {!r}".format(path))
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
        if partial and len(path) - 1 == n:
            break
        try:
            obj = obj[key_or_index]  # may raise KeyError or IndexError
        except KeyError:  # for dicts
            if create:
                obj[key_or_index] = obj = {}  # autovivification
            else:
                raise KeyError(path[:n+1]) from None
        except IndexError:  # for list
            raise IndexError(path[:n+1]) from None
    tail = path[-1]
    if partial:
        return obj, tail
    else:
        return obj


def lookup(collection, x, *, type=None):
    assert isinstance(collection, CONTAINER_TYPES)  # fixme
    if type is not None:
        validate_type(type)
    if isinstance(x, str) and isinstance(collection, builtins.dict):
        path = [x]
        value = collection[x]  # may raise KeyError
    elif (isinstance(x, int)
            and not isinstance(x, bool)
            and isinstance(collection, builtins.list)):
        path = [x]
        value = collection[x]  # may raise IndexError
    elif isinstance(x, PATH_SYNTAX_TYPES):
        path = x
        validate_path(path)
        value = resolve_path(collection, path)  # may raise any LookupError
    else:
        raise InvalidPathError(
            "path must contain only str or int: {!r}".format(x))
    if type is not None:
        check_type(value, type=type, path=path)
    return value


class SaneCollection(BaseCollection):
    """
    Base class for ``sanest.dict`` and ``sanest.list``.
    """
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

    def copy(self, *, deep=False):
        fn = copy.deepcopy if deep else copy.copy
        return fn(self)

    @abc.abstractmethod
    def wrap(cls, data, *, check=True):
        raise NotImplementedError

    @abc.abstractmethod
    def unwrap(self):
        raise NotImplementedError

    def lookup(self, key_index_or_path, *, type=None):
        value = lookup(self._data, key_index_or_path, type=type)
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value


class dict(SaneCollection, collections.abc.MutableMapping):
    """
    dict-like container with support for nested lookups and type checking.
    """
    __slots__ = ('_data',)

    def __init__(self, *args, **kwargs):
        self._data = {}
        if args or kwargs:
            self.update(*args, **kwargs)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        return cls((key, value) for key in iterable)

    @classmethod
    def wrap(cls, d, *, check=True):
        if isinstance(d, cls):
            return d  # already wrapped
        if not isinstance(d, builtins.dict):
            raise TypeError("not a dict")
        if check:
            collections.deque(validated_items(d.items()), 0)  # fast looping
        obj = cls.__new__(cls)
        obj._data = d
        return obj

    def unwrap(self):
        """
        Return a regular ``dict`` without making a copy.

        This ``sanest.dict`` can be safely used afterwards as long
        as the return value is treated as read-only.
        """
        return self._data

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return '{}.{.__name__}({!r})'.format(
            __name__, type(self), self._data)

    def __eq__(self, other):
        if self is other:
            return True
        if isinstance(other, sanest_dict):
            return self._data == other._data
        if isinstance(other, builtins.dict):
            return self._data == other
        return NotImplemented

    def __getitem__(self, key_or_path):
        if isinstance(key_or_path, str):  # fast path
            value = self._data[key_or_path]
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value, check=False)
            return value
        key, path, type = parse_pathspec(
            key_or_path, allow_type=True, allow_empty_string=True)
        key_or_path = path if key is None else key  # type stripped off
        value = self.get(key_or_path, MISSING, type=type)
        if value is MISSING:
            raise KeyError(key_or_path)
        return value

    def get(self, key_or_path, default=None, *, type=None):
        try:
            return self.lookup(key_or_path, type=type)
        except LookupError:
            return default

    def contains(self, key_or_path, *, type=None):
        try:
            self.lookup(key_or_path, type=type)
        except (DataError, LookupError):
            return False
        else:
            return True

    def __contains__(self, key_or_path):
        if isinstance(key_or_path, str):  # fast path
            # e.g. 'a' in d
            return key_or_path in self._data
        path = key_or_path
        if isinstance(path, PATH_SYNTAX_TYPES) and path and path[-1] in TYPES:
            # e.g. ['a', 'b', int] in d  (slice syntax not possible)
            *path, type = path
            return self.contains(path, type=type)
        else:
            # e.g. ['a', 'b'] in d
            return self.contains(path)

    def set(self, key_or_path, value, *, type=None):
        if type is not None:
            validate_type(type)
        if isinstance(value, (sanest_dict, sanest_list)):
            value = value.unwrap()
        elif value is not None:
            validate_value(value)
        if isinstance(key_or_path, str) and key_or_path and type is None:
            # fast path
            d = self._data
            key = key_or_path
        else:
            _, path, _ = parse_pathspec(key_or_path, allow_type=False)
            if type is not None and value is not None:
                check_type(value, type=type, path=path)
            d, key = resolve_path(self._data, path, partial=True, create=True)
        if value is None:
            d.pop(key, None)
        else:
            d[key] = value

    def setdefault(self, key_or_path, default=None, *, type=None):
        value = self.get(key_or_path, MISSING, type=type)
        if value is MISSING:
            self.set(key_or_path, default, type=type)
            value = default
        return value

    def __setitem__(self, key_or_path, value):
        simple_key, path, type = parse_pathspec(
            key_or_path, allow_type=True, allow_empty_string=False)
        self.set(
            path if simple_key is None else simple_key,
            value,
            type=type)

    def update(self, *args, **kwargs):
        for key, value in validated_items(pairs(*args, **kwargs)):
            if value is None:
                self._data.pop(key, None)
            else:
                self._data[key] = value

    def pop(self, key_or_path, default=MISSING, *, type=None):
        if type is not None:
            validate_type(type)
        if isinstance(key_or_path, str):  # fast path
            d = self._data
            key = key_or_path
            path = [key]
            value = d.get(key, MISSING)
        else:
            _, path, _ = parse_pathspec(
                key_or_path, allow_type=False, allow_empty_string=True)
            if not isinstance(path[-1], str):
                raise InvalidPathError("path must point to a dict key")
            try:
                d, key = resolve_path(self._data, path, partial=True)
                value = d[key]
            except LookupError:
                value = MISSING
        if value is MISSING:
            if default is MISSING:
                raise KeyError(key_or_path) from None
            return default
        if type is not None:
            check_type(value, type=type, path=path)
        del d[key]
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value

    def popitem(self, *, type=None):
        try:
            key = next(iter(self._data))
        except StopIteration:
            raise KeyError("dictionary is empty") from None
        value = self.get(key, type=type)
        del self._data[key]
        return key, value

    def __delitem__(self, key_or_path):
        if isinstance(key_or_path, str):  # fast path
            del self._data[key_or_path]
            return
        key, path, type = parse_pathspec(
            key_or_path, allow_type=True, allow_empty_string=False)
        self.pop(path if key is None else key, type=type)

    def clear(self):
        self._data.clear()


class list(SaneCollection, collections.abc.MutableSequence):
    """
    list-like container with support for nested lookups and type checking.
    """
    # todo: implement

    def __init__(self, *args):
        self._data = []
        if args:
            iterable, *rest = args
            if rest:
                raise TypeError(
                    "expected at most 1 argument, got {0:d}".format(len(args)))
            self.extend(iterable)

    @classmethod
    def wrap(cls, l, *, check=True):
        if isinstance(l, cls):
            return l  # already wrapped
        if not isinstance(l, builtins.list):
            raise TypeError("not a list")
        for value in l:
            validate_value(value)
        obj = cls.__new__(cls)
        obj._data = l
        return obj

    def unwrap(self):
        """
        Return a regular ``list`` without making a copy.

        This ``sanest.list`` can be safely used afterwards as long
        as the return value is treated as read-only.
        """
        return self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return '{}.{.__name__}({!r})'.format(
            __name__, type(self), self._data)

    def __eq__(self, other):
        if self is other:
            return True
        if isinstance(other, sanest_list):
            return self._data == other._data
        if isinstance(other, builtins.list):
            return self._data == other
        return NotImplemented

    def __getitem__(self, index_or_path):
        if isinstance(index_or_path, int):  # fast path
            return self._data[index_or_path]
        _, path, type = parse_pathspec(index_or_path, allow_type=True)
        value = lookup(self._data, path, type=type)
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value

    def contains(self, value, *, type=None):
        raise NotImplementedError

    def __contains__(self, value):
        if (isinstance(value, PATH_SYNTAX_TYPES)
                and value and value[-1] in TYPES):
            # e.g. ['a', int] in l  (slice syntax not possible)
            *value, type = value
            return self.contains(value, type=type)
        else:
            # e.g. 'a' in l
            return value in self._data

    def index(self, value, start=0, stop=None, *, type=None):
        if type is None:
            return self._data.index(value, start, stop)
        raise NotImplementedError

    def count(self, value, *, type=None):
        if type is not None:
            return self._data.count(value)
        raise NotImplementedError

    def __reversed__(self):
        return reversed(self._data)

    def __setitem__(self, index, value):
        raise NotImplementedError

    def insert(self, index_or_path, value, *, type=None):
        if type is not None:
            validate_type(type)
        if isinstance(value, (sanest_dict, sanest_list)):
            value = value.unwrap()
        if isinstance(index_or_path, int) and type is None:  # fast path
            self._data.insert(index_or_path, value)
            return
        raise NotImplementedError

    def append(self, value, *, type=None):
        self.insert(len(self), value, type=type)

    def extend(self, iterable, *, type=None):
        for value in iterable:
            self.append(value, type=type)

    def pop(self, index=-1, *, type=None):
        raise NotImplementedError

    def __delitem__(self, index):
        if isinstance(index, int):  # fast path
            del self._data[index]
        # todo: path support
        raise NotImplementedError

    def remove(self, value, *, type=None):
        del self[self.index(value, type=type)]

    def clear(self):
        self._data.clear()

    def reverse(self):
        self._data.reverse()

    def sort(self, key=None, reverse=False):
        self._data.sort(key=key, reverse=reverse)


# internal aliases to make the code above less confusing
sanest_dict = dict
sanest_list = list
