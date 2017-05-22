"""
tests for sanest
"""

import copy

import pytest

import sanest


def test_dict_basics():
    d = sanest.Dict()
    d['a'] = 1
    assert d['a'] == 1
    d['a'] = 2
    d['b'] = 3
    assert d['a'] == 2
    assert d['b'] == 3


def test_dict_length_and_truthiness():
    d = sanest.Dict()
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


def test_dict_contains():
    d = sanest.Dict()
    d['a'] = 1
    assert 'a' in d
    assert 'b' not in d


def test_dict_setdefault():
    d = sanest.Dict()
    d['a'] = 1
    d.setdefault('a', 2)
    d.setdefault('b', 3)
    assert d['a'] == 1
    assert d['b'] == 3


def test_dict_clear():
    d = sanest.Dict()
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
    d = sanest.Dict()
    with pytest.raises(sanest.InvalidKeyError):
        d[key]
    with pytest.raises(sanest.InvalidKeyError):
        d.get(key)
    with pytest.raises(sanest.InvalidKeyError):
        key in d
    with pytest.raises(sanest.InvalidKeyError):
        d[key] = key
    with pytest.raises(sanest.InvalidKeyError):
        del d[key]
    with pytest.raises(sanest.InvalidKeyError):
        d.pop(key)


def test_dict_getitem_with_type():
    d = sanest.Dict()
    d['a'] = 'aaa'
    d['b'] = 2

    assert d['a':str] == 'aaa'
    assert d['b':int] == 2

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a':int]
    assert str(excinfo.value) == "requested int, got str at path ['a']: 'aaa'"


def test_dict_get_with_type():
    d = sanest.Dict()
    d['a'] = 'aaa'

    assert d.get('a', type=str) == 'aaa'
    assert d.get('c', type=str) is None

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.get('a', type=int)
    assert str(excinfo.value) == "requested int, got str at path ['a']: 'aaa'"


def test_dict_get_with_default_and_type():
    d = sanest.Dict()
    value = 123
    d['a'] = value
    assert d.get('a', type=int) is value

    # the 'default' argument is not type checked
    assert d.get('b', type=int) is None
    assert d.get('b', 234, type=int) == 234
    assert d.get('b', 'not an int', type=int) == 'not an int'

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        # here the default is identical to the actual value. type
        # checking should prevent a non-string return value.
        d.get('a', value, type=str)
    assert str(excinfo.value) == "requested str, got int at path ['a']: 123"


def test_dict_getitem_with_invalid_type():
    d = sanest.Dict()
    with pytest.raises(sanest.InvalidValueTypeError) as excinfo:
        d['nonexistent':bytes]
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


def test_dict_get_with_invalid_type():
    d = sanest.Dict()
    with pytest.raises(sanest.InvalidValueTypeError) as excinfo:
        d.get('nonexistent', type=bytes)
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


def test_dict_typed_getitem_with_invalid_slice():
    d = sanest.Dict()
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a':int:str]
    assert str(excinfo.value).startswith("slice cannot contain step value: ")


def test_dict_getitem_with_path():
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['aa'] = 123
    d['b'] = 456
    assert d['a', 'aa'] == 123
    path = ['a', 'aa']
    assert d[path] == 123

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', 123, True]
    assert str(excinfo.value) == (
        "path must contain only str or int: ['a', 123, True]")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['b', 'c', 'd']
    assert str(excinfo.value) == (
        "expected dict, got int at subpath ['b'] of ['b', 'c', 'd']")


def test_dict_getitem_with_path_and_type():
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['b'] = 123
    assert d['a', 'b':int] == 123
    path = ['a', 'b']
    assert d[path:int] == 123
    assert d['a':dict]
    path = ['a']
    assert d[path:dict]

    path = ['b', 'c']
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', path:int]
    assert str(excinfo.value).startswith("mixed path syntaxes: ")

    path = ['b', 'c']
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d[path, 'a':int]
    assert str(excinfo.value).startswith("path must contain only str or int: ")


def test_dict_contains_with_path():
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['b'] = 123
    assert ('a', 'b') in d  # tuple
    assert ['a', 'b'] in d  # list
    assert ['c', 'd'] not in d
    assert d.contains(['a', 'b'])
    assert not d.contains(['a', 'c'])
    with pytest.raises(sanest.InvalidKeyError):
        ['a', None] in d


def test_dict_contains_with_path_and_type():
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['b'] = 123
    assert d.contains(['a', 'b'], type=int)
    assert d.contains(('a', 'b'), type=int)
    assert not d.contains(('a', 'b'), type=str)
    assert ['a', 'b', int] in d
    assert ('a', 'b', int) in d
    assert ('a', 'b', str) not in d


def test_dict_get_with_path():
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['b'] = 123
    assert d.get(('a', 'b')) == 123
    assert d.get(['a', 'c']) is None
    assert d.get(['b', 'c'], 456) == 456

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.get([])
    assert str(excinfo.value) == "empty path or path component: []"


def test_dict_iteration():
    d = sanest.Dict()
    assert list(iter(d)) == []
    d['a'] = 1
    assert list(iter(d)) == ['a']


def test_empty_key():
    d = sanest.Dict()

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = []
        d[path]
    assert str(excinfo.value) == "empty path or path component: []"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = []
        d[path:str]
    assert str(excinfo.value).startswith("empty path or path component: ")

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['']
    assert str(excinfo.value) == "empty path or path component: ''"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['':int]
    assert str(excinfo.value).startswith("empty path or path component: ")

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = ['a', 'b', '']
        d[path]
    assert str(excinfo.value).startswith("empty path or path component: ")


def test_dict_copy():
    # todo: this "works" only for read-only dicts
    d = sanest.Dict()
    d['a'] = 1
    expected = {'a': 1}
    assert d.copy() == expected
    assert copy.copy(d) == expected
    assert copy.deepcopy(d) == expected
