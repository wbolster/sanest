"""
tests for sanest
"""

import builtins
import copy
import pickle
import pprint
import sys
import textwrap

import IPython.lib.pretty
import pytest

import sanest
from sanest import sanest as _sanest  # internal module


class MyClass:
    def __repr__(self):
        return '<MyClass>'


#
# path parsing
#

class WithGetItem:
    def __getitem__(self, thing):
        return _sanest.parse_path_like_with_type(thing)


def test_parse_path_like_with_type_as_slice():
    x = WithGetItem()
    path = ['a', 'b']
    assert x['a'] == ('a', ['a'], None)
    assert x[2] == (2, [2], None)
    assert x['a':str] == ('a', ['a'], str)
    assert x[2:str] == (2, [2], str)
    assert x[path] == (None, ['a', 'b'], None)
    assert x[path:str] == (None, ['a', 'b'], str)
    assert x['a', 'b'] == (None, ['a', 'b'], None)
    assert x['a', 'b':str] == (None, ['a', 'b'], str)
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        empty_path = []
        x[empty_path]
    assert str(excinfo.value) == "empty path: []"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        x[1.23]
    assert str(excinfo.value) == "invalid path: 1.23"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        x['x', path:int]
    assert str(excinfo.value).startswith("mixed path syntaxes: ")
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        x[path, 'a':int]
    assert str(excinfo.value).startswith("path must contain only str or int: ")
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        x['a':int:str]
    assert str(excinfo.value).startswith(
        "step value not allowed for slice syntax: ")
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        x['a':None]
    assert str(excinfo.value).startswith("type is required for slice syntax: ")


def test_parse_path_like_with_type_in_list():
    f = _sanest.parse_path_like_with_type
    assert f('a', allow_slice=False) == ('a', ['a'], None)
    assert f(['a', str], allow_slice=False) == (None, ['a'], str)
    assert f(['a', 'b'], allow_slice=False) == (None, ['a', 'b'], None)
    assert f(['a', 'b', str], allow_slice=False) == (None, ['a', 'b'], str)
    path = ['a', 'b']
    assert f([path, str], allow_slice=False) == (None, ['a', 'b'], str)


#
# type checking
#

@pytest.mark.parametrize('t', [
    str,
    bool,
    int,
    float,
    dict,
    list,
    [str],
    [int],
    [dict],
    {str: int},
    {str: str},
    {str: list},
])
def test_validate_type(t):
    _sanest.validate_type(t)


@pytest.mark.parametrize('t', [
    None,
    bytes,
    object,
    'xyz',
    [None],
    [bytes],
    [object],
    ['xyz'],
    {'a': 'b'},
    {int: str},
    {str: bytes},
])
def test_validate_type_invalid(t):
    with pytest.raises(sanest.InvalidTypeError) as excinfo:
        _sanest.validate_type(t)
    assert str(excinfo.value).startswith('expected dict, list, ')


def test_type_checking_success():
    d = {
        'a': [
            {'b': 'c'},
            {'d': 'e'},
        ]
    }
    _sanest.check_type(d, type=dict)
    _sanest.check_type(d['a'], type=list)
    _sanest.check_type(d['a'], type=[dict])
    _sanest.check_type(d['a'][0], type=dict)
    _sanest.check_type(d['a'][0], type={str: str})


@pytest.mark.parametrize(('value', 'type', 'message'), [
    ('a', int, "expected int, got str"),
    (123, str, "expected str, got int"),
    (True, int, "expected int, got bool"),
    ([123, 'a', 'b'], [int], "expected [int], got non-conforming list"),
    ({'a': 123}, {str: str}, "expected {str: str}, got non-conforming dict"),
])
def test_type_checking_fails(value, type, message):
    _sanest.validate_type(type)
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        _sanest.check_type(value, type=type)
    assert str(excinfo.value).startswith("{}: ".format(message))


@pytest.mark.parametrize(('type', 'expected'), [
    (int, 'int'),
    (str, 'str'),
    ([dict], '[dict]'),
    ([int], '[int]'),
    ({str: str}, '{str: str}'),
    ({str: dict}, '{str: dict}'),
])
def test_type_repr(type, expected):
    actual = _sanest.repr_for_type(type)
    assert actual == expected


def test_type_repr_invalid():
    with pytest.raises(ValueError) as excinfo:
        _sanest.repr_for_type('foobar')
    assert str(excinfo.value) == "invalid type: 'foobar'"


#
# dicts
#

def test_pairs():
    actual = list(_sanest.pairs(a=1))
    expected = [("a", 1)]
    assert actual == expected

    actual = list(_sanest.pairs({'a': 1}, b=2))
    expected = [("a", 1), ("b", 2)]
    assert actual == expected

    actual = list(_sanest.pairs([("a", 1), ("b", 2)]))
    expected = [("a", 1), ("b", 2)]
    assert actual == expected

    class WithKeys:
        def keys(self):
            yield "a"
            yield "b"

        def __getitem__(self, key):
            return "x"

    actual = list(_sanest.pairs(WithKeys()))
    expected = [("a", "x"), ("b", "x")]
    assert actual == expected

    g = _sanest.pairs({}, {}, {})
    with pytest.raises(TypeError) as excinfo:
        next(g)
    assert str(excinfo.value) == "expected at most 1 argument, got 3"


def test_dict_basics():
    d = sanest.dict()
    d['a'] = 1
    assert d['a'] == 1
    d['a'] = 2
    d['b'] = 3
    assert d['a'] == 2
    assert d['b'] == 3


def test_dict_comparison():
    d1 = sanest.dict({'a': 1})
    d2 = sanest.dict({'a': 1})
    d3 = {'a': 1}
    d4 = sanest.dict({'b': 2})
    assert d1 == d2
    assert d1 == d3
    assert d1 == d1
    assert d4 != d1
    assert d4 != d3
    assert d1 != object()


def test_dict_constructor():
    regular_dict = {'a': 1, 'b': 2}
    d = sanest.dict(regular_dict)
    assert d == regular_dict
    d = sanest.dict(regular_dict, c=3)
    regular_dict['c'] = 3
    assert d == regular_dict


def test_dict_length_and_truthiness():
    d = sanest.dict()
    assert len(d) == 0
    assert not d
    assert not bool(d)
    d['a'] = 'aaa'
    assert len(d) == 1
    assert d
    assert bool(d)
    d['a'] = 'abc'
    assert len(d) == 1
    assert d
    d['b'] = 'bbb'
    assert len(d) == 2
    assert d


def test_dict_clear():
    d = sanest.dict()
    d['a'] = 1
    assert len(d) == 1
    d.clear()
    assert 'a' not in d
    assert len(d) == 0
    assert not d


@pytest.mark.parametrize('key', [
    123.456,
    None,
    b"foo",
    True,
    [],
])
def test_dict_string_keys_only(key):
    d = sanest.dict()
    with pytest.raises(sanest.InvalidPathError):
        d[key]
    with pytest.raises(sanest.InvalidPathError):
        d.get(key)
    with pytest.raises(sanest.InvalidPathError):
        key in d
    with pytest.raises(sanest.InvalidPathError):
        d[key] = key
    with pytest.raises(sanest.InvalidPathError):
        del d[key]
    with pytest.raises(sanest.InvalidPathError):
        d.pop(key)


def test_dict_getitem():
    d = sanest.dict()

    d['a'] = 1
    assert d['a'] == 1

    with pytest.raises(KeyError) as excinfo:
        d['x']
    assert str(excinfo.value) == "['x']"


def test_dict_getitem_with_type():
    d = sanest.dict()
    d['a'] = 'aaa'
    d['b'] = 2

    assert d['a':str] == 'aaa'
    assert d['b':int] == 2

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a':int]
    assert str(excinfo.value) == "expected int, got str at path ['a']: 'aaa'"

    with pytest.raises(KeyError) as excinfo:
        d['c':int]
    assert str(excinfo.value) == "['c']"


def test_dict_get():
    d = sanest.dict()
    d['a'] = 'aaa'
    assert d.get('a') == 'aaa'
    assert d.get('b') is None
    assert d.get('c', 'x') == 'x'


def test_dict_get_with_type():
    d = sanest.dict()
    d['a'] = 'aaa'

    assert d.get('a', type=str) == 'aaa'
    assert d.get('c', type=str) is None

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.get('a', type=int)
    assert str(excinfo.value) == "expected int, got str at path ['a']: 'aaa'"


def test_dict_get_with_default_and_type():
    d = sanest.dict()
    value = 123
    d['a'] = value
    assert d.get('a', type=int) is value

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        # here the default is identical to the actual value. type
        # checking should prevent a non-string return value.
        d.get('a', value, type=str)
    assert str(excinfo.value) == "expected str, got int at path ['a']: 123"


def test_dict_get_default_arg_is_not_type_checked():
    d = sanest.dict()
    assert d.get('b', type=int) is None
    assert d.get('b', 234, type=int) == 234
    assert d.get('b', 'not an int', type=int) == 'not an int'


def test_dict_typed_getitem_with_invalid_slice():
    d = sanest.dict()
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d['a':int:str]
    assert str(excinfo.value).startswith(
        "step value not allowed for slice syntax: ")


def test_dict_getitem_with_path():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['aa'] = 123
    d['b'] = 456
    assert d['a', 'aa'] == 123
    path = ['a', 'aa']
    assert d[path] == 123

    with pytest.raises(KeyError) as excinfo:
        d['a', 'x']  # a exists, but x does not
    assert str(excinfo.value) == "['a', 'x']"

    with pytest.raises(KeyError) as excinfo:
        d['x', 'y', 'z']  # x does not exist
    assert str(excinfo.value) == "['x']"

    with pytest.raises(KeyError) as excinfo:
        path = ['x']
        d[path]
    assert str(excinfo.value) == "['x']"

    with pytest.raises(KeyError) as excinfo:
        path = ['x', 'y', 'z']
        d[path]
    assert str(excinfo.value) == "['x']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d['a', 123, True]
    assert str(excinfo.value) == (
        "path must contain only str or int: ['a', 123, True]")

    with pytest.raises(sanest.InvalidStructureError) as excinfo:
        d['b', 'c', 'd']
    assert str(excinfo.value) == (
        "expected dict, got int at subpath ['b'] of ['b', 'c', 'd']")


def test_dict_getitem_with_path_and_type():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d['a', 'b':int] == 123
    path = ['a', 'b']
    assert d[path:int] == 123
    assert d['a':dict]
    path = ['a']
    assert d[path:dict]

    with pytest.raises(KeyError) as excinfo:
        d['x', 'y']
    assert str(excinfo.value) == "['x']"


def test_dict_contains():
    d = sanest.dict()
    d['a'] = 1
    assert 'a' in d
    assert 'b' not in d


def test_dict_contains_with_type():
    d = sanest.dict()
    d['a'] = 123
    d['b'] = [1, 2, 3]
    assert ['a', int] in d
    assert ['a', str] not in d
    assert ['b', [int]] in d
    assert not ['b', [str]] in d


def test_dict_contains_with_path():
    d = sanest.dict()
    d['a', 'b'] = 123
    assert ('a', 'b') in d  # tuple
    assert ['a', 'b'] in d  # list
    assert ['c', 'd'] not in d
    with pytest.raises(sanest.InvalidPathError):
        ['a', None] in d


def test_dict_contains_with_path_and_type():
    d = sanest.dict()
    d['a', 'b'] = 123
    assert ['a', 'b', int] in d
    assert ('a', 'b', int) in d
    assert ('a', 'b', str) not in d
    assert ('a', 'b', 'c') not in d
    assert ('a', 'b', 'c', int) not in d


def test_dict_slice_syntax_limited_use():
    """
    Slice syntax is only valid for d[a,b:int], not in other places.
    """
    d = sanest.dict()
    x = ['a', slice('b', int)]  # this is what d['a', 'b':int)] results in
    with pytest.raises(sanest.InvalidPathError):
        d.get(x)
    with pytest.raises(sanest.InvalidPathError):
        x in d
    with pytest.raises(sanest.InvalidPathError):
        d.setdefault(x, 123)


def test_dict_get_with_path():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d.get(('a', 'b')) == 123
    assert d.get(['a', 'c']) is None
    assert d.get(['b', 'c'], 456) == 456


def test_dict_iteration():
    d = sanest.dict()
    assert list(iter(d)) == []
    d['a'] = 1
    assert list(iter(d)) == ['a']


def test_dict_setitem():
    d = sanest.dict()
    d['a'] = 'b'
    assert d['a'] == 'b'


def test_dict_setitem_with_type():
    d = sanest.dict()
    d['a':int] = 123
    assert d['a'] == 123


def test_dict_setitem_with_path():
    d = sanest.dict()
    d['a', 'b'] = 123
    assert d['a', 'b'] == 123
    path = ['a', 'b']
    d[path] = 456
    assert d[path] == 456


def test_dict_setitem_with_path_and_type():
    d = sanest.dict()
    d['a', 'b':int] = 123
    assert d == {'a': {'b': 123}}
    assert d['a', 'b':int] == 123
    path = ['a', 'b', 'c']
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d[path:int] = 'not an int'
    assert str(excinfo.value) == (
        "expected int, got str: 'not an int'")
    path = ['']


def test_dict_empty_path():
    d = sanest.dict()

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = []
        d[path]
    assert str(excinfo.value) == "empty path: []"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = []
        d[path:str]
    assert str(excinfo.value) == "empty path: []"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.get([], type=str)
    assert str(excinfo.value) == "empty path: []"


def test_dict_setdefault():
    d = sanest.dict()
    d['a'] = 1
    assert d.setdefault('a', 2) == 1
    assert d.setdefault(['b', 'c'], 'foo', type=str) == 'foo'
    assert d['a'] == 1
    assert d['b', 'c'] == 'foo'
    d.setdefault('d')
    assert d['d'] is None
    d.setdefault('e', None)
    assert d['e'] is None

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault(['b', 'c'], 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str at path ['b', 'c']: 'foo'")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault('x', 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str: 'not an int'")
    assert 'x' not in d

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault('a', 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str: 'not an int'")

    d2 = d.setdefault('xy', {'x': 'y'})
    assert isinstance(d2, sanest.dict)
    assert d2 == {'x': 'y'}


def test_dict_update():
    d = sanest.dict()
    d['a'] = 1
    d.update({'a': 2}, b=3)
    assert d == {'a': 2, 'b': 3}


def test_dict_value_atomic_type():
    d1 = sanest.dict()
    d2 = {}
    for d in [d1, d2]:
        d['a'] = 1
        d['b'] = 1.23
        d['c'] = "foo"
        d['d'] = True
    assert d1 == d2


def test_dict_value_container_type():
    d = sanest.dict()
    nested = {'b': 123, 'c': {'c1': True, 'c2': False}}
    d['a'] = nested
    assert isinstance(d.get('a'), sanest.dict)
    assert isinstance(d['a'], sanest.dict)
    assert d['a'] == nested
    assert d['a']['b':int] == 123
    d2 = d['a', 'c':dict]
    assert isinstance(d2, sanest.dict)
    assert d2['c1':bool] is True


def test_dict_delitem():
    d = sanest.dict()
    with pytest.raises(KeyError) as excinfo:
        del d['a']
    assert str(excinfo.value) == "['a']"
    d['a'] = 3
    assert 'a' in d
    del d['a']
    assert 'a' not in d
    with pytest.raises(KeyError) as excinfo:
        del d['a']
    assert str(excinfo.value) == "['a']"


def test_dict_delitem_with_type():
    d = sanest.dict({'a': 1, 'b': 2})
    del d['a':int]
    assert 'a' not in d
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        del d['b':str]
    assert str(excinfo.value) == "expected str, got int at path ['b']: 2"
    assert d['b'] == 2


def test_dict_delitem_with_path():
    d = sanest.dict({'a': {'b': 2}})
    with pytest.raises(KeyError) as excinfo:
        del d['a', 'x']
    assert str(excinfo.value) == "['a', 'x']"
    del d['a', 'b']
    assert d['a'] == {}


def test_dict_delitem_with_path_and_type():
    original = {'a': {'b': 2}}
    d = sanest.dict(original)
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        del d['a', 'b':str]
    assert str(excinfo.value) == "expected str, got int at path ['a', 'b']: 2"
    assert d == original
    del d['a', 'b':int]
    assert d['a'] == {}


def test_dict_pop():
    d = sanest.dict({'a': 1, 'b': 2})

    # existing key
    assert d.pop('a') == 1
    assert 'a' not in d

    # missing key
    with pytest.raises(KeyError) as excinfo:
        d.pop('a')
    assert str(excinfo.value) == "['a']"

    # existing key, with default arg
    assert d.pop('b', 22) == 2
    assert not d

    # missing key, with default arg
    assert d.pop('b', 22) == 22


def test_dict_pop_with_type():
    d = sanest.dict({'a': 1, 'b': 2})

    # existing key, correct type
    assert d.pop('a', type=int) == 1

    # existing key, wrong type
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.pop('b', type=str)
    assert str(excinfo.value) == "expected str, got int at path ['b']: 2"
    assert d['b'] == 2

    # existing key, with default arg, wrong type
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert d.pop('b', 22, type=str)
    assert str(excinfo.value) == "expected str, got int at path ['b']: 2"
    assert d['b'] == 2

    # existing key, with default arg, correct type
    assert d.pop('b', 22, type=int) == 2

    # missing key
    with pytest.raises(KeyError) as excinfo:
        d.pop('x', type=str)
    assert str(excinfo.value) == "['x']"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__

    # missing key, with default arg: not type checked, just like .get()
    assert d.pop('x', 99, type=int) == 99
    assert d.pop('x', 'not an int', type=int) == 'not an int'

    assert not d


def test_dict_pop_default_arg_not_wrapped():
    default = {'a': 1}
    d = sanest.dict().pop('foo', default)
    assert d is default


def test_dict_pop_with_path():
    d = sanest.dict({
        'a': {
            'b': 2,
            'c': 3,
        },
        'd': {
            'e': {
                'f': {
                    'g': 'hello',
                },
            },
        }})
    assert d.pop(['a', 'b']) == 2
    assert ['a', 'b'] not in d
    assert d.pop(['a', 'c'], 33) == 3
    assert ['a', 'c'] not in d
    assert d['a'] == {}
    assert d.pop(['a', 'x'], 99, type=str) == 99
    with pytest.raises(KeyError) as excinfo:
        d.pop(['a', 'x'])
    assert str(excinfo.value) == "['a', 'x']"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__
    with pytest.raises(KeyError) as excinfo:
        d.pop(['d', 'e', 'x', 'y', 'z'])
    assert str(excinfo.value) == "['d', 'e', 'x']"
    assert d.pop(['d', 'e', 'x', 'y', 'z'], 'hi') == 'hi'
    d.pop(['d', 'e', 'f']) == {'g': 'hello'}


def test_dict_methods_with_path_pointing_to_list_item():
    """
    dict specific methods that take a path to work on a nested structure
    should enforce that the path actually leads to a nested dict, and
    not to a list.
    """
    d = sanest.dict({'a': [{}, {}]})
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.get(['a', 0])
    assert str(excinfo.value) == "path must lead to dict key"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.pop(['a', 0])
    assert str(excinfo.value) == "path must lead to dict key"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.setdefault(['a', 0], 'x')
    assert str(excinfo.value) == "path must lead to dict key"


def test_dict_pop_with_path_and_type():
    d = sanest.dict({'a': {'b': 2}})
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert d.pop(['a', 'b'], type=str)
    assert str(excinfo.value) == "expected str, got int at path ['a', 'b']: 2"
    assert d.pop(['a', 'b'], 22, type=int) == 2
    assert d == {'a': {}}
    assert d.pop(['a', 'x'], 99, type=str) == 99


def test_dict_popitem():
    d = sanest.dict({'a': 1})
    assert d.popitem() == ('a', 1)
    assert d == {}
    d['b'] = 2
    assert d.popitem() == ('b', 2)
    with pytest.raises(KeyError) as excinfo:
        assert d.popitem()
    assert str(excinfo.value) == "dictionary is empty"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


def test_dict_popitem_with_type():
    d = sanest.dict({'a': 1})
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert d.popitem(type=str)
    assert str(excinfo.value) == "expected str, got int at path ['a']: 1"
    assert d['a'] == 1
    assert d.popitem(type=int) == ('a', 1)
    with pytest.raises(KeyError) as excinfo:
        assert d.popitem(type=str)
    assert str(excinfo.value) == "dictionary is empty"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


def test_dict_convert_to_regular_dict():
    original = {'a': {'b': 123}, "c": True}
    d = sanest.dict(original)
    as_dict = d.unwrap()
    assert type(as_dict) is dict
    assert as_dict == original


def test_dict_repr():
    d = sanest.dict({'a': {'b': {'c': 123}}})
    assert repr(d) == "sanest.dict({'a': {'b': {'c': 123}}})"
    assert eval(repr(d)) == d


def test_dict_shallow_copy():
    d1 = sanest.dict({'a': 1, 'b': {'b1': 21, 'b2': 22}})
    d2 = sanest.dict({'a': 1, 'b': {'b1': 21, 'b2': 22}})
    copies = [
        (d1, d1.copy()),
        (d2, copy.copy(d2)),
    ]
    for original, other in copies:
        assert other == original
        assert other is not original
        # change shallow field: original is unchanged
        other['a'] = 111
        assert original['a'] == 1
        # change nested field: copy reflects the change
        original['b', 'b2'] = 2222
        assert other['b', 'b2'] == 2222


def test_dict_deep_copy():
    d1 = sanest.dict({'a': 1, 'b': {'b1': 21, 'b2': 22}})
    d2 = sanest.dict({'a': 1, 'b': {'b1': 21, 'b2': 22}})
    copies = [
        (d1, d1.copy(deep=True)),
        (d2, copy.deepcopy(d2)),
    ]
    for original, other in copies:
        assert other == original
        assert other is not original
        # change shallow field: original is unchanged
        other['a'] = 111
        assert original['a'] == 1
        # change nested field: copy is unchanged change
        original['b', 'b2'] = 2222
        assert other['b', 'b2'] == 22


def test_dict_pickle():
    d1 = sanest.dict({'a': 1, 'b': {'b1': 21, 'b2': 22}})
    s = pickle.dumps(d1)
    d2 = pickle.loads(s)
    assert d1 == d2
    assert d2['b', 'b1'] == 21


def test_dict_fromkeys():
    keys = ['a', 'b']
    d = sanest.dict.fromkeys(keys)
    assert d == {'a': None, 'b': None}
    d = sanest.dict.fromkeys(keys, 123)
    assert d == {'a': 123, 'b': 123}


def test_dict_wrap():
    original = {'a': {'b': 12}}
    d = sanest.dict.wrap(original)
    assert d['a', 'b'] == 12
    assert d.unwrap() is original
    assert sanest.dict.wrap(original) == sanest.dict.wrap(original)


def test_dict_wrap_invalid():
    with pytest.raises(TypeError) as excinfo:
        sanest.dict.wrap(123)
    assert str(excinfo.value) == "not a dict"


def test_dict_wrap_twice():
    original = {'a': {'b': 12}}
    d = sanest.dict.wrap(original)
    d2 = sanest.dict.wrap(d)
    assert d is d2


def test_dict_constructor_validation():
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        sanest.dict({True: False})
    assert str(excinfo.value) == "invalid dict key: True"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        sanest.dict({123: 123})
    assert str(excinfo.value) == "invalid dict key: 123"
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        sanest.dict({'a': MyClass()})
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_dict_validate_assigned_values():
    d = sanest.dict()
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a'] = MyClass()
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"

    d = sanest.dict()
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a', 'b'] = MyClass()
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_dict_wrap_validation():
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        sanest.dict.wrap({123: True})
    assert str(excinfo.value) == (
        "invalid dict key: 123")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        sanest.dict.wrap({"foo": MyClass()})
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_dict_wrap_skip_validation():
    invalid_dict = {True: False}
    wrapped = sanest.dict.wrap(invalid_dict, check=False)
    unwrapped = wrapped.unwrap()
    assert unwrapped is invalid_dict


def test_dict_validate():
    d = sanest.dict({'a': 1, 'b': 2})
    d.check_types(type=int)
    d = sanest.dict({'a': [1, 2]})
    d.check_types(type=[int])
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.check_types(type=str)
    assert str(excinfo.value) == "expected str, got list at path ['a']: [1, 2]"


def test_dict_view_repr():
    d = sanest.dict({'a': 123})
    assert repr(d.keys()) == "sanest.dict({'a': 123}).keys()"
    assert repr(d.items()) == "sanest.dict({'a': 123}).items()"
    assert repr(d.values()) == "sanest.dict({'a': 123}).values()"


def test_dict_keys_view():
    d = sanest.dict({'a': {'b': 123}})
    keys_view = d.keys()
    assert len(keys_view) == len(d) == 1
    assert 'a' in keys_view
    assert ['a'] in keys_view
    assert ['a', dict] in keys_view
    assert ['a', 'b'] in keys_view
    assert ['a', 'b', int] in keys_view
    assert ['a', 'x'] not in keys_view
    assert keys_view & {'a', 'q'} == {'a'}
    assert list(iter(keys_view)) == ['a']


def test_dict_values_view_contains():
    d = sanest.dict({'a': 1, 'b': 2, 'c': [3, 4, 5]})
    values_view = d.values()
    assert len(values_view) == len(d) == 3
    assert 1 in values_view
    assert [3, 4, 5] in values_view
    assert sanest.list([3, 4, 5]) in values_view
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        MyClass() in values_view
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_dict_values_view_iteration():
    d = sanest.dict({'a': 'b'})
    assert list(d.values()) == ['b']
    d = sanest.dict({'a': [1, 2]})
    values_view = d.values(type=[int])
    values = list(values_view)
    assert len(values) == 1
    value = values[0]
    assert value == [1, 2]
    assert isinstance(value, sanest.list)
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.values(type=bool)
    assert str(excinfo.value) == (
        "expected bool, got list at path ['a']: [1, 2]")


def test_dict_items_view_contains():
    d = sanest.dict({'a': {'b': 2}})
    items_view = d.items()
    key = 'a'
    value = {'b': 2}
    assert (key, value) in items_view
    key = 'a'
    value = sanest.dict({'b': 2})
    assert (key, value) in items_view
    key = ['a', 'b']
    value = 2
    assert (key, value) in items_view
    key = ['a', 'x']
    value = 123
    assert not (key, value) in items_view


def test_dict_items_view_iteration():
    d = sanest.dict({'a': 1})
    assert list(d.items()) == [('a', 1)]
    d = sanest.dict({'a': {'b': 2}})
    items_view = d.items(type={str: int})
    assert list(items_view) == [('a', {'b': 2})]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.values(type=bool)
    assert str(excinfo.value) == (
        "expected bool, got dict at path ['a']: {'b': 2}")


#
# lists
#

def test_list_basics():
    d = sanest.list()
    d.append('a')
    assert d[0] == 'a'
    d.append('b')
    d.append('c')
    assert d[1] == 'b'
    assert d[2] == 'c'


def test_list_constructor():
    regular_list = ['a', 'b']
    ll = sanest.list(regular_list)
    assert len(ll) == 2
    with pytest.raises(TypeError) as excinfo:
        sanest.list([1, 2, 3], [4, 5], [6, 7])
    assert str(excinfo.value) == "expected at most 1 argument, got 3"


def test_list_comparison_equality():
    l1 = sanest.list([1, 2])
    l2 = sanest.list([1, 2])
    normal_list = [1, 2]
    assert l1 == normal_list
    assert l1 == l1
    assert l1 == l2
    assert l1 != [2, 1]
    assert l1 != [3]
    assert l1 != object()


def test_list_comparison_ordering():
    l1 = sanest.list([1, 2])
    l2 = sanest.list([2, 3, 4])
    normal_list = [1, 2]
    assert l1 < l2
    assert l1 <= l2
    assert l2 > l1
    assert l2 >= l1
    assert not l1 < normal_list
    assert not l1 > normal_list
    assert l1 <= normal_list
    assert l1 >= normal_list
    assert l2 > normal_list
    assert normal_list < l2
    if sys.version_info >= (3, 6):
        pattern = r" not supported between instances "
    else:
        pattern = r"^unorderable types: "
    with pytest.raises(TypeError) as excinfo:
        l1 < object()
    assert excinfo.match(pattern)
    with pytest.raises(TypeError) as excinfo:
        l1 <= object()
    assert excinfo.match(pattern)
    with pytest.raises(TypeError) as excinfo:
        l1 > object()
    assert excinfo.match(pattern)
    with pytest.raises(TypeError) as excinfo:
        l1 >= object()
    assert excinfo.match(pattern)


def test_list_repr():
    ll = sanest.list([1, 2, [3, 4]])
    assert repr(ll) == "sanest.list([1, 2, [3, 4]])"
    assert eval(repr(ll)) == ll


def test_list_pickle():
    l1 = sanest.list([1, 2, 3])
    s = pickle.dumps(l1)
    l2 = pickle.loads(s)
    assert l1 == l2


def test_list_wrap():
    original = ['a', 'b', ['c1', 'c2'], None]
    ll = sanest.list.wrap(original)
    assert ll[2, 0] == 'c1'
    assert ll.unwrap() is original
    assert sanest.list.wrap(original) == sanest.list.wrap(original)


def test_list_wrap_invalid():
    with pytest.raises(TypeError) as excinfo:
        sanest.list.wrap(123)
    assert str(excinfo.value) == "not a list"


def test_list_wrap_twice():
    original = [1, 2, 3]
    l1 = sanest.list.wrap(original)
    l2 = sanest.list.wrap(l1)
    assert l1 is l2


def test_list_wrap_validation():
    original = [MyClass(), MyClass()]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        sanest.list.wrap(original)
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"
    ll = sanest.list.wrap(original, check=False)
    assert len(ll) == 2


def test_list_validate():
    ll = sanest.list([1, 2, 3])
    ll.check_types(type=int)
    ll = sanest.list([{'a': 1}, {'a': 2}, {'a': 3}])
    ll.check_types(type={str: int})
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.check_types(type=str)
    assert str(excinfo.value) == "expected str, got dict at path [0]: {'a': 1}"


def test_list_getitem():
    ll = sanest.list(['a', 'b'])
    assert ll[0] == 'a'
    assert ll[1] == 'b'
    with pytest.raises(IndexError) as excinfo:
        ll[2]
    assert str(excinfo.value) == "[2]"


def test_list_getitem_with_type():
    ll = sanest.list(['a', {}])
    assert ll[0:str] == 'a'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert ll[0:bool] == 'a'
    assert str(excinfo.value) == "expected bool, got str at path [0]: 'a'"
    assert isinstance(ll[1], sanest.dict)


def test_list_getitem_with_path():
    ll = sanest.list(['a', ['b1', 'b2']])
    assert ll[1, 0] == 'b1'
    path = (1, 0)
    assert ll[path] == 'b1'
    path = [1, 0]
    assert ll[path] == 'b1'
    with pytest.raises(IndexError) as excinfo:
        ll[1, 2, 3, 4]
    assert str(excinfo.value) == "[1, 2]"
    with pytest.raises(sanest.InvalidStructureError) as excinfo:
        ll[0, 9]
    assert str(excinfo.value) == (
        "expected list, got str at subpath [0] of [0, 9]")


def test_list_getitem_with_path_and_type():
    ll = sanest.list(['a', ['b1', 'b2']])
    assert ll[1, 0:str] == "b1"
    path = [1, 0]
    assert ll[path:str] == "b1"
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll[1, 1:bool]
    assert str(excinfo.value) == "expected bool, got str at path [1, 1]: 'b2'"


def test_list_setitem():
    ll = sanest.list(['a', 'b'])
    ll[0] = 'b'
    ll[1] = sanest.list()
    assert ll == ['b', []]
    with pytest.raises(IndexError) as excinfo:
        ll[5] = 'a'
    assert str(excinfo.value) == "[5]"
    assert ll == ['b', []]


def test_list_setitem_with_type():
    ll = sanest.list(['a'])
    assert ll[0:str] == 'a'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll[0:bool] = 'a'
    assert str(excinfo.value) == "expected bool, got str: 'a'"


def test_list_setitem_with_path():
    ll = sanest.list(['a', ['b', 'c', 'd']])
    ll[1, 0] = 'e'
    path = (1, 1)
    ll[path] = 'f'
    path = [1, 2]
    ll[path] = 'g'
    assert ll == ['a', ['e', 'f', 'g']]
    with pytest.raises(IndexError) as excinfo:
        ll[5, 4, 3] = 'h'
    assert str(excinfo.value) == "[5]"
    assert ll == ['a', ['e', 'f', 'g']]


def test_list_setitem_with_path_and_type():
    ll = sanest.list(['a', ['b', 'c']])
    ll[1, 0:str] = "d"
    path = [1, 1]
    ll[path:str] = "e"
    assert ll == ['a', ['d', 'e']]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll[1, 1:bool] = 'x'
    assert str(excinfo.value) == "expected bool, got str: 'x'"
    assert ll == ['a', ['d', 'e']]


def test_list_contains():
    ll = sanest.list([
        1,
        'a',
        [2, 3],
        {'c': 'd'},
        None,
    ])
    assert 1 in ll
    assert 'a' in ll
    assert [2, 3] in ll
    assert sanest.list([2, 3]) in ll
    assert {'c': 'd'} in ll
    assert sanest.dict({'c': 'd'}) in ll
    assert None in ll
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        MyClass() in ll
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_list_contains_with_type():
    ll = sanest.list([1, 'a', {'c': 'd'}])
    assert ll.contains(1, type=int)
    assert ll.contains('a', type=str)
    assert ll.contains({'c': 'd'}, type=dict)
    assert not ll.contains(1, type=str)
    assert not ll.contains(2, type=str)
    assert not ll.contains({'x': 'y'}, type=dict)
    assert not ll.contains({'x': 'y'}, type=int)


def test_list_iteration():
    ll = sanest.list([
        {'a': 1},
        [2, 3],
        'x',
    ])
    first, second, third = ll
    assert isinstance(first, sanest.dict)
    assert first == {'a': 1}
    assert isinstance(second, sanest.list)
    assert second == [2, 3]
    assert third == 'x'


def test_list_iteration_with_type():
    ll = sanest.list(['a', 'a'])
    assert list(ll.iter()) == ['a', 'a']
    assert list(ll.iter(type=str)) == ['a', 'a']
    ll = sanest.list([1, 2, 'oops'])
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.iter(type=int)  # eager validation, not during yielding
    assert str(excinfo.value) == "expected int, got str at path [2]: 'oops'"
    ll = sanest.list([{}])
    assert isinstance(next(ll.iter(type=dict)), sanest.dict)


def test_list_index():
    ll = sanest.list([
        'a',         # 0
        {'b': 'c'},  # 1
        None,        # 2
        None,        # 3
        'a',         # 4
        None,        # 5
        None,        # 6
    ])
    assert ll.index('a') == 0
    assert ll.index('a', type=str) == 0
    assert ll.index('a', 2) == 4
    assert ll.index('a', 2, type=str) == 4
    assert ll.index('a', 2, 6) == 4
    assert ll.index(None, 2) == 2
    assert ll.index(None, 4) == 5
    assert ll.index({'b': 'c'}) == 1
    assert ll.index(sanest.dict({'b': 'c'})) == 1
    with pytest.raises(ValueError) as excinfo:
        ll.index('a', 5)
    assert str(excinfo.value) == "'a' is not in list"
    with pytest.raises(ValueError) as excinfo:
        ll.index('a', 2, 3)
    assert str(excinfo.value) == "'a' is not in list"
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.index(2, type=str)
    assert str(excinfo.value) == "expected str, got int: 2"


def test_list_count():
    ll = sanest.list([1, 2, 3, 1, 1, 2, 3, {'a': 'b'}])
    assert ll.count(1) == 3
    assert ll.count(1, type=int) == 3
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.count(1, type=str)
    assert str(excinfo.value) == "expected str, got int: 1"
    assert ll.count({'a': 'b'}) == 1
    assert ll.count(sanest.dict({'a': 'b'})) == 1


def test_list_insert():
    ll = sanest.list(range(5))
    assert ll == [0, 1, 2, 3, 4]
    ll.insert(0, 'a')
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.insert(0, 'a', type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert ll == ['a', 0, 1, 2, 3, 4]
    ll.insert(2, 'b')
    assert ll == ['a', 0, 'b', 1, 2, 3, 4]
    ll.insert(20, 'c')
    assert ll == ['a', 0, 'b', 1, 2, 3, 4, 'c']
    ll.insert(-3, 'd')
    assert ll == ['a', 0, 'b', 1, 2, 'd', 3, 4, 'c']


def test_list_append():
    ll = sanest.list()
    ll.append(1)
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.append('a', type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert ll == [1]
    ll.append(2)
    ll.append([3, 4])
    ll.append(sanest.list([5, 6]))
    assert len(ll) == 4
    assert ll == [1, 2, [3, 4], [5, 6]]


def test_list_extend():
    ll = sanest.list([1, 2])
    ll.extend(sanest.list([3, 4]))
    ll.extend([5, 6], type=int)
    assert ll == [1, 2, 3, 4, 5, 6]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.extend(['a', 'b'], type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert ll == [1, 2, 3, 4, 5, 6]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.extend([MyClass()])
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"
    ll.extend(n for n in [7, 8])
    assert ll == [1, 2, 3, 4, 5, 6, 7, 8]


@pytest.mark.parametrize(
    ('value', 'type_name'),
    [
        ('foo', 'str'),
        (b'foo', 'bytes'),
        (bytearray(b'foo'), 'bytearray'),
    ])
def test_list_guard_against_implicit_string_splitting(value, type_name):
    ll = sanest.list()
    expected_message = (
        "expected iterable that is not string-like, got {}"
        .format(type_name))
    with pytest.raises(TypeError) as excinfo:
        ll.extend(value)
    assert str(excinfo.value) == expected_message
    with pytest.raises(TypeError) as excinfo:
        ll += value
    assert str(excinfo.value) == expected_message
    with pytest.raises(TypeError) as excinfo:
        ll[:] = value
    assert str(excinfo.value) == expected_message


def test_list_extend_nested_unwrapping():
    ll = sanest.list([
        [
            [1, 2],
            [3, 4]
        ],
        sanest.list([
            sanest.list([5, 6]),
            sanest.list([7, 8]),
        ]),
    ])
    assert ll == [
        [[1, 2], [3, 4]],
        [[5, 6], [7, 8]],
    ]


def test_list_concat():
    x = sanest.list(['a', 'b'])
    y = sanest.list(['c'])
    z = ['d']
    xy = x + y
    assert xy == ['a', 'b', 'c']
    assert isinstance(xy, sanest.list)
    xz = x + z
    assert xz == ['a', 'b', 'd']
    assert isinstance(xz, sanest.list)
    assert x == ['a', 'b']
    zx = z + x
    assert zx == ['d', 'a', 'b']
    assert isinstance(zx, builtins.list)
    x += z
    assert isinstance(x, sanest.list)
    assert x == xz
    xy += z
    assert isinstance(xy, sanest.list)
    assert xy == ['a', 'b', 'c', 'd']


def test_list_concat_only_accepts_lists():
    ll = sanest.list()
    with pytest.raises(TypeError) as excinfo:
        ll + 'abc'
    assert str(excinfo.value) == "expected list, got str"


def test_list_repeat():
    ll = sanest.list([1, 2])
    assert ll * 2 == [1, 2, 1, 2]
    assert 2 * ll == [1, 2, 1, 2]
    assert ll == [1, 2]
    assert isinstance(ll, sanest.list)
    ll *= 2
    assert ll == [1, 2, 1, 2]
    assert isinstance(ll, sanest.list)


def test_list_reversing():
    ll = sanest.list(['a', {}])
    rev = reversed(ll)
    first, second = rev
    assert first == {}
    assert isinstance(first, sanest.dict)
    assert second == 'a'
    assert ll == ['a', {}]
    ll.reverse()
    assert ll == [{}, 'a']


def test_list_clear():
    ll = sanest.list([1, 2, 3])
    ll.clear()
    assert ll == []


def test_list_delitem():
    ll = sanest.list(['a', 'b', 'c'])
    del ll[1]
    assert ll == ['a', 'c']
    del ll[-1]
    assert ll == ['a']
    del ll[0]
    assert ll == []


def test_list_delitem_with_type():
    ll = sanest.list(['a', 'b', 'c'])
    del ll[0:str]
    assert ll == ['b', 'c']
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        del ll[-1:int]
    assert str(excinfo.value) == "expected int, got str at path [-1]: 'c'"
    assert ll == ['b', 'c']


def test_list_delitem_with_path():
    ll = sanest.list([['a', 'aa'], ['b', 'bb']])
    del ll[0, 1]
    assert ll == [['a'], ['b', 'bb']]
    path = [1, 0]
    del ll[path]
    assert ll == [['a'], ['bb']]


def test_list_delitem_with_path_and_type():
    ll = sanest.list([['a', 'aa'], ['b', 'bb']])
    del ll[0, 0:str]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        del ll[0, 0:int]
    assert str(excinfo.value) == "expected int, got str at path [0, 0]: 'aa'"
    assert ll == [['aa'], ['b', 'bb']]
    path = [1, 1]
    del ll[path:str]
    assert ll == [['aa'], ['b']]


def test_list_pop():
    ll = sanest.list(['a', [], 'b', 'c'])
    assert ll.pop() == 'c'
    assert ll.pop(-1) == 'b'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.pop(0, type=int)
    assert str(excinfo.value) == "expected int, got str at path [0]: 'a'"
    assert ll.pop(0, type=str) == 'a'
    with pytest.raises(IndexError) as excinfo:
        ll.pop(123)
    assert str(excinfo.value) == "[123]"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__
    value = ll.pop(type=list)
    assert isinstance(value, sanest.list)
    assert len(ll) == 0
    with pytest.raises(IndexError) as excinfo:
        ll.pop(0, type=int)
    assert str(excinfo.value) == "pop from empty list"


def test_list_pop_with_path():
    ll = sanest.list([
        {'items': ['a', 'b', 'c']},
    ])
    assert ll.pop([0, 'items', 0]) == 'a'
    assert ll[0, 'items'] == ['b', 'c']
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.pop([0, 'items', 1], type=int)
    assert str(excinfo.value) == (
        "expected int, got str at path [0, 'items', 1]: 'c'")
    assert ll.pop([0, 'items', 1], type=str) == 'c'
    assert ll.pop([0, 'items', 0]) == 'b'
    assert ll[0, 'items'] == []
    with pytest.raises(IndexError) as excinfo:
        ll.pop([0, 'items', 0])
    assert str(excinfo.value) == "pop from empty list"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        ll.pop([0, 'x'])
    assert str(excinfo.value) == "path must lead to list index"


def test_list_remove():
    ll = sanest.list(['a', 'a', 'b', 'a', {}])
    ll.remove('a')
    assert ll == ['a', 'b', 'a', {}]
    with pytest.raises(ValueError) as excinfo:
        ll.remove('c')
    assert str(excinfo.value) == "'c' is not in list"
    ll.remove('a', type=str)
    ll.remove({}, type=dict)
    assert ll == ['b', 'a']
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll.remove('a', type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert ll == ['b', 'a']


def test_list_sort():
    ll = sanest.list(['a', 'c', 'b'])
    ll.sort()
    assert ll == ['a', 'b', 'c']
    ll.sort(reverse=True)
    assert ll == ['c', 'b', 'a']


def test_list_get_slice():
    ll = sanest.list(['a', 'b', 'c'])
    assert ll[0:] == ['a', 'b', 'c']
    assert ll[2:] == ['c']
    assert ll[:0] == []
    assert ll[:-2] == ['a']
    assert ll[0:20] == ['a', 'b', 'c']
    assert ll[:] == ['a', 'b', 'c']
    assert ll[::2] == ['a', 'c']
    assert isinstance(ll[1:2], sanest.list)


def test_list_set_slice():
    ll = sanest.list(['a', 'b', 'c', 'd', 'e'])
    ll[::2] = ['x', 'y', 'z']
    assert ll == ['x', 'b', 'y', 'd', 'z']
    ll[:] = ['p', 'q', 'r']
    assert ll == ['p', 'q', 'r']
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        ll[:3] = [MyClass()]
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"
    assert ll == ['p', 'q', 'r']
    ll[:2] = sanest.list([{}, []])
    assert ll == [{}, [], 'r']
    with pytest.raises(ValueError) as excinfo:
        ll[0::2] = ['this', 'one', 'is', 'too', 'long']
    assert str(excinfo.value) == (
        "attempt to assign sequence of size 5 to extended slice of size 2")


def test_list_del_slice():
    ll = sanest.list(['a', 'b', 'c', 'd', 'e'])
    del ll[:2]
    assert ll == ['c', 'd', 'e']
    del ll[-1:]
    assert ll == ['c', 'd']
    del ll[:]
    assert ll == []


#
# dicts and lists
#


def test_prevent_subclassing():
    with pytest.raises(TypeError) as excinfo:
        class X(sanest.dict):
            pass
    assert str(excinfo.value) == (
        "type 'sanest.dict' is not an acceptable base type")

    with pytest.raises(TypeError) as excinfo:
        class Y(sanest.list):
            pass
    assert str(excinfo.value) == (
        "type 'sanest.list' is not an acceptable base type")


def test_wrap():
    ll = _sanest.list.wrap([1, 2])
    assert isinstance(ll, sanest.list)
    d = _sanest.wrap({'a': 1})
    assert isinstance(d, sanest.dict)
    with pytest.raises(TypeError) as excinfo:
        _sanest.wrap(MyClass())
    assert str(excinfo.value) == "not a dict or list: <MyClass>"


def test_dict_list_mixed_nested_lookup():
    d = sanest.dict({
        'a': [
            {'b': [1]},
            {'b': [2]},
        ],
    })
    assert d['a', 0] == {'b': [1]}
    assert d['a', 0, 'b'] == [1]
    assert d['a', 1, 'b', 0] == 2


def test_dict_list_contains():
    d = sanest.dict({
        'a': ['b', 'c'],
    })
    assert ['a'] in d
    assert ['a', 0] in d
    assert ['a', 0, 'x'] not in d
    assert ['a', 'x'] not in d
    assert ['a', 3] not in d


def test_wrong_path_for_container_type():
    d = sanest.dict()
    ll = sanest.list()
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d[2, 'a']
    assert str(excinfo.value) == "dict path must start with str: [2, 'a']"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        ll['a', 2]
    assert str(excinfo.value) == "list path must start with int: ['a', 2]"


def test_read_only():
    d = sanest.dict.wrap({'a': ['b1', 'b2']})
    rd = d.read_only()
    with pytest.raises(TypeError) as excinfo:
        rd['c'] = 'd'
    assert str(excinfo.value).endswith("does not support item assignment")
    with pytest.raises(TypeError) as excinfo:
        del rd['a']
    assert str(excinfo.value).endswith("does not support item deletion")
    for method in {'setdefault', 'update', 'pop', 'popitem', 'clear'}:
        assert not hasattr(rd, method)


def test_read_only_identity():
    d = sanest.dict.wrap({'a': ['b1', 'b2']})
    rd = d.read_only()
    assert d.unwrap() is rd.unwrap()
    assert rd.read_only() is rd
    assert rd.ro() is rd


def test_read_only_copy_becomes_read_write():
    d = sanest.dict()
    rd = d.ro()
    d_copy = rd.copy()
    d_copy['a'] = 1
    assert d_copy['a'] == 1


def test_read_only_copy_is_not_shallow():
    d = sanest.dict.wrap({'a': {'b': {'c': 'd'}}})
    rd = d.ro()
    d_copy = rd.copy()
    d['a', 'b'].clear()
    assert len(rd['a', 'b']) == 0
    assert d_copy['a', 'b'] == {'c': 'd'}


def test_read_only_to_read_write():
    orig = {'a': 'b'}
    d = sanest.dict.wrap(orig)
    rd = d.ro()
    rw = rd.rw()
    rw['a'] = 'c'
    assert rw.unwrap() is orig
    rw.rw().unwrap() is orig


def test_read_only_assignment_to_read_write_container():
    d = sanest.dict()
    rd = sanest.dict({'b': 1}).ro()
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a'] = rd
    assert str(excinfo.value) == (
        "cannot assign a read-only container to a mutable container")
    d['a'] = rd.rw()
    assert d['a', 'b'] == 1


#
# misc
#

def test_missing_arg_repr():
    assert repr(_sanest.MISSING) == '<missing>'
    assert str(_sanest.MISSING) == '<missing>'


def test_slots():
    d = sanest.dict()
    with pytest.raises(AttributeError):
        d.foo = 123
    ll = sanest.list()
    with pytest.raises(AttributeError):
        ll.foo = 123


def dedent(s):
    s = s.lstrip('\n')
    s = textwrap.dedent(s).rstrip()
    return s


PRETTY_PRINT_SAMPLES = [
    (
        sanest.dict(a='a' * 30, b='b' * 30),
        dedent("""\
            sanest.dict({'a': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                         'b': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'})
        """)),
    (
        sanest.list(['a' * 30, 'b' * 30]),
        dedent("""\
            sanest.list(['aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                         'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'])
        """)),
]


@pytest.mark.skipif(
    sys.version_info < (3, 5),
    reason="requires python 3.5+ pprint module")
@pytest.mark.parametrize(('input', 'expected'), PRETTY_PRINT_SAMPLES)
def test_pretty_printing_pprint(input, expected):
    actual = pprint.pformat(input)
    assert actual == expected


@pytest.mark.parametrize(('input', 'expected'), PRETTY_PRINT_SAMPLES)
def test_pretty_printing_ipython(input, expected):
    actual = IPython.lib.pretty.pretty(input)
    assert actual == expected
