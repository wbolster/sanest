"""
tests for sanest
"""

import sanest

import pytest


@pytest.mark.parametrize(
    'key',
    [123, None, b"foo", True])
def test_dict_string_keys_only(key):
    d = sanest.dict()

    with pytest.raises(TypeError) as excinfo:
        d[key]
    assert str(excinfo.value).startswith("invalid key: ")

    with pytest.raises(TypeError) as excinfo:
        d[key] = key
    assert str(excinfo.value).startswith("invalid key: ")

    with pytest.raises(TypeError) as excinfo:
        d.get(key)
    assert str(excinfo.value).startswith("invalid key: ")

    with pytest.raises(TypeError) as excinfo:
        key in d
    assert str(excinfo.value).startswith("invalid key: ")


def test_dict_basics():
    d = sanest.dict()
    d['a'] = 1
    assert d['a'] == 1
    d.setdefault('a', 2)
    d.setdefault('b', 2)
    assert d['a'] == 1
    assert d['b'] == 2


def test_dict_typed_lookup():
    d = sanest.dict()
    d['a'] = 'aaa'
    d['b'] = 2

    assert d['a':str] == 'aaa'
    assert d['b':int] == 2

    with pytest.raises(ValueError) as excinfo:
        d['a':int]
    assert str(excinfo.value) == "requested int, got str: 'aaa'"

    with pytest.raises(TypeError) as excinfo:
        d['nonexistent':bytes]
    assert str(excinfo.value) == "type must be one of bool, float, int, str"

    with pytest.raises(TypeError) as excinfo:
        d['a':int:str]
    assert str(excinfo.value) == "invalid key: slice cannot contain step value"


def test_dict_path_lookup():
    # todo: nice way to constructed nested dicts
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d['a', 'b'] == 123
    assert d['a', 'b':int] == 123
