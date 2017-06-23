import abc
import builtins
import collections
import collections.abc
import copy
import reprlib
import sys

try:
    # Python 3.6+
    from collections.abc import Collection
except ImportError:  # pragma: no cover
    # Python 3.5 and earlier
    class Collection(
            collections.abc.Sized,
            collections.abc.Iterable,
            collections.abc.Container):
        pass

ATOMIC_TYPES = (bool, float, int, str)
CONTAINER_TYPES = (builtins.dict, builtins.list)
TYPES = CONTAINER_TYPES + ATOMIC_TYPES
PATH_SYNTAX_TYPES = (builtins.tuple, builtins.list)

typeof = builtins.type


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
    if not path:
        raise InvalidPathError("empty path: {!r}".format(path))
    if any(type(k) not in (int, str) for k in path):
        raise InvalidPathError(
            "path must contain only str or int: {!r}".format(path))


def validate_type(type):
    """
    Validate that ``type`` is a valid argument for type checking purposes.
    """
    if type in TYPES:
        return
    if typeof(type) is builtins.list and len(type) == 1 and type[0] in TYPES:
        # e.g. [str], [dict]
        return
    if typeof(type) is builtins.dict and len(type) == 1:
        # e.g. {str: int}, {str: [list]}
        key, value = next(iter(type.items()))
        if key is str and value in TYPES:
            return
    raise InvalidTypeError(
        "expected {}, [...] (for lists) or {{str: ...}} (for dicts), got {}"
        .format(', '.join(t.__name__ for t in TYPES), reprlib.repr(type)))


def validate_value(value):
    if value is None:
        return
    if type(value) not in TYPES:
        raise InvalidValueError(
            "invalid value of type {.__name__}: {}"
            .format(type(value), reprlib.repr(value)))
    if type(value) is builtins.dict:
        collections.deque(validated_items(value.items()), 0)  # fast looping
    elif type(value) is builtins.list:
        collections.deque(validated_values(value), 0)  # fast looping


def validated_items(iterable):
    for key, value in iterable:
        if type(key) is not str:
            raise InvalidPathError("invalid dict key: {!r}".format(key))
        validate_value(value)
        yield key, value


def validated_values(iterable):
    for value in iterable:
        validate_value(value)
        yield value


def pairs(*args, **kwargs):
    """
    Yield key/value pairs, handling args like the ``dict()`` built-in does.

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


def is_regular_list_slice(sl):
    return (
        (sl.start is None or type(sl.start) is int)
        and (sl.stop is None or type(sl.stop) is int)
        and (sl.step is None or type(sl.step) is int))


def wrap(value, *, check=True):
    """
    Wrap a container (dict or list) without making a copy.
    """
    if type(value) is builtins.dict:
        return sanest_dict.wrap(value, check=check)
    if type(value) is builtins.list:
        return sanest_list.wrap(value, check=check)
    raise TypeError("not a dict or list: {!r}".format(value))


def parse_path_like(path):
    if type(path) in (str, int):
        return path, [path]
    if type(path) in PATH_SYNTAX_TYPES:
        validate_path(path)
        return None, path
    raise InvalidPathError("invalid path: {!r}".format(path))


def parse_path_like_with_type(x, *, allow_slice=True):
    sl = None
    if typeof(x) in (int, str):
        # e.g. d['a'] and d[2]
        key_or_index = x
        path = [key_or_index]
        type = None
    elif allow_slice and typeof(x) is slice:
        sl = x
        if typeof(sl.start) in PATH_SYNTAX_TYPES:
            # e.g. d[path:str]
            key_or_index = None
            path = sl.start
            validate_path(path)
        else:
            # e.g. d['a':str] and d[2:str]
            key_or_index = sl.start
            path = [key_or_index]
    elif typeof(x) in PATH_SYNTAX_TYPES:
        # e.g. d['a', 'b'] and d[path] and d['a', 'b':str]
        key_or_index = None
        path = builtins.list(x)  # makes a copy
        type = None
        if path:
            if allow_slice and typeof(path[-1]) is slice:
                # e.g. d['a', 'b':str]
                sl = path.pop()
                if typeof(sl.start) in PATH_SYNTAX_TYPES:
                    raise InvalidPathError(
                        "mixed path syntaxes: {!r}".format(x))
                path.append(sl.start)
            elif not allow_slice and path[-1] in TYPES:
                # e.g. ['a', 'b', str]
                type = path.pop()
                if len(path) == 1 and typeof(path[0]) in PATH_SYNTAX_TYPES:
                    # e.g. [path, str]
                    path = path[0]
        validate_path(path)
    else:
        raise InvalidPathError("invalid path: {!r}".format(x))
    if sl is not None:
        if sl.stop is None:
            raise InvalidPathError(
                "type is required for slice syntax: {!r}".format(x))
        type = sl.stop
        if sl.step is not None:
            raise InvalidPathError(
                "step value not allowed for slice syntax: {!r}".format(x))
    if type is not None:
        validate_type(type)
    return key_or_index, path, type


def repr_for_type(type):
    """
    Return a friendly repr() for a type checking argument.
    """
    if type in TYPES:
        # e.g. str
        return type.__name__
    if typeof(type) is builtins.list:
        # e.g. [int]
        return '[{}]'.format(type[0].__name__)
    if typeof(type) is builtins.dict:
        # e.g. {str: bool}
        return '{{str: {}}}'.format(next(iter(type.values())).__name__)
    raise ValueError("invalid type: {!r}".format(type))


def check_type(value, *, type, path=None):
    """
    Check that the type of ``value`` matches what ``type`` prescribes.
    """
    # note: type checking is extremely strict: it avoids isinstance()
    # to avoid booleans passing as integers, and to avoid subclasses of
    # built-in types which will likely cause json serialisation errors
    # anyway.
    if type in TYPES and typeof(value) is type:
        # e.g. str, int
        return
    if typeof(type) is typeof(value) is builtins.list:
        # e.g. [str], [int]
        contained_type = type[0]
        if all(typeof(v) is contained_type for v in value):
            return
        actual = "non-conforming list"
    elif typeof(type) is typeof(value) is builtins.dict:
        # e.g. {str: bool}
        contained_type = type[next(iter(type))]  # first dict value
        if all(typeof(v) is contained_type for v in value.values()):
            return
        actual = "non-conforming dict"
    else:
        actual = typeof(value).__name__
    raise InvalidValueError("expected {}, got {}{}: {}".format(
        repr_for_type(type),
        actual,
        '' if path is None else ' at path {}'.format(path),
        reprlib.repr(value)))


def clean_value(value, *, type=None):
    """
    Obtain a clean value by checking types and unwrapping containers.

    This function performs basic input validation for container methods
    accepting a value argument from their caller.
    """
    if type is not None:
        validate_type(type)
    if typeof(value) in SANEST_CONTAINER_TYPES:
        value = value._data
    elif value is not None:
        validate_value(value)
    if type is not None:
        check_type(value, type=type)
    return value


def resolve_path(obj, path, *, partial=False, create=False):
    if type(path[0]) is int and type(obj) is builtins.dict:
        raise InvalidPathError(
            "dict path must start with str: {!r}".format(path))
    elif type(path[0]) is str and type(obj) is builtins.list:
        raise InvalidPathError(
            "list path must start with int: {!r}".format(path))
    for n, key_or_index in enumerate(path):
        if type(key_or_index) is str and type(obj) is not builtins.dict:
            raise InvalidStructureError(
                "expected dict, got {.__name__} at subpath {!r} of {!r}"
                .format(type(obj), path[:n], path))
        if type(key_or_index) is int and type(obj) is not builtins.list:
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


class SaneCollection(Collection):
    """
    Base class for ``sanest.dict`` and ``sanest.list``.
    """
    @abc.abstractmethod
    def wrap(cls, data, *, check=True):
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def unwrap(self):
        raise NotImplementedError  # pragma: no cover

    def __len__(self):
        return len(self._data)

    def __getitem__(self, path_like):
        key_or_index, path, type = parse_path_like_with_type(path_like)
        value = resolve_path(self._data, path)
        if type is not None:
            check_type(value, type=type, path=path)
        if typeof(value) in CONTAINER_TYPES:
            value = wrap(value, check=False)
        return value

    def __setitem__(self, path_like, value):
        key_or_index, path, type = parse_path_like_with_type(path_like)
        value = clean_value(value, type=type)
        obj, key_or_index = resolve_path(
            self._data, path, partial=True, create=True)
        try:
            obj[key_or_index] = value
        except IndexError as exc:  # list assignment can fail
            raise IndexError(path) from None

    def __delitem__(self, x):
        key_or_index, path, type = parse_path_like_with_type(x)
        obj, key_or_index = resolve_path(self._data, path, partial=True)
        try:
            if type is not None:
                value = obj[key_or_index]
                check_type(value, type=type, path=path)
            del obj[key_or_index]
        except LookupError as exc:
            raise typeof(exc)(path) from None

    def clear(self):
        self._data.clear()

    def __eq__(self, other):
        if self is other:
            return True
        if type(other) is type(self):
            if self._data is other._data:
                return True
            return self._data == other._data
        if type(other) in CONTAINER_TYPES:
            return self._data == other
        return NotImplemented

    def __repr__(self):
        return '{}.{.__name__}({!r})'.format(
            __package__, type(self), self._data)

    def _truncated_repr(self):
        return '{}.{.__name__}({})'.format(
            __package__, type(self), reprlib.repr(self._data))

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
        if type(d) is cls:
            return d  # already wrapped
        if type(d) is not builtins.dict:
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

    def check_types(self, *, type):
        """
        Check the type of all values in this dict.
        """
        validate_type(type)
        for key, value in self._data.items():
            check_type(value, type=type, path=[key])

    def __iter__(self):
        return iter(self._data)

    def get(self, path_like, default=None, *, type=None):
        if type is not None:
            validate_type(type)
        key, path = parse_path_like(path_like)
        if typeof(path[-1]) is not str:
            raise InvalidPathError("path must lead to dict key")
        try:
            if typeof(key) is str:
                value = self._data[key]
            else:
                value = resolve_path(self._data, path)
        except LookupError:
            return default
        if type is not None:
            check_type(value, type=type, path=path)
        if typeof(value) in CONTAINER_TYPES:
            value = wrap(value, check=False)
        return value

    def contains(self, path_like, *, type=None):
        key, path = parse_path_like(path_like)
        try:
            if type is None:
                self[path]
            else:
                self[path:type]
        except (LookupError, DataError):
            return False
        else:
            return True

    def __contains__(self, path_like):
        if typeof(path_like) is str:  # fast path
            # e.g. 'a' in d
            return path_like in self._data
        # e.g. ['a', 'b'] and ['a', 'b', int] (slice syntax not possible)
        _, path, type = parse_path_like_with_type(path_like, allow_slice=False)
        return self.contains(path, type=type)

    def setdefault(self, path_like, default=None, *, type=None):
        if default is None:
            raise InvalidValueError("setdefault() requires a default value")
        value = self.get(path_like, MISSING, type=type)
        if value is MISSING:
            # default value validation is done by set()
            key, path = parse_path_like(path_like)
            if type is None:
                self[path] = default
            else:
                self[path:type] = default
            value = default
            if typeof(value) in CONTAINER_TYPES:
                value = wrap(value, check=False)
        else:
            # check default value even if an existing value was found,
            # so that this method is strict regardless of dict contents.
            clean_value(default, type=type)
        return value

    def update(self, *args, **kwargs):
        self._data.update(validated_items(pairs(*args, **kwargs)))

    def pop(self, path_like, default=MISSING, *, type=None):
        if type is not None:
            validate_type(type)
        if typeof(path_like) is str:  # fast path
            d = self._data
            key = path_like
            path = [key]
            value = d.get(key, MISSING)
        else:
            _, path = parse_path_like(path_like)
            if typeof(path[-1]) is not str:
                raise InvalidPathError("path must lead to dict key")
            try:
                d, key = resolve_path(self._data, path, partial=True)
            except LookupError:
                if default is MISSING:
                    raise   # contains partial path in exception message
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
        if typeof(value) in CONTAINER_TYPES:
            value = wrap(value, check=False)
        return value

    def popitem(self, *, type=None):
        try:
            key = next(iter(self._data))
        except StopIteration:
            raise KeyError(reprstr("dictionary is empty")) from None
        value = self.pop(key, type=type)
        return key, value

    def keys(self):
        return DictKeysView(self)

    def values(self, *, type=None):
        if type is not None:
            self.check_types(type=type)
        return DictValuesView(self)

    def items(self, *, type=None):
        if type is not None:
            self.check_types(type=type)
        return DictItemsView(self)


class DictKeysView(collections.abc.KeysView):
    __slots__ = ()

    def __repr__(self):
        return '{}.keys()'.format(self._mapping._truncated_repr())


class DictValuesView(collections.abc.ValuesView):
    __slots__ = ('_sanest_dict')

    def __init__(self, d):
        self._sanest_dict = d
        super().__init__(d)

    def __repr__(self):
        return '{}.values()'.format(self._mapping._truncated_repr())

    def __contains__(self, value):
        value = clean_value(value)
        return any(  # pragma: no branch
            v is value or v == value
            for v in self._sanest_dict._data.values())

    def __iter__(self):
        for value in self._sanest_dict._data.values():
            if type(value) in CONTAINER_TYPES:
                value = wrap(value, check=False)
            yield value


class DictItemsView(collections.abc.ItemsView):
    __slots__ = ('_sanest_dict')

    def __init__(self, d):
        self._sanest_dict = d
        super().__init__(d)

    def __repr__(self):
        return '{}.items()'.format(self._mapping._truncated_repr())

    def __contains__(self, item):
        key, value = item
        value = clean_value(value)
        try:
            v = self._sanest_dict[key]
        except KeyError:
            return False
        else:
            return v is value or v == value

    def __iter__(self):
        for key, value in self._sanest_dict._data.items():
            if type(value) in CONTAINER_TYPES:
                value = wrap(value, check=False)
            yield key, value


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
        if type(l) is cls:
            return l  # already wrapped
        if type(l) is not builtins.list:
            raise TypeError("not a list")
        if check:
            collections.deque(validated_values(l), 0)  # fast looping
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

    def check_types(self, *, type):
        """
        Check the type of all values in this list.
        """
        validate_type(type)
        for index, value in enumerate(self._data):
            check_type(value, type=type, path=[index])

    def __iter__(self):
        for value in self._data:
            if type(value) in CONTAINER_TYPES:
                value = wrap(value, check=False)
            yield value

    def iter(self, *, type=None):
        if type is not None:
            self.check_types(type=type)
        return iter(self)

    def __getitem__(self, path_like):
        if type(path_like) is slice and is_regular_list_slice(path_like):
            return sanest_list.wrap(self._data[path_like], check=False)
        return super().__getitem__(path_like)

    def __setitem__(self, path_like, value):
        if type(path_like) is slice and is_regular_list_slice(path_like):
            # slice assignment takes any iterable, like .extend()
            if isinstance(value, (str, bytes, bytearray)):
                raise TypeError(
                    "expected iterable that is not string-like, "
                    "got {.__name__}".format(type(value)))
            if type(value) in SANEST_CONTAINER_TYPES:
                value = value._data
            else:
                value = validated_values(value)
            self._data[path_like] = value
        else:
            return super().__setitem__(path_like, value)

    def __delitem__(self, path_like):
        if type(path_like) is slice and is_regular_list_slice(path_like):
            del self._data[path_like]
        else:
            return super().__delitem__(path_like)

    def __lt__(self, other):
        if type(other) is type(self):
            return self._data < other._data
        if type(other) is builtins.list:
            return self._data < other
        return NotImplemented

    def __le__(self, other):
        if type(other) is type(self):
            return self._data <= other._data
        if type(other) is builtins.list:
            return self._data <= other
        return NotImplemented

    def __gt__(self, other):
        if type(other) is type(self):
            return self._data > other._data
        if type(other) is builtins.list:
            return self._data > other
        return NotImplemented

    def __ge__(self, other):
        if type(other) is type(self):
            return self._data >= other._data
        if type(other) is builtins.list:
            return self._data >= other
        return NotImplemented

    def __contains__(self, value):
        return clean_value(value) in self._data

    def index(self, value, start=0, stop=None, *, type=None):
        if stop is None:
            stop = sys.maxsize
        return self._data.index(clean_value(value, type=type), start, stop)

    def count(self, value, *, type=None):
        return self._data.count(clean_value(value, type=type))

    def __reversed__(self):
        for value in reversed(self._data):
            if type(value) in CONTAINER_TYPES:
                value = wrap(value, check=False)
            yield value

    def insert(self, index, value, *, type=None):
        self._data.insert(index, clean_value(value, type=type))

    def append(self, value, *, type=None):
        self._data.append(clean_value(value, type=type))

    def extend(self, iterable, *, type=None):
        if typeof(iterable) is typeof(self):
            self._data.extend(iterable._data)
        elif isinstance(iterable, (str, bytes, bytearray)):
            raise TypeError(
                "expected iterable that is not string-like, got {.__name__}"
                .format(typeof(iterable)))
        else:
            for value in iterable:
                self.append(value, type=type)

    def __add__(self, other):
        if type(other) not in (type(self), builtins.list):
            raise TypeError(
                "expected list, got {.__name__}".format(type(other)))
        result = self.copy()
        result.extend(other)
        return result

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __radd__(self, other):
        return other + self._data

    def __mul__(self, n):
        return type(self).wrap(self._data * n, check=False)

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
        if typeof(value) in CONTAINER_TYPES:
            value = wrap(value, check=False)
        return value

    def remove(self, value, *, type=None):
        value = clean_value(value, type=type)
        try:
            self._data.remove(value)
        except ValueError:
            raise ValueError("{!r} is not in list".format(value)) from None

    def reverse(self):
        self._data.reverse()

    def sort(self, key=None, reverse=False):
        self._data.sort(key=key, reverse=reverse)


# internal aliases to make the code above less confusing
sanest_dict = dict
sanest_list = list

SANEST_CONTAINER_TYPES = (sanest_dict, sanest_list)
