======
sanest
======

sane nested dictionaries and lists

*sanest* is a python library that makes it easy to work with nested
dictionaries and lists, such as those commonly used in json formats,
without losing your sanity.

this is a work-in-progress and you should not use it (for now).


todo and ideas
==============

* write docs and docstrings

* sensible sanest.list support

* should some_dict[2] raise some other exception because integers are
  not valid keys? (similiar for str indexes and lists)

* nested walk helpers dict.walk() and list.walk()

* json helpers

* improve exception types: unexpected structure (e.g. path lookup) versus
  wrong supplied leaf value (e.g. setitem with incorrect value)

* iteration helpers? e.g. dict.iter(type=…) or something like that?

* sanity checks that prevent creating circular references

  * possible at all? no complicated parent(s) tracking please

* maybe allow None values (optionally)

* dotted path strings or other separator? is this a good idea at all?

* configurability

  * maybe factory helper that produces two custom classes?
  * e.g. mydict, mylist = sanest.make_contains(options=would, go=here)
  * requires major overhaul

* public api for read-only structures?
  * construct-only
  * sanest.dict.readonly()
  * what about mixing?

* way to ‘infect’ an existing nested structure (which must not be used
  afterwards anymore) without making full copies.

  * requires recursively applying transformations

* alternative implementation idea: act as a wrapper around a plain
  data structure:

  * do not convert into sanest.dict/list upon assignment
  * create new wrappers on the fly, when retrieving.
  * would influence identity checks. cached weakrefs?
  * __eq__() shortcut can compare ._data identity first
  * as_dict() may optionally not return a copy (performance)
