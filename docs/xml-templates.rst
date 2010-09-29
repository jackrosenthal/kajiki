.. testsetup:: *

   import kajiki

==================================
Kajiki XML Templates
==================================

Kajiki provides a full-featured XML-based template engine that guarantees
well-formed output when generating HTML and XML.  This document describes that
language.  Templates are XML files that include template directives that control
how the template is rendered and expressions that are substituted into the
generated text at render time. 

Please see :doc:`templating-basics` for general information on embedding Python
code in templates.

Basic Expressions
=========================

Let's start with a hello world template:

>>> Template = kajiki.XMLTemplate('<div>Hello, $name!</div>')
>>> print Template(dict(name='world')).render()
<div>Hello, world!</div>

By default, the $-syntax picks up any identifiers following it, as well as any
periods.  If you want something more explicit, use the extended expression form
as follows:

>>> Template = kajiki.XMLTemplate('<div>Hello, 2+2 is ${2+2}</div>')
>>> print Template().render()
<div>Hello, 2+2 is 4</div>

If you wish to include a literal $, simply double it:

>>> Template = kajiki.XMLTemplate('<div>The price is $$${price}</div>')
>>> print Template(dict(price='5.00')).render()
<div>The price is $5.00</div>

You can also include expressions in template attributes:

>>> Template = kajiki.XMLTemplate('<div id="$foo">Bar</div>')
>>> print Template(dict(foo='baz')).render()
<div id="baz">Bar</div>

Control Flow
============

Kajiki provides several directives that affect the rendering of a template.  This
section describes the various directives.  Directives in text templates can
either appear as special attributes on tags prefixed by `py:` or as standalone
tags whose tagname is prefixed by `py:`.

py:if, py:else
^^^^^^^^^^^^^^^

Only render the enclosed content if the expression evaluates to a truthy value:

>>> Template = kajiki.XMLTemplate('<div><py:if test="foo">bar</py:if><py:else>baz</py:else></div>')
>>> print Template(dict(foo=True)).render()
<div>bar</div>
>>> print Template(dict(foo=False)).render()
<div>baz</div>
>>> Template = kajiki.XMLTemplate('<div><span py:if="foo">bar</span></div>')
>>> print Template(dict(foo=True)).render()
<div><span>bar</span></div>
>>> print Template(dict(foo=False)).render()
<div></div>

py:switch, py:case, py:else
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Perform multiple tests to render one of several alternatives.  The first matching
`case` is rendered, and if no `case` matches, the `else` branch is rendered:

>>> Template = kajiki.XMLTemplate('''<div>
... $i is <py:switch test="i % 2">
... <py:case value="0">even</py:case>
... <py:else>odd</py:else>
... </py:switch></div>''')
>>> print Template(dict(i=4)).render()
<div>
4 is even</div>
>>> print Template(dict(i=3)).render()
<div>
3 is odd</div>

py:for
^^^^^^^^^^^^^

py:def
^^^^^^^^^^^^^^

py:call
^^^^^^^^^^^^^^^^^^

py:include
^^^^^^^^^^^^^^^^^^^^^^^^

py:import
^^^^^^^^^^^^^^^^^^^^^^

Content Generation
=========================

py:attrs
^^^^^^^^^^^^^^

py:strip
^^^^^^^^^^^^^^

py:content
^^^^^^^^^^^^^^

py:replace
^^^^^^^^^^^^^^

Inheritance (py:extends, py:block)
===================================

