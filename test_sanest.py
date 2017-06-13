"""
tests for sanest
"""

import builtins
import copy
import pickle

import pytest

import sanest


class MyClass:
    def __repr__(self):
        return '<MyClass>'


class WithGetItem:
    def __getitem__(self, thing):
        return sanest.parse_path_like_with_type(thing)


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
    f = sanest.parse_path_like_with_type
    assert f('a', allow_slice=False) == ('a', ['a'], None)
    assert f(['a', str], allow_slice=False) == (None, ['a'], str)
    assert f(['a', 'b'], allow_slice=False) == (None, ['a', 'b'], None)
    assert f(['a', 'b', str], allow_slice=False) == (None, ['a', 'b'], str)
    path = ['a', 'b']
    assert f([path, str], allow_slice=False) == (None, ['a', 'b'], str)


def test_pairs():
    actual = list(sanest.pairs(a=1))
    expected = [("a", 1)]
    assert actual == expected

    actual = list(sanest.pairs({'a': 1}, b=2))
    expected = [("a", 1), ("b", 2)]
    assert actual == expected

    actual = list(sanest.pairs([("a", 1), ("b", 2)]))
    expected = [("a", 1), ("b", 2)]
    assert actual == expected

    class WithKeys:
        def keys(self):
            yield "a"
            yield "b"

        def __getitem__(self, key):
            return "x"

    actual = list(sanest.pairs(WithKeys()))
    expected = [("a", "x"), ("b", "x")]
    assert actual == expected

    with pytest.raises(TypeError) as excinfo:
        for x in sanest.pairs({}, {}, {}):
            pass
    assert str(excinfo.value) == "expected at most 1 argument, got 3"


def test_missing_arg_repr():
    assert str(sanest.MISSING) == '<missing>'


#
# dicts
#

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
        "expected int, got str at path ['a', 'b', 'c']: 'not an int'")


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

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['']
        d[path]
    assert str(excinfo.value) == "empty path component: ['']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d.get([''], type=str)
    assert str(excinfo.value) == "empty path component: ['']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['a', 'b', '']
        d[path]
    assert str(excinfo.value) == "empty path component: ['a', 'b', '']"

    with pytest.raises(sanest.InvalidPathError) as excinfo:
        path = ['', 'b']
        d[path]
    assert str(excinfo.value) == "empty path component: ['', 'b']"


def test_dict_setdefault():
    d = sanest.dict()
    d['a'] = 1
    assert d.setdefault('a', 2) == 1
    assert d.setdefault(['b', 'c'], 'foo', type=str) == 'foo'
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

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault('a', 'not an int', type=int)
    assert str(excinfo.value) == (
        "expected int, got str: 'not an int'")

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault('x')
    assert str(excinfo.value) == "setdefault() requires a default value"

    with pytest.raises(sanest.InvalidValueError) as excinfo:
        d.setdefault('x', None)
    assert str(excinfo.value) == "setdefault() requires a default value"

    d2 = d.setdefault('d', {'x': 'y'})
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
    assert l1 == l1
    assert l1 == l2
    assert l1 != [2, 1]
    assert l1 != [3]
    assert l1 != object()


def test_list_repr():
    l = sanest.list([1, 2, [3, 4]])
    assert repr(l) == "sanest.list([1, 2, [3, 4]])"
    assert eval(repr(l)) == l


def test_list_wrap():
    original = ['a', 'b', ['c1', 'c2'], None]
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
    l = sanest.list(['a', {}])
    assert l[0:str] == 'a'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert l[0:bool] == 'a'
    assert str(excinfo.value) == "expected bool, got str at path [0]: 'a'"
    assert isinstance(l[1], sanest.dict)


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
    with pytest.raises(sanest.InvalidStructureError) as excinfo:
        l[0, 9]
    assert str(excinfo.value) == (
        "expected list, got str at subpath [0] of [0, 9]")


def test_list_getitem_with_path_and_type():
    l = sanest.list(['a', ['b1', 'b2']])
    assert l[1, 0:str] == "b1"
    path = [1, 0]
    assert l[path:str] == "b1"
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l[1, 1:bool]
    assert str(excinfo.value) == "expected bool, got str at path [1, 1]: 'b2'"


def test_list_setitem():
    l = sanest.list(['a', 'b'])
    l[0] = 'b'
    l[1] = sanest.list()
    assert l == ['b', []]
    with pytest.raises(IndexError) as excinfo:
        l[5] = 'a'
    assert str(excinfo.value) == "[5]"
    assert l == ['b', []]


def test_list_setitem_with_type():
    l = sanest.list(['a'])
    assert l[0:str] == 'a'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l[0:bool] = 'a'
    assert str(excinfo.value) == "expected bool, got str at path [0]: 'a'"


def test_list_setitem_with_path():
    l = sanest.list(['a', ['b', 'c', 'd']])
    l[1, 0] = 'e'
    path = (1, 1)
    l[path] = 'f'
    path = [1, 2]
    l[path] = 'g'
    assert l == ['a', ['e', 'f', 'g']]
    with pytest.raises(IndexError) as excinfo:
        l[5, 4, 3] = 'h'
    assert str(excinfo.value) == "[5]"
    assert l == ['a', ['e', 'f', 'g']]


def test_list_setitem_with_path_and_type():
    l = sanest.list(['a', ['b', 'c']])
    l[1, 0:str] = "d"
    path = [1, 1]
    l[path:str] = "e"
    assert l == ['a', ['d', 'e']]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l[1, 1:bool] = 'x'
    assert str(excinfo.value) == "expected bool, got str at path [1, 1]: 'x'"
    assert l == ['a', ['d', 'e']]


def test_list_contains():
    l = sanest.list([
        1,
        'a',
        [2, 3],
        {'c': 'd'},
        None,
    ])
    assert 1 in l
    assert 'a' in l
    assert [2, 3] in l
    assert sanest.list([2, 3]) in l
    assert {'c': 'd'} in l
    assert sanest.dict({'c': 'd'}) in l
    assert None in l
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        assert MyClass() in l
    assert str(excinfo.value) == "invalid value of type MyClass: <MyClass>"


def test_list_iteration_wrapping():
    l = sanest.list([
        {'a': 1},
        [2, 3],
        'x',
    ])
    first, second, third = l
    assert isinstance(first, sanest.dict)
    assert first == {'a': 1}
    assert isinstance(second, sanest.list)
    assert second == [2, 3]
    assert third == 'x'


def test_list_index():
    l = sanest.list([
        'a',         # 0
        {'b': 'c'},  # 1
        None,        # 2
        None,        # 3
        'a',         # 4
        None,        # 5
        None,        # 6
    ])
    assert l.index('a') == 0
    assert l.index('a', type=str) == 0
    assert l.index('a', 2) == 4
    assert l.index('a', 2, type=str) == 4
    assert l.index('a', 2, 6) == 4
    assert l.index(None, 2) == 2
    assert l.index(None, 4) == 5
    assert l.index({'b': 'c'}) == 1
    assert l.index(sanest.dict({'b': 'c'})) == 1
    with pytest.raises(ValueError) as excinfo:
        l.index('a', 5)
    assert str(excinfo.value) == "'a' is not in list"
    with pytest.raises(ValueError) as excinfo:
        l.index('a', 2, 3)
    assert str(excinfo.value) == "'a' is not in list"
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l.index(2, type=str)
    assert str(excinfo.value) == "expected str, got int: 2"


def test_list_count():
    l = sanest.list([1, 2, 3, 1, 1, 2, 3, {'a': 'b'}])
    assert l.count(1) == 3
    assert l.count(1, type=int) == 3
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l.count(1, type=str)
    assert str(excinfo.value) == "expected str, got int: 1"
    assert l.count({'a': 'b'}) == 1
    assert l.count(sanest.dict({'a': 'b'})) == 1


def list_insert():
    l = sanest.list(range(5))
    assert l == [0, 1, 2, 3, 4]
    l.insert(0, 'a')
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l.insert(0, 'a', type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert l == ['a', 0, 1, 2, 3, 4]
    l.insert(2, 'b')
    assert l == ['a', 0, 'b', 1, 2, 3, 4]
    l.insert(20, 'c')
    assert l == ['a', 0, 'b', 1, 2, 3, 4, 'c']
    l.insert(-3, 'd')
    assert l == ['a', 0, 'b', 1, 2, 'd', 3, 4, 'c']


def test_list_append():
    l = sanest.list()
    l.append(1)
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l.append('a', type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert l == [1]
    l.append(2)
    l.append([3, 4])
    l.append(sanest.list([5, 6]))
    assert len(l) == 4
    assert l == [1, 2, [3, 4], [5, 6]]


def test_list_extend():
    l = sanest.list([1, 2])
    l.extend(sanest.list([3, 4]))
    l.extend([5, 6], type=int)
    assert l == [1, 2, 3, 4, 5, 6]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l.extend(['a', 'b'], type=int)
    assert str(excinfo.value) == "expected int, got str: 'a'"
    assert l == [1, 2, 3, 4, 5, 6]
    l.extend(n for n in [7, 8])
    assert l == [1, 2, 3, 4, 5, 6, 7, 8]


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


def test_list_repeat():
    l = sanest.list([1, 2])
    assert l * 2 == [1, 2, 1, 2]
    assert 2 * l == [1, 2, 1, 2]
    assert l == [1, 2]
    assert isinstance(l, sanest.list)
    l *= 2
    assert l == [1, 2, 1, 2]
    assert isinstance(l, sanest.list)


def test_list_reverse():
    l = sanest.list(['a', 'b', 'c'])
    assert list(reversed(l)) == ['c', 'b', 'a']
    assert l == ['a', 'b', 'c']
    l.reverse()
    assert l == ['c', 'b', 'a']


def test_list_clear():
    l = sanest.list([1, 2, 3])
    l.clear()
    assert l == []


def test_list_delitem():
    l = sanest.list(['a', 'b', 'c'])
    del l[1]
    assert l == ['a', 'c']
    del l[-1]
    assert l == ['a']
    del l[0]
    assert l == []


def test_list_delitem_with_type():
    l = sanest.list(['a', 'b', 'c'])
    del l[0:str]
    assert l == ['b', 'c']
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        del l[-1:int]
    assert str(excinfo.value) == "expected int, got str at path [-1]: 'c'"
    assert l == ['b', 'c']


def test_list_delitem_with_path():
    l = sanest.list([['a', 'aa'], ['b', 'bb']])
    del l[0, 1]
    assert l == [['a'], ['b', 'bb']]
    path = [1, 0]
    del l[path]
    assert l == [['a'], ['bb']]


def test_list_delitem_with_path_and_type():
    l = sanest.list([['a', 'aa'], ['b', 'bb']])
    del l[0, 0:str]
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        del l[0, 0:int]
    assert str(excinfo.value) == "expected int, got str at path [0, 0]: 'aa'"
    assert l == [['aa'], ['b', 'bb']]
    path = [1, 1]
    del l[path:str]
    assert l == [['aa'], ['b']]


def test_list_pop():
    l = sanest.list(['a', [], 'b', 'c'])
    assert l.pop() == 'c'
    assert l.pop(-1) == 'b'
    with pytest.raises(sanest.InvalidValueError) as excinfo:
        l.pop(0, type=int)
    assert str(excinfo.value) == "expected int, got str at path [0]: 'a'"
    assert l.pop(0, type=str) == 'a'
    with pytest.raises(IndexError) as excinfo:
        l.pop(123)
    assert str(excinfo.value) == "123"
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__
    value = l.pop(type=list)
    assert isinstance(value, sanest.list)
    assert len(l) == 0
    with pytest.raises(IndexError) as excinfo:
        l.pop(0, type=int)
    assert str(excinfo.value) == "pop from empty list"


def test_list_sort():
    l = sanest.list(['a', 'c', 'b'])
    l.sort()
    assert l == ['a', 'b', 'c']
    l.sort(reverse=True)
    assert l == ['c', 'b', 'a']


#
# dicts and lists
#


def test_wrap():
    l = sanest.wrap([1, 2])
    assert isinstance(l, sanest.list)
    d = sanest.wrap({'a': 1})
    assert isinstance(d, sanest.dict)
    with pytest.raises(TypeError) as excinfo:
        sanest.wrap(MyClass())
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


def test_wrong_path_for_container_type():
    d = sanest.dict()
    l = sanest.list()
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        d[2, 'a']
    assert str(excinfo.value) == "dict path must start with str: [2, 'a']"
    with pytest.raises(sanest.InvalidPathError) as excinfo:
        l['a', 2]
    assert str(excinfo.value) == "list path must start with int: ['a', 2]"
