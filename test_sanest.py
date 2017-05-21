"""
tests for sanest
"""

import sanest

import pytest


@pytest.mark.parametrize(
    'key',
    [123, None, b"foo", True, []])
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


def test_dict_typed_lookup():
    d = sanest.Dict()
    d['a'] = 'aaa'
    d['b'] = 2

    assert d['a':str] == 'aaa'
    assert d['b':int] == 2
    assert d.get('a', type=str) == 'aaa'
    assert d.get('c', type=str) is None
    assert d.get('c', default=123, type=str) == 123

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a':int]
    assert str(excinfo.value) == "requested int, got str: 'aaa'"

    with pytest.raises(sanest.InvalidValueTypeError) as excinfo:
        d['nonexistent':bytes]
    assert str(excinfo.value) == "type must be one of bool, float, int, str"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a':int:str]
    assert str(excinfo.value).startswith("slice cannot contain step value: ")


def test_dict_nested_lookup():
    # todo: nice way to constructed nested dicts
    d = sanest.Dict()
    d['a'] = sanest.Dict()
    d['a']['b'] = 123

    assert d['a', 'b'] == 123
    assert d['a', 'b':int] == 123
    assert ('a', 'b') in d
    assert ['a', 'b'] in d
    assert ['c', 'd'] not in d
    assert d.get(('a', 'b')) == 123

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', 123, True]

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.get([])
    assert str(excinfo.value).startswith("empty path: ")
