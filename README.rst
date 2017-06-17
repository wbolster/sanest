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

note: this is just a braindump, not a check list. some ideas may not
be good ideas after all and may never make it into this library.

* write docs and docstrings

* slice syntax to get containers out as built-in (not sanest counterpart) types

  * d['a', 'b'::list] same as d['a', 'b':list].to_list()
  * d['a', 'b'::dict] same as d['a', 'b':dict].to_dict()

* nested walk helpers dict.walk() and list.walk()

* json helpers

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

* identity checks fail when repeatedly getting the same container
  because of the wrapping. keep cached WeakValuesDict for any wrapped
  structures handed out?

* have a ``check=False`` everywhere values can be set, not just in
  ``.wrap()``

* maybe list.contains() with type= arg that checks provided value
  while also checking containment

* typed list.__contains__

* list comparison ``__lt__`` and friends
