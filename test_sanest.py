"""
tests for sanest
"""

import copy

import pytest

import sanest


def test_dict_basics():
    d = sanest.dict()
    d['a'] = 1
    assert d['a'] == 1
    d['a'] = 2
    d['b'] = 3
    assert d['a'] == 2
    assert d['b'] == 3


def test_dict_comparison():
    d1 = sanest.dict()
    d1['a'] = 1
    d2 = sanest.dict()
    d2['a'] = 1
    d3 = {'a': 1}
    assert d1 == d2 == d3


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


def test_dict_contains():
    d = sanest.dict()
    d['a'] = 1
    assert 'a' in d
    assert 'b' not in d


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


def test_dict_getitem():
    d = sanest.dict()

    d['a'] = 1
    assert d['a'] == 1

    with pytest.raises(KeyError) as excinfo:
        d['x']
    assert str(excinfo.value) == "'x'"


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
    assert str(excinfo.value) == "'c'"


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

    # the 'default' argument is not type checked
    assert d.get('b', type=int) is None
    assert d.get('b', 234, type=int) == 234
    assert d.get('b', 'not an int', type=int) == 'not an int'

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        # here the default is identical to the actual value. type
        # checking should prevent a non-string return value.
        d.get('a', value, type=str)
    assert str(excinfo.value) == "expected str, got int at path ['a']: 123"


def test_dict_getitem_with_invalid_type():
    d = sanest.dict()
    with pytest.raises(sanest.InvalidValueTypeError) as excinfo:
        d['nonexistent':bytes]
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


def test_dict_get_with_invalid_type():
    d = sanest.dict()
    with pytest.raises(sanest.InvalidValueTypeError) as excinfo:
        d.get('nonexistent', type=bytes)
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


def test_dict_typed_getitem_with_invalid_slice():
    d = sanest.dict()
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a':int:str]
    assert str(excinfo.value).startswith("slice cannot contain step value: ")


def test_dict_getitem_with_path():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['aa'] = 123
    d['b'] = 456
    assert d['a', 'aa'] == 123
    path = ['a', 'aa']
    assert d[path] == 123

    with pytest.raises(KeyError) as excinfo:
        path = ['x']
        d[path]
    assert str(excinfo.value) == "['x']"

    with pytest.raises(KeyError) as excinfo:
        path = ['x', 'y']
        d[path]
    assert str(excinfo.value) == "['x', 'y']"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', 123, True]
    assert str(excinfo.value) == (
        "path must contain only str or int: ['a', 123, True]")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
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
    assert str(excinfo.value) == "['x', 'y']"

    path = ['b', 'c']
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d['a', path:int]
    assert str(excinfo.value).startswith("mixed path syntaxes: ")

    path = ['b', 'c']
    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d[path, 'a':int]
    assert str(excinfo.value).startswith("path must contain only str or int: ")


def test_dict_contains_with_type():
    d = sanest.dict()
    d['a'] = 123
    assert d.contains('a', type=int)
    assert not d.contains('a', type=str)
    assert ['a', int] in d
    assert ['a', str] not in d


def test_dict_contains_with_path():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert ('a', 'b') in d  # tuple
    assert ['a', 'b'] in d  # list
    assert ['c', 'd'] not in d
    assert d.contains(['a', 'b'])
    assert not d.contains(['a', 'c'])
    with pytest.raises(sanest.InvalidKeyError):
        ['a', None] in d


def test_dict_contains_with_path_and_type():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d.contains(['a', 'b'], type=int)
    assert d.contains(('a', 'b'), type=int)
    assert not d.contains(('a', 'b'), type=str)
    assert ['a', 'b', int] in d
    assert ('a', 'b', int) in d
    assert ('a', 'b', str) not in d


def test_dict_slice_syntax_limited_use():
    """
    Slice syntax is only valid for d[a,b:int], not in other places.
    """
    d = sanest.dict()
    x = ['a', slice('b', int)]  # this is what d['a', 'b':int)] results in
    with pytest.raises(sanest.InvalidKeyError):
        d.get(x)
    with pytest.raises(sanest.InvalidKeyError):
        x in d
    with pytest.raises(sanest.InvalidKeyError):
        d.contains(x)
    with pytest.raises(sanest.InvalidKeyError):
        d.setdefault(x, 123)


def test_dict_get_with_path():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d.get(('a', 'b')) == 123
    assert d.get(['a', 'c']) is None
    assert d.get(['b', 'c'], 456) == 456

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.get([])
    assert str(excinfo.value) == "empty path or path component: []"


def test_dict_iteration():
    d = sanest.dict()
    assert list(iter(d)) == []
    d['a'] = 1
    assert list(iter(d)) == ['a']


def test_dict_empty_key():
    # though empty keys are invalid and cannot be set, simple string
    # lookups and containment checks should not raise surprising
    # exceptions.
    d = sanest.dict()
    with pytest.raises(KeyError) as excinfo:
        d['']
    assert str(excinfo.value) == "''"
    with pytest.raises(KeyError) as excinfo:
        d['':int]
    assert str(excinfo.value) == "''"
    assert d.get('', 123) == 123
    assert '' not in d
    assert not d.contains('')


def test_dict_empty_path():
    d = sanest.dict()

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = []
        d[path]
    assert str(excinfo.value) == "empty path or path component: []"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = []
        d[path:str]
    assert str(excinfo.value) == "empty path or path component: []"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.get([], type=str)
    assert str(excinfo.value) == "empty path or path component: []"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = ['']
        d[path]
    assert str(excinfo.value) == "empty path or path component: ['']"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.get([''], type=str)
    assert str(excinfo.value) == "empty path or path component: ['']"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = ['a', 'b', '']
        d[path]
    assert str(excinfo.value) == "empty path or path component: ['a', 'b', '']"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = ['', 'b']
        d[path]
    assert str(excinfo.value) == "empty path or path component: ['', 'b']"


def test_dict_copy():
    # todo: this "works" only for read-only dicts
    d = sanest.dict()
    d['a'] = 1
    expected = {'a': 1}
    assert d.copy() == expected
    assert copy.copy(d) == expected
    assert copy.deepcopy(d) == expected


def test_dict_set():
    d = sanest.dict()
    d.set('a', 'b')
    assert d['a'] == 'b'

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        d.set('', 'foo')
    assert str(excinfo.value) == "empty path or path component: ''"

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = ['', 'b']
        d.set(path, 'foo')
    assert str(excinfo.value) == "empty path or path component: ['', 'b']"


def test_dict_set_with_type():
    d = sanest.dict()
    d.set('a', 'b', type=str)
    assert d['a'] == 'b'

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.set('a', 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str at path ['a']: 'not an int'")


def test_dict_set_with_path():
    d = sanest.dict()
    path = ['a', 'b', 'c', 'd1']
    d[path] = 123
    assert d[path] == 123
    assert d == {'a': {'b': {'c': {'d1': 123}}}}

    path = ['a', 'b', 'c', 'd2']
    d[path] = 234
    assert d == {'a': {'b': {'c': {'d1': 123, 'd2': 234}}}}

    with pytest.raises(sanest.InvalidKeyError) as excinfo:
        path = ['', 'b']
        d.set(path, 'foo')
    assert str(excinfo.value) == "empty path or path component: ['', 'b']"


def test_dict_set_with_path_and_type():
    d = sanest.dict()
    path = ['a', 'b', 'c']
    d.set(path, 123, type=int)
    assert d[path] == 123

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.set(path, 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str at path ['a', 'b', 'c']: 'not an int'")


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
        "expected int, got str at path ['a', 'b', 'c']: 'not an int'")


def test_dict_setdefault():
    d = sanest.dict()
    d['a'] = 1
    d.setdefault('a', 2)
    d.setdefault(['b', 'c'], 'foo', type=str)
    assert d['a'] == 1
    assert d['b', 'c'] == 'foo'

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault(['b', 'c'], 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str at path ['b', 'c']: 'foo'")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault('d', 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str at path ['d']: 'not an int'")


def test_dict_update():
    d = sanest.dict()
    d['a'] = 1
    d.update({'a': 2}, b=3)
    assert d == {'a': 2, 'b': 3}


def test_dict_value_atomic_type():
    d = sanest.dict()
    d['a'] = 1
    d['b'] = 1.23
    d['c'] = "foo"
    d['d'] = True


def test_dict_value_container_type_conversion():
    d = sanest.dict()
    d['a'] = {'b': 123}
    d2 = d['a']
    assert isinstance(d2, sanest.dict)
    assert d2 == {'b': 123}
    assert d2['b':int] == 123


def test_dict_value_invalid_type():
    class MyClass:
        def __repr__(self):
            return '<MyClass>'

    d = sanest.dict()
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d['a'] = MyClass()
    assert str(excinfo.value) == (
        "cannot use values of type MyClass: <MyClass>")


def test_dict_none_value_is_delete():
    d = sanest.dict()
    d['a', 'b'] = 1
    d['a', 'b'] = None
    assert ['a', 'b'] not in d
    d['a', 'b'] = None  # idempotent


def test_dict_delitem():
    d = sanest.dict()
    with pytest.raises(KeyError) as excinfo:
        del d['a']
    assert str(excinfo.value) == "'a'"
    d['a'] = 3
    assert 'a' in d
    del d['a']
    assert 'a' not in d
    with pytest.raises(KeyError) as excinfo:
        del d['a']
    assert str(excinfo.value) == "'a'"


def test_dict_convert_to_regular_dict():
    original = {'a': {'b': 123}, "c": True}
    d = sanest.dict(original)
    as_dict = d.as_dict()
    assert type(as_dict) is dict
    assert as_dict == original


def test_dict_repr():
    d = sanest.dict({'a': {'b': {'c': 123}}})
    assert repr(d) == "sanest.dict({'a': {'b': {'c': 123}}})"
