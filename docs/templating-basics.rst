.. testsetup:: *

   import kajiki

Kajiki Templating Basics
=================================

Kajiki provides a two templating engines, one which is useful for generating
markup (HTML or XML most likely), and one of which is useful for generating plain
text.  This document describes the aspects of the two engines that are similar
and the basic API for using them.

Synopsis
--------------

A Kajiki *xml template* is a well-formed XML document that may include one or
more custom tags and attributes prefixed by the namespace 'py:'.  XML templates
also may contain python expressions that will be evaluated at template expansion
time as well as processing instructions that may contain Python code.  XML
templates should be used when generating XML or HTML, as they provide awareness
of well-formedness rules and proper escaping.

The following is an example of a simple Kajki markup template:

.. code-block:: xml

    <?python
      title = "A Kajiki Template"
      fruits = ["apple", "orange", "kiwi"]
    ?>
    <html>
      <head>
        <title py:content="title">This is replaced.</title>
      </head>
      <body>
        <p>These are some of my favorite fruits:</p>
        <ul>
          <li py:for="fruit in fruits">
            I like ${fruit}s
          </li>
        </ul>
      </body>
    </html>

This template would generate output similar to this (in X(H)ML mode):

.. code-block:: xml

    <html>
      <head>
        <title>A Kajiki Template</title>
      </head>
      <body>
        <p>These are some of my favorite fruits:</p>
        <ul>
          <li>I like apples</li>
          <li>I like oranges</li>
          <li>I like kiwis</li>
        </ul>
      </body>
    </html>

or this (in HTML mode):

.. code-block:: html

    <html>
      <head>
        <title>A Kajiki Template</title>
      <body>
        <p>These are some of my favorite fruits:
        <ul>
          <li>I like apples
          <li>I like oranges
          <li>I like kiwis
        </ul>

*Text templates*, on the other hand, are plain text documents that can contain
 embedded Python directives and expressions.  Text templates should be used when
 generating non-markup text format such as email.  Here is a simple text template:

.. code-block:: none

   Dear $name,
   These are some of my favorite fruits:
   %for fruit in fruts
     * $fruit
   %end

This would generate something similar to the following:

.. code-block:: none

   Dear Rick,
   These are some of my favorite fruits:
     * Apples
     * Bananas
     * Pears

Python API
-------------------------

In order to actually use Kajiki in generating text (either via the XML or the
text-based languages), the pattern is as follows:

  #. Obtain an XMLTemplate or TextTemplate subclass containing the template source.  This can either be done directly or via a template loader.
  #. Instantiate the template with one constructor argument, a dict containing all the values that should be made available as global variables to the template.
  #. Render the template instance using its render() method (for rendering to a single string) or iterating through it (for "stream") rendering.

For instance:

.. doctest::

   >>> Template = kajiki.XMLTemplate('<h1>Hello, $name!</h1>')
   >>> t = Template(dict(name='world'))
   >>> t.render()
   u'<h1>Hello, world!</h1>'

Using text templates is similar:

.. doctest::

   >>> Template = kajiki.TextTemplate('Hello, $name!')
   >>> t = Template(dict(name='world'))
   >>> t.render()
   u'Hello, world!'

You can also use a template loader to indirectly generate the template classes.
Using a template loader give two main advantages over directly instantiating
templates: 

 * Compiled templates are cached and only re-parsed when the template changes
 * Several template tags such as `extends`, `import`, and `include` that require knowlege of other templates become enabled.

Using a template loader would look similar to the following::

    loader = PackageLoader()
    Template = loader.import_('my.package.text.template')
    t = Template(dict(title='Hello, world!')
    print t.render()

Template Expressions and Code Blocks
-------------------------------------------------------

Python expressions can be used in "plain text" areas of templates, including, in
XML templates, tag attributes.  They are also used in some directive arguments.
Whenever a Python expression is used in a "plain text" area, it must be prefixed
by a dollar sign ($) and possibly enclosed in curly braces.  If the expression
starts with a letter and contains only letters, digits, dots, and underscores,
then the curly braces may be omitted.  In all other cases, they are required.
For example:

.. doctest::

   >>> Template = kajiki.XMLTemplate('<em>${items[0].capitalize()}</em>')
   >>> Template(dict(items=['first', 'second'])).render()
   u'<em>First</em>'
   >>> import sys
   >>> Template = kajiki.TextTemplate('Maxint is $sys.maxint')
   >>> Template(dict(sys=sys)).render()
   u'Maxint is 9223372036854775807'

Escaping
^^^^^^^^^^^^^^

If you need a literal dollar sign where Kajiki would normally detect an
expression, you can simply double the dollar sign:

.. doctest::

   >>> Template = kajiki.XMLTemplate('<em>$foo</em>')
   >>> Template().render()
   Traceback (most recent call last):
      ...
   NameError: global name 'foo' is not defined
   >>> Template = kajiki.XMLTemplate('<em>$$foo</em>')
   >>> Template().render()
   u'<em>$foo</em>'

Code Blocks
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Templates also support full Python syntax, using the <?py ?> processing
instruction:

.. code-block:: xml

    <div>
        <?py import sys>
        Maxint is $sys.maxint
    </div>

This will produce the following output:

.. code-block:: xml

    <div>
        Maxint is 9223372036854775807
    </div>

In text blocks, the %py (or {%py%} directive accomplishes the same goal:

.. code-block:: none

    %py import sys
    Maxint is $sys.maxint

This will produce:

.. code-block:: none

    Maxint is 9223372036854775807
    
In both of the above cases, the Python code runs in the 'local scope' of the
template's main rendering function, so any variables defined there will not be
accessible in functions or blocks defined elsewhere in the template.  To force
the python block to run at 'module-level' in XML templates,  simply prefix the
first line of the Python with a percent (%) sign:

.. doctest::

   >>> Template = kajiki.XMLTemplate('''<div
   ... ><?py %import os
   ... ?><py:def function="test()"
   ... >${os.path.join('a', 'b', 'c')}</py:def
   ... >${test()}</div>''')
   >>> Template().render()
   u'<div>a/b/c</div>'

In text templates, replace the %py directive with %py%:

.. doctest::

   >>> Template = kajiki.TextTemplate('''%py% import os
   ... %def test()
   ... ${os.path.join('a','b','c')}\\
   ... %end
   ... ${test()}''')
   >>> Template().render()
   u'a/b/c'

Built-in Functions and Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All templates have access to the following functions and variables:

.. function:: literal(x)

   Wrap some user-generated text so that it doesn't get escaped along with
   everything else.

.. data:: local

   The current template being defined

.. data:: self

   The current template being defined, or, if used in the context of a parent
   template that is being extended, the final ("child-most") template in the
   inheritance hierarchy.

.. data:: parent

   The parent template (via py:extends) of the template being defined

.. data:: child

   The child template (via py:extends) of the template being defined

Template Directives
--------------------------------------------

Template directives provide control flow and inheritance functionality for
templates.  As their syntax depends on whether you're using XML or text
templates, please refer to :doc:`xml-templates` or :doc:`text-templates` 
for more information.
