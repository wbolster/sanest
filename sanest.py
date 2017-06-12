"""
sanest, sane nested dictionaries and lists
"""

import abc
import builtins
import collections
import collections.abc
import copy
import sys

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


class reprstr(str):
    """
    String with a repr() identical to str().

    This is a hack to "undo" an unwanted repr() made by code that
    cannot be changed. Practically, this prevents quote characters
    around the string.
    """
    def __repr__(self):
        return self


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
    if not isinstance(path, PATH_SYNTAX_TYPES):
        raise InvalidPathError(
            "path must contain only str or int: {!r}".format(path))
    if not path:
        raise InvalidPathError("invalid path: {!r}".format(path))
    for k in path:
        # explicitly check for booleans, since bool is a subclass of int.
        if isinstance(k, bool) or not isinstance(k, (int, str)):
            raise InvalidPathError(
                "path must contain only str or int: {!r}".format(path))
        if k == '':
            raise InvalidPathError("invalid path: {!r}".format(path))


def validate_type(type):
    if type not in TYPES:
        raise InvalidTypeError(
            "type must be one of {}: {!r}"
            .format(', '.join(t.__name__ for t in TYPES), type))


def validate_value(value):
    if value is None:
        return
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
        validate_value(value)
        yield key, value


def validate_list(l):
    for value in l:
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


def parse_path_like(path, allow_empty_string=False):
    if type(path) in (str, int):
        if path == '' and not allow_empty_string:
            raise InvalidPathError("invalid path: {!r}".format(['']))
        return path, [path]
    if isinstance(path, PATH_SYNTAX_TYPES):
        validate_path(path)
        return None, path
    raise InvalidPathError("invalid path: {!r}".format(path))


def parse_path_like_with_type(x, *, allow_slice=True):
    sl = None
    if isinstance(x, (int, str)) and not isinstance(x, bool):
        # e.g. d['a'] and d[2]
        key_or_index = x
        path = [key_or_index]
        type = None
    elif allow_slice and isinstance(x, slice):
        sl = x
        if isinstance(sl.start, PATH_SYNTAX_TYPES):
            # e.g. d[path:str]
            key_or_index = None
            path = sl.start
            validate_path(path)
            type = sl.stop
        else:
            # e.g. d['a':str] and d[2:str]
            key_or_index = sl.start
            path = [key_or_index]
            type = sl.stop
    elif isinstance(x, PATH_SYNTAX_TYPES):
        # e.g. d['a', 'b'] and d[path] and d['a', 'b':str]
        key_or_index = None
        path = builtins.list(x)  # makes a copy
        type = None
        if path:
            if allow_slice and isinstance(path[-1], slice):
                # e.g. d['a', 'b':str]
                sl = path.pop()
                if isinstance(sl.start, PATH_SYNTAX_TYPES):
                    raise InvalidPathError(
                        "mixed path syntaxes: {!r}".format(x))
                path.append(sl.start)
                type = sl.stop
            elif not allow_slice and path[-1] in TYPES:
                # e.g. ['a', 'b', str]
                type = path.pop()
                if len(path) == 1 and isinstance(path[0], PATH_SYNTAX_TYPES):
                    # e.g. [path, str]
                    path = path[0]
        validate_path(path)
    else:
        raise InvalidPathError("invalid path: {!r}".format(x))
    if sl is not None and sl.step is not None:
        raise InvalidPathError(
            "step value not allowed for slice syntax: {!r}".format(sl))
    if type is not None:
        validate_type(type)
    return key_or_index, path, type


def check_type(value, *, type, path=None):
    if not isinstance(value, type):
        at_path = '' if path is None else ' at path {}'.format(path)
        raise InvalidValueError(
            "expected {.__name__}, got {.__name__}{}: {!r}"
            .format(type, builtins.type(value), at_path, value))


def resolve_path(obj, path, *, partial=False, create=False):
    assert isinstance(obj, CONTAINER_TYPES)
    if isinstance(path[0], int) and isinstance(obj, builtins.dict):
        raise InvalidPathError(
            "dict path must start with str: {!r}".format(path))
    elif isinstance(path[0], str) and isinstance(obj, builtins.list):
        raise InvalidPathError(
            "list path must start with int: {!r}".format(path))
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
        except IndexError:  # for lists
            raise IndexError(path[:n+1]) from None
    tail = path[-1]
    if partial:
        return obj, tail
    else:
        return obj


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
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def unwrap(self):
        raise NotImplementedError  # pragma: no cover


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

    def __getitem__(self, path_and_type_slice):
        key, path, type = parse_path_like_with_type(path_and_type_slice)
        if isinstance(key, str):
            try:
                value = self._data[key]
            except KeyError:
                raise KeyError(path) from None
        else:
            value = resolve_path(self._data, path)
        if type is not None:
            check_type(value, type=type, path=path)
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value

    def get(self, path_like, default=None, *, type=None):
        if type is not None:
            validate_type(type)
        key, path = parse_path_like(path_like, allow_empty_string=True)
        if key == '':
            return default
        assert isinstance(path[-1], str)
        try:
            if isinstance(key, str):
                value = self._data[key]
            else:
                value = resolve_path(self._data, path)
        except LookupError:
            return default
        if type is not None:
            check_type(value, type=type, path=path)
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value

    def contains(self, path_like, *, type=None):
        key, path = parse_path_like(path_like, allow_empty_string=True)
        if key == '':
            return False
        try:
            value = self.get(path, MISSING, type=type)
        except DataError:
            return False
        else:
            return value is not MISSING

    def __contains__(self, path_like):
        if isinstance(path_like, str):  # fast path
            # e.g. 'a' in d
            return path_like in self._data
        # e.g. ['a', 'b'] and ['a', 'b', int] (slice syntax not possible)
        _, path, type = parse_path_like_with_type(path_like, allow_slice=False)
        return self.contains(path, type=type)

    def set(self, path_like, value, *, type=None):
        key, path = parse_path_like(path_like)
        if type is not None:
            validate_type(type)
        if isinstance(value, SANEST_CONTAINER_TYPES):
            value = value.unwrap()
        else:
            validate_value(value)
        if type is not None:
            check_type(value, type=type, path=path)
        if isinstance(key, str):
            d = self._data
        else:
            d, key = resolve_path(self._data, path, partial=True, create=True)
        if value is None:
            # fixme: resolve_path creates leading paths even when
            # value is None which is supposed to remove values only.
            d.pop(key, None)
        else:
            d[key] = value

    def setdefault(self, path_like, default=None, *, type=None):
        if default is None:
            raise InvalidValueError("setdefault() requires a default value")
        value = self.get(path_like, MISSING, type=type)
        if value is MISSING:
            # default value validation is done by set()
            self.set(path_like, default, type=type)
            value = default
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value, check=False)
        else:
            # check default value even if an existing value was found,
            # so that this method is strict regardless of dict contents.
            validate_value(default)
            if type is not None:
                check_type(default, type=type)
        return value

    def __setitem__(self, path_like, value):
        key, path, type = parse_path_like_with_type(path_like)
        self.set(path, value, type=type)

    def update(self, *args, **kwargs):
        for key, value in validated_items(pairs(*args, **kwargs)):
            if value is None:
                self._data.pop(key, None)
            else:
                self._data[key] = value

    def pop(self, path_like, default=MISSING, *, type=None):
        if type is not None:
            validate_type(type)
        if isinstance(path_like, str):  # fast path
            d = self._data
            key = path_like
            path = [key]
            value = d.get(key, MISSING)
        else:
            _, path = parse_path_like(path_like)
            if not isinstance(path[-1], str):
                raise InvalidPathError("path must point to a dict key")
            try:
                d, key = resolve_path(self._data, path, partial=True)
            except LookupError:
                value = MISSING
            else:
                value = d.get(key, MISSING)
        if value is MISSING:
            if default is MISSING:
                raise KeyError(path) from None
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
            raise KeyError(reprstr("dictionary is empty")) from None
        value = self.pop(key, type=type)
        return key, value

    def __delitem__(self, x):
        if isinstance(x, str):
            try:
                del self._data[x]
                return
            except KeyError:
                raise KeyError([x]) from None
        key, path, type = parse_path_like_with_type(x)
        self.pop(path, type=type)

    def clear(self):
        self._data.clear()


class list(SaneCollection, collections.abc.MutableSequence):
    """
    list-like container with support for nested lookups and type checking.
    """
    __slots__ = ('_data',)

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
        if check:
            validate_list(l)
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
        for value in self._data:
            if isinstance(value, CONTAINER_TYPES):
                value = wrap(value, check=False)
            yield value

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

    def __getitem__(self, path_and_type_slice):
        index, path, type = parse_path_like_with_type(path_and_type_slice)
        if isinstance(index, int):
            try:
                value = self._data[index]
            except IndexError:
                raise IndexError(path) from None
        else:
            value = resolve_path(self._data, path)
        if type is not None:
            check_type(value, type=type, path=path)
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value

    def __contains__(self, value):
        if isinstance(value, SANEST_CONTAINER_TYPES):
            value = value.unwrap()  # gives faster comparisons
        else:
            validate_value(value)
        return value in self._data

    def index(self, value, start=0, stop=None, *, type=None):
        if stop is None:
            stop = sys.maxsize
        if isinstance(value, SANEST_CONTAINER_TYPES):
            value = value.unwrap()  # gives faster comparisons
        else:
            validate_value(value)
        if type is not None:
            check_type(value, type=type)
        return self._data.index(value, start, stop)

    def count(self, value, *, type=None):
        if isinstance(value, SANEST_CONTAINER_TYPES):
            value = value.unwrap()  # gives faster comparisons
        else:
            validate_value(value)
        if type is not None:
            check_type(value, type=type)
        return self._data.count(value)

    def __reversed__(self):
        return reversed(self._data)

    def __setitem__(self, path_like, value):
        index, path, type = parse_path_like_with_type(path_like)
        if isinstance(value, SANEST_CONTAINER_TYPES):
            value = value.unwrap()
        else:
            validate_value(value)
        if type is not None:
            check_type(value, type=type, path=path)
        if isinstance(index, int):
            obj = self._data
        else:
            obj, index = resolve_path(self._data, path, partial=True)
        try:
            obj[index] = value
        except LookupError as exc:
            raise builtins.type(exc)(path) from None

    def insert(self, index, value, *, type=None):
        if type is not None:
            validate_type(type)
        if isinstance(value, SANEST_CONTAINER_TYPES):
            value = value.unwrap()
        else:
            validate_value(value)
        if type is not None:
            check_type(value, type=type)
        self._data.insert(index, value)

    def append(self, value, *, type=None):
        self.insert(len(self), value, type=type)

    def extend(self, iterable, *, type=None):
        if isinstance(iterable, sanest_list):
            self._data.extend(iterable.unwrap())
        else:
            for value in iterable:
                self.append(value, type=type)

    def __add__(self, other):
        result = self.copy()
        result.extend(other)
        return result

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __radd__(self, other):
        return other + self.unwrap()

    def __mul__(self, n):
        return type(self).wrap(self.unwrap() * n, check=False)

    __rmul__ = __mul__

    def pop(self, index=-1, *, type=None):
        # todo: nested path pop() like dict.pop?
        if not self._data:
            raise IndexError("pop from empty list")
        try:
            value = self._data[index]
        except IndexError:
            raise IndexError(index) from None
        if type is not None:
            check_type(value, type=type, path=[index])
        del self._data[index]
        if isinstance(value, CONTAINER_TYPES):
            value = wrap(value, check=False)
        return value

    def __delitem__(self, index):
        if isinstance(index, int):  # fast path
            del self._data[index]
        # todo: path support
        raise NotImplementedError  # todo

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

SANEST_CONTAINER_TYPES = (sanest_dict, sanest_list)
