CHANGES
=======

0.4.4 (2013-09-07)
------------------

* Also accept "$." without erroring out. In fact, accept anything.
* Add integration plugin for TurboGears 1

0.4.3 (2013-08-12)
------------------

* Accept "$(" without erroring out. Easier to write jQuery stuff.

0.4.2 (2013-08-01)
------------------

* There was a showstopper regression in FileLoader. Fixes #1

0.4.0 (2013-07-29)
------------------

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

0.3.5 (2012-05-07)
------------------

* Several bugfixes
* Output HTML attributes in alphabetical order (for testability)

0.3.4 (2011-06-01)
------------------

* Make Kajiki work on Python 2.4

0.3.2 (2010-11-26)
------------------

* Fix Python 2.5 syntax error

0.3.1 (2010-11-24)
------------------

* Add support for py:with
* Remove unused babel import that was breaking pip/easy_install
* Python 2.5 fixes
* Correctly strip None attributes and expressions
* Turn off autoescaping in text templates

0.3 (2010-10-10)
----------------

* Adds i18n support
* Fixes several bugs: [#7], [#9], [#10]
