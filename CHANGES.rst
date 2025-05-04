CHANGES
=======

1.0.0 (2025-05-04)
------------------

* `py:match` and structural pattern matching added.  Python 3.10+ is required
  for this feature.  Thanks @CastixGitHub for the contribution.
* PEP-517 backend switched from setuptools to hatchling.
* Removed API usages of `pkg_resources`.
* Added integration tests with TurboGears2 to ensure we don't break users.
* Python 3.8+ is now required.

0.9.2 (2022-11-24)
------------------

* Python 3.11 compatibility.
* Documentation updates and clarifications.
* Unit test updates.

0.9.1 (2022-04-20)
------------------

* Fixed compatibility for Python 3.11 alpha.
* The unit tests were moved out of the ``kajiki`` package: tests are
  now under the ``tests/`` directory.
* Migrated from Travis CI to GitHub Actions.

0.9.0 (2021-11-29)
------------------

* Support dropped for Python 2.7.
* Fixed up lnotab bugs in Python 3.6+ (``ERROR LOOKING UP LINE``
  messages).
* DTD will not be inserted before an ``<?xml ...?>`` declaration
  anymore.
* Dependency on ``nine`` dropped.
* Dropped integration for TurboGears 1.
* Improved end-to-end testing.

.. note::

   Kajiki 0.9.x will be the last series to support Python 3.4 and 3.5.
   Users are encouraged to upgrade to Python 3.6+ soon.

0.8.3 (2021-06-18)
------------------

* Fixed compatibility for Python 3.10
* Switched the test runner to pytest
* Added the ``kajiki`` command line interface
* Documentation typo corrections

.. note::

   Kajiki 0.8.3 will be the last release to support Python 2.7.
   Kajiki 0.9 will require Python 3.4+.

0.8.2 (2019-11-26)
------------------

* Fixed some HTML entities not being properly recognised

0.8.1 (2019-10-20)
------------------

* Fixed unexpected <DOCTYPE> when including templates

0.8.0 (2019-06-03)
------------------

* Fixed support for Python 3.8
* Dropped support for Python 2.6 and 3.3

0.7.2 (2018-04-16)
------------------

* Improve parsing of ``${}`` expressions and fix syntax errors reporting in braced expressions.
* Improve parsing of documents with comments before the root element

0.7.1 (2017-09-11)
------------------

* Allow to replace ``gettext`` function by providing it in the template context or through ``base_globals`` in Loader

0.7.0 (2017-06-27)
------------------

* Text for i18n is now extracted ignoring the empty spaces surrounding the text itself. Empty text will always be treated as non translatable nodes for performance reasons.
* ``extract_python`` option will now report syntax errors when extracting text for translation.

0.6.3 (2017-05-25)
------------------

* Added ``extract_python`` option to babel message extractor, this allows extracting gettext calls in ``${}`` expressions

0.6.1 (2016-11-28)
------------------

* Actually report 0.6 in kajiki/version.py
* Expose ``strip_text`` option in loader

0.6.0 (2016-11-27)
------------------

* Fixed ``py:switch`` error message wrongly mentioning ``py:with``
* Support for multiline ``${}`` expressions
* Subsequent text nodes are now squashed into a single text node. This allows translating whole paragraphs instead of single sentences.
* Allow code and function calls inside tag attributes
* Added ``strip_text`` option to XMLTemplate and i18n collector to ensure leading and trailing spaces are stipped by text nodes (also leads to minified HTML)
* Some HTML nodes that do not require being closed but is commonly considered best practice to close them are now emitted with ending tag (IE: <p>)
* Generally improved code documentation to lower entry barrier for contributors


0.5.5 (2016-06-08)
------------------

* ``py:attrs`` will now emit the attribute name itself or will omit the attribute at all in case of
  ``bool`` values for 'checked', 'disabled', 'readonly', 'multiple', 'selected', 'nohref',
  'ismap', 'declare' and 'defer',

0.5.4 (2016-06-04)
------------------

* ``py:switch`` now correctly supports multiple ``py:case`` statements.
* text inside ``<script>`` and ``<style>`` tags is no longer collected translation.
* Syntax errors now report the line and the surrounding code when there is a markup or python syntax error.
* As ``py:swtich`` discards all its content apart from ``py:case`` and ``py:else`` statements it will now correctly report an error when the statements has other content.
* ``py:else`` will now correctly detect spurious content between itself and ``py:if`` as the two must be consequential.
* Improved code documentation on core classes.

0.5.3 (2016-01-25)
------------------

* ``py:with`` statement now keeps order of variables, so that variables can depend from each other.
* Babel is no longer a dependency unless you want to use the message extractor.

0.5.2 (2015-10-13)
------------------

* TranslatableTextNodes are now only generated for non-empty strings
* ``py:with`` statement now accepts multiple variables separated by semicolon
* Babel message extractor fixed on Python2

0.5.1 (2015-07-26)
------------------

* Fix crash on PyPy

0.5.0 (2015-07-25)
------------------

* CDATA sections created by the user are now properly preserved
* ``cdata_scripts=False`` option in ``XMLTemplate`` allows disabling automatic CDATA for script and style tags.
* Autoblocks experimental feature automatically creates blocks from specified tag names.

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
