======
sanest
======

.. image:: https://travis-ci.org/wbolster/sanest.svg?branch=master
    :target: https://travis-ci.org/wbolster/sanest

sane nested dictionaries and lists

*sanest* is a python library that makes it easy to work with nested
dictionaries and lists, such as those commonly used in json formats,
without losing your sanity.

this is a work-in-progress and you should not use it (for now).


todo and ideas
==============

note: this is just a braindump, not a check list. some ideas may not
be good ideas after all and may never make it into this library.

* nested walk helpers dict.walk() and list.walk()

* configurability

  * maybe factory helper that produces two custom classes?
  * e.g. mydict, mylist = sanest.make_contains(options=would, go=here)
  * requires major overhaul

* public api for read-only structures?

  * construct-only
  * sanest.dict.readonly()
  * what about mixing?

* maybe list.contains() with type= arg that checks provided value
  while also checking containment

* typed list.__contains__

* add a .clean(deep=True) helper (needs better name) to remove None
  values from a (nested) dict
