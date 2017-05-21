"""
tests for sanest
"""

import sanest

import pytest


@pytest.mark.parametrize(
    'key',
    [123.456, None, b"foo", True, []])
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


def test_dict_basics():
    d = sanest.Dict()
    d['a'] = 1
    assert d['a'] == 1
    d.setdefault('a', 2)
    d.setdefault('b', 2)
    assert d['a'] == 1
    assert d['b'] == 2


def test_dict_typed_getitem():
    d = sanest.Dict()
    d['a'] = 'aaa'
    d['b'] = 2

    assert d['a':str] == 'aaa'
    assert d['b':int] == 2

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a':int]
    assert str(excinfo.value) == "requested int, got str: 'aaa'"


def test_dict_typed_get():
    d = sanest.Dict()
    d['a'] = 'aaa'

    assert d.get('a', type=str) == 'aaa'
    assert d.get('c', type=str) is None
    assert d.get('c', default=123, type=str) == 123

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.get('a', type=int)
    assert str(excinfo.value) == "requested int, got str: 'aaa'"


def test_dict_get_with_default_and_type():
    d = sanest.Dict()
    value = 123
    d['a'] = value

    # the 'default' argument is not type checked
    assert d.get('b', type=int) is None
    assert d.get('b', 234, type=int) == 234
    assert d.get('b', 'not an int', type=int) == 'not an int'

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        # here the default is
        # identical to the actual value. type checking should prevent a
        # non-string return value.
        d.get('a', value, type=str)
    assert str(excinfo.value) == "requested str, got int: 123"


def test_dict_typed_lookup_invalid_type():
    d = sanest.Dict()
    with pytest.raises(sanest.InvalidValueTypeError) as excinfo:
        d['nonexistent':bytes]
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


def test_dict_typed_lookup_invalid_slice():
    d = sanest.Dict()
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a':int:str]
    assert str(excinfo.value).startswith("slice cannot contain step value: ")


def test_dict_nested_lookup():
    # todo: nice way to constructed nested dicts
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['b'] = 123

    assert d['a', 'b'] == 123
    path = ['a', 'b']
    assert d[path] == 123

    assert d['a':dict]
    assert d['a', 'b':int] == 123
    path = ['a', 'b']
    assert d[path:int] == 123

    assert ('a', 'b') in d
    assert ['a', 'b'] in d
    assert ['c', 'd'] not in d

    assert d.get(('a', 'b')) == 123

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', 123, True]

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.get([])
    assert str(excinfo.value).startswith("empty path: ")

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', path:int]
    assert str(excinfo.value).startswith("mixed path syntaxes: ")


def test_empty_key():
    d = sanest.Dict()

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = []
        d[path]
    assert str(excinfo.value) == "empty path: []"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = []
        d[path:str]
    assert str(excinfo.value).startswith("empty path: ")

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['']
    assert str(excinfo.value).startswith("empty path: ''")

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['':int]
    assert str(excinfo.value).startswith("empty path: ")
