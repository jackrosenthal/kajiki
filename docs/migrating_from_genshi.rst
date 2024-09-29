Migrating from Genshi
======================================

Kajiki uses syntax derived from the syntax of Genshi_.  In particular, the
following directives are supported, with semantics intended to be nearly
identical to those of Genshi_.

 * ``py:def``
 * ``py:choose`` -- renamed ``py:with``
 * ``py:when`` -- renamed ``py:case``
 * ``py:otherwise`` -- renamed ``py:else``
 * ``py:for``
 * ``py:if``
 * ``py:with``
 * ``py:replace``
 * ``py:content``
 * ``py:attrs``
 * ``py:strip``
 * ``xi:include`` -- renamed ``py:include``

Note that, in particular, py:match in Kajiki differs from Genshi, implementing `PEP634 <https://peps.python.org/pep-0636/>`_.

Kajiki also supports the following additional directives not in Genshi:
   
 * ``py:extends`` - indicates that this is an extension template.  The parent
   template will be read in and used for layout, with any ``py:block`` directives in
   the child template overriding the ``py:block`` directives defined in the parent.
 * ``py:block`` - used to name a replaceable 'slot' in a parent template, or to
   specify a slot override in a child template.  The ``py:block`` semantics are
   modeled after the ``{% block %}`` semantics of Jinja2_.

Generally, migration consists of a few steps that can be simple or quite
difficult based on your fondness of the ``py:match`` directive in Genshi.  In
simple cases where you have one ``master.html`` template with a few ``py:match``
directives that is ``xi:included`` into all your page templates, the following
steps should suffice:

 * Rename tags and attributes as indicated above;
   e.g. ``xi:include`` becomes ``py:include``.
 * Rewrite your *include* directives to use Kajiki's module naming system
   and relative imports.
 * In a simple case where you have only a few ``py:match`` directives, all of which
   are in a ``master.html`` template that is being included from child templates,
   I recommend that you rewrite the ``master.html`` as ``layout.html``, defining
   named ``py:block`` regions that will be overridden in child templates.
 * In your child templates, remove the ``<xi:include href="master.html">`` that
   probably lurks near the top.  Then add a ``py:extends`` directive to the
   top-level tag (usually ``<html>``).  The tag the parts of the child template
   that are intended to override parts of the parent template with the
   ``py:block`` directive.

Kajiki also provides some helper functions of Genshi:

* ``defined('some_variable')`` (which returns True if 'some_variable' exists
  in the template context),
* ``value_of('name', default_value)``, and
* ``Markup(some_string)`` (which marks a string so it won't be escaped in the
  output), though Kajiki prefers to call this ``literal(some_string)``.

Example Migration
---------------------------------

Suppose you have a couple of Genshi templates, one of which called ``master.html``
and one of which is ``index.html``.  (TurboGears developers may recognize these
files as slightly modified versions of the default templates deposited in a TG
quickstarted project.)  The contents of ``master.html`` are:

.. literalinclude:: include/master.html
   :linenos:
   :language: html

Likewise, the contents of ``index.html`` are as follows:

.. literalinclude:: include/index.html
   :linenos:
   :language: html

In order to perform our kajiki migration, we begin by creating two empty
templates.  The first one will replace our ``master.html``, and we will call it
``layout.html``:

.. literalinclude:: include/layout.html
   :linenos:
   :language: html

Note the introduction of the ``py:block`` directive, and the disappearance of the
``py:match`` directives from ``master.html``.  ``py:block`` mimics the behavior of
Jinja2 "blocks", providing a name to a construct in a parent template which can be
replaced by the contents of ``py:block`` -named constructs in child templates.  For
instance, the "title" slot in ``layout.html``:

.. literalinclude:: include/layout.html
   :linenos:
   :language: html
   :lines: 8

can be replaced by a similarly-named slot in the child document ``index_kajiki.html``:

.. literalinclude:: include/index_kajiki.html
   :linenos:
   :language: html
   :lines: 1-8

We also provide a way of including the contents of the parent template's slot in
a child template's slot using ``${parent_block()}``.  The following slot in
``layout.html``:

.. literalinclude:: include/layout.html
   :linenos:
   :language: html
   :lines:  16

can be replaced in ``include/index_kajiki.html`` with:

.. literalinclude:: include/index_kajiki.html
   :linenos:
   :language: html
   :lines: 9-12

Yielding the following html once rendered:

.. code-block:: html
   :linenos:

    <h1>My Header</h1>
    <h1>Some extra header data</h1>

.. _Genshi: http://genshi.edgewall.org/
.. _Jinja2: http://jinja.pocoo.org/2/documentation/
