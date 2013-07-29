0.4.0
=====
* Support Python versions 2.6, 2.7, 3.2, 3.3 in a single codebase
  using the *nine* library.
* Support HTML entities as well as XML entities in input templates.
* py:include fixed, can see global variables.
* Genshi compatibility: support built-in functions:
  defined(), value_of() and Markup().
* ``py:def``: Do not crash if a function has no content.
* ``py:strip=''`` is the same as ``py:strip='True'``.
* Correctness: escape HTML attribute values.
* Correctness: Always close script tags, even in XML mode.
* Add integration module for the Pyramid web framework.
* Give the FileLoader a *path*, not just a base *directory*.
* Documentation improvements, including the need to write CDATA sections.
* Move from Sourceforge to Github.
* Use Travis for continuous integration.
* The whole codebase is formatted according to PEP8.

0.3.2
=====

* Fix Python 2.5 syntax error

0.3.1
=====

* Add support for py:with
* Remove unused babel import that was breaking pip/easy_install
* Python 2.5 fixes
* Correctly strip None attributes and expressions
* Turn off autoescaping in text templates

0.3
===

* Adds i18n support
* Fixes several bugs: [#7], [#9], [#10]
