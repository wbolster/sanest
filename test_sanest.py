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
    with pytest.raises(TypeError):
        d[key]
    with pytest.raises(TypeError):
        d[key] = key
    with pytest.raises(TypeError):
        d.get(key)
    with pytest.raises(TypeError):
        key in d


def test_dict_basics():
    d = sanest.dict()
    d['a'] = 1
    assert d['a'] == 1
    d.setdefault('a', 2)
    d.setdefault('b', 2)
    assert d['a'] == 1
    assert d['b'] == 2
