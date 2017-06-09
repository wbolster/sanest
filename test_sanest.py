"""
tests for sanest
"""

import copy
import pickle

import pytest

import sanest


class MyClass:
    def __repr__(self):
        return '<MyClass>'


def test_parse_path_like_with_type():
    class WithGetItem:
        def __getitem__(self, thing):
            return sanest.parse_path_like_with_type(thing)
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
    f = sanest.parse_path_like_with_type
    assert f('a', allow_slice=False) == ('a', ['a'], None)
    assert f(['a', str], allow_slice=False) == (None, ['a'], str)
    assert f(['a', 'b'], allow_slice=False) == (None, ['a', 'b'], None)
    assert f(['a', 'b', str], allow_slice=False) == (None, ['a', 'b'], str)
    assert f([path, str], allow_slice=False) == (None, ['a', 'b'], str)


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
    d4 = sanest.dict()
    d4['b'] = 2
    assert d4 != d1
    assert d4 != d3


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
    with pytest.raises(sanest.InvalidTypeError) as excinfo:
        d['nonexistent':bytes]
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


def test_dict_get_with_invalid_type():
    d = sanest.dict()
    with pytest.raises(sanest.InvalidTypeError) as excinfo:
        d.get('nonexistent', type=bytes)
    assert str(excinfo.value) == (
        "type must be one of dict, list, bool, float, int, str: "
        "<class 'bytes'>")


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

    path = ['b', 'c']
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d['a', path:int]
    assert str(excinfo.value).startswith("mixed path syntaxes: ")

    path = ['b', 'c']
    with pytest.raises(sanest.InvalidPathError) as excinfo:
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
    with pytest.raises(sanest.InvalidPathError):
        ['a', None] in d


def test_dict_contains_with_path_and_type():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d.contains(['a', 'b'], type=int)
    assert d.contains(('a', 'b'), type=int)
    assert ['a', 'b', int] in d
    assert ('a', 'b', int) in d
    assert not d.contains(('a', 'b'), type=str)
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
        d.contains(x)
    with pytest.raises(sanest.InvalidPathError):
        d.setdefault(x, 123)


def test_dict_get_with_path():
    d = sanest.dict()
    d['a'] = sanest.dict()
    d['a']['b'] = 123
    assert d.get(('a', 'b')) == 123
    assert d.get(['a', 'c']) is None
    assert d.get(['b', 'c'], 456) == 456

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.get([])
    assert str(excinfo.value) == "invalid path: []"


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
    assert str(excinfo.value) == "['']"
    with pytest.raises(KeyError) as excinfo:
        d['':int]
    assert str(excinfo.value) == "['']"
    assert d.get('', 123) == 123
    assert '' not in d
    assert not d.contains('')


def test_dict_empty_path():
    d = sanest.dict()

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = []
        d[path]
    assert str(excinfo.value) == "invalid path: []"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = []
        d[path:str]
    assert str(excinfo.value) == "invalid path: []"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.get([], type=str)
    assert str(excinfo.value) == "invalid path: []"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['']
        d[path]
    assert str(excinfo.value) == "invalid path: ['']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.get([''], type=str)
    assert str(excinfo.value) == "invalid path: ['']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['a', 'b', '']
        d[path]
    assert str(excinfo.value) == "invalid path: ['a', 'b', '']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['', 'b']
        d[path]
    assert str(excinfo.value) == "invalid path: ['', 'b']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.set('', 'foo')
    assert str(excinfo.value) == "invalid path: ['']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['', 'b']
        d.set(path, 'foo')
    assert str(excinfo.value) == "invalid path: ['', 'b']"


def test_dict_set():
    d = sanest.dict()
    d.set('a', 'b')
    assert d['a'] == 'b'


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

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['', 'b']
        d.set(path, 'foo')
    assert str(excinfo.value) == "invalid path: ['', 'b']"


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
    d = sanest.dict({'a': {'b': 2, 'c': 3}})
    assert d.pop(['a', 'b']) == 2
    assert d.pop(['a', 'c'], 33) == 3
    assert d == {'a': {}}
    assert d.pop(['a', 'x'], 99, type=str) == 99
    with pytest.raises(KeyError) as excinfo:
        d.pop(['a', 'x'], type=str)
    assert str(excinfo.value) == "['a', 'x']"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__


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
    assert d == {}  # empty because of None values
    d = sanest.dict.fromkeys(keys, 123)
    assert d == {'a': 123, 'b': 123}


def test_dict_wrap():
    original = {'a': {'b': 12}}
    d = sanest.dict.wrap(original)
    assert d['a', 'b'] == 12
    assert d.unwrap() is original


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


def test_dict_value_validation():
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
        sanest.wrap({123: True})
    assert str(excinfo.value) == (
        "invalid dict key: 123")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        sanest.wrap({"foo": MyClass()})
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_dict_wrap_skip_validation():
    invalid_dict = {True: False}
    wrapped = sanest.wrap(invalid_dict, check=False)
    unwrapped = wrapped.unwrap()
    assert unwrapped is invalid_dict


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
    l = sanest.list(regular_list)
    assert len(l) == 2
    with pytest.raises(TypeError) as excinfo:
        sanest.list([1, 2, 3], [4, 5], [6, 7])
    assert str(excinfo.value) == "expected at most 1 argument, got 3"


def test_list_comparison():
    l1 = sanest.list([1, 2])
    l2 = sanest.list([1, 2])
    normal_list = [1, 2]
    assert l1 == normal_list
    assert l1 == l2
    assert l1 == [1, 2]
    assert l1 != [2, 1]
    assert l1 != [3]
    assert l1 != object()


def test_list_repr():
    l = sanest.list([1, 2, [3, 4]])
    assert repr(l) == "sanest.list([1, 2, [3, 4]])"
    assert eval(repr(l)) == l


def test_list_wrap():
    original = ['a', 'b', ['c1', 'c2']]
    l = sanest.list.wrap(original)
    assert l[2, 0] == 'c1'
    assert l.unwrap() is original


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

    l = sanest.list.wrap(original, check=False)
    assert len(l) == 2


def test_list_getitem():
    l = sanest.list(['a', 'b'])
    assert l[0] == 'a'
    assert l[1] == 'b'
    with pytest.raises(IndexError) as excinfo:
        l[2]
    assert str(excinfo.value) == "[2]"


def test_list_getitem_with_type():
    l = sanest.list(['a'])
    assert l[0:str] == 'a'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert l[0:bool] == 'a'
    assert str(excinfo.value) == "expected bool, got str at path [0]: 'a'"


def test_list_getitem_with_path():
    l = sanest.list(['a', ['b1', 'b2']])
    assert l[1, 0] == 'b1'
    path = (1, 0)
    assert l[path] == 'b1'
    path = [1, 0]
    assert l[path] == 'b1'
    with pytest.raises(IndexError) as excinfo:
        l[1, 2, 3, 4]
    assert str(excinfo.value) == "[1, 2]"


def test_list_getitem_with_path_and_type():
    l = sanest.list(['a', ['b1', 'b2']])
    assert l[1, 0:str] == "b1"
    path = [1, 0]
    assert l[path:str] == "b1"
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l[1, 1:bool]
    assert str(excinfo.value) == "expected bool, got str at path [1, 1]: 'b2'"


def test_list_iteration_wrapping():
    l = sanest.list([
        {'a': 1},
        [2, 3],
    ])
    first, second = l
    assert isinstance(first, sanest.dict)
    assert first == {'a': 1}
    assert isinstance(second, sanest.list)
    assert second == [2, 3]


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
