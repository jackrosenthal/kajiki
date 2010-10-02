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

Output Modes
=========================

Although Kajiki XML templates must be well-formed XML documents, Kajiki is capable of
rendering HTML or XML.  By default, Kajiki will inspect the doctype of the
template to determine how to render:

>>> tpl_text = '''<!DOCTYPE html>
... <html>
...     <head><!-- Some stuff here --></head>
...     <body>
...         <form>
...             <input type="checkbox" checked="checked"/>
...             <select>
...                 <option selected="selected">One</option>
...                 <option>Two</option>
...                 <option>Three</option>
...             </select>
...         </form>
...     </body>
... </html>'''
>>> Template = kajiki.XMLTemplate(tpl_text)
>>> print Template().render().strip()
<!DOCTYPE html><html>
    <head><!--  Some stuff here  -->
    <body>
        <form>
            <input type="checkbox" CHECKED>
            <select>
                <option SELECTED>One
                <option>Two
                <option>Three
            </select>
        </form>
>>> # If we want to override the detected type, we can pass a 'mode' param
>>> Template = kajiki.XMLTemplate(tpl_text, mode='xml')
>>> print Template().render().strip()
<!DOCTYPE html><html>
    <head><!--  Some stuff here  --></head>
    <body>
        <form>
            <input type="checkbox" checked="checked"/>
            <select>
                <option selected="selected">One</option>
                <option>Two</option>
                <option>Three</option>
            </select>
        </form>
    </body>
</html>
>>> # We can also omit the generated DOCTYPE by specifying the template
>>> # is a fragment
>>> Template = kajiki.XMLTemplate(tpl_text, mode='xml', is_fragment=True)
>>> print Template().render().strip()
<html>
    <head><!--  Some stuff here  --></head>
    <body>
        <form>
            <input type="checkbox" checked="checked"/>
            <select>
                <option selected="selected">One</option>
                <option>Two</option>
                <option>Three</option>
            </select>
        </form>
    </body>
</html>

.. note::

    In Kajiki, you can use normal XML comments, and the comments will exist in the
    generated markup.  If you wish the comments to be removed before rendering the
    document, you can begin the comment with the syntax `<!--!` instead of `<!--`:

    >>> Template = kajiki.XMLTemplate('''<div>
    ... <!-- This comment is preserved. 
    ... --><!--! This comment is stripped. -->
    ... </div>''')
    >>> print Template().render()
    <div>
    <!--  This comment is preserved. 
     -->
    </div>

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

Repeatedly render the content for each item in an iterable:

>>> Template = kajiki.XMLTemplate('''<ul>
... <li py:for="x in range(sz)">$x</li>
... </ul>''')
>>> print Template(dict(sz=3)).render()
<ul>
<li>0</li><li>1</li><li>2</li>
</ul>

py:def
^^^^^^^^^^^^^^

Defines a function that can be used elsewhere in the template:

>>> Template = kajiki.XMLTemplate('''<div
... ><py:def function="evenness(n)"
... ><py:if test="n%2==0">even</py:if><py:else>odd</py:else></py:def
... ><ul>
... <li py:for="x in range(sz)">$x is ${evenness(x)}</li>
... </ul></div>''')
>>> print Template(dict(sz=3)).render()
<div><ul>
<li>0 is even</li><li>1 is odd</li><li>2 is even</li>
</ul></div>


py:call
^^^^^^^^^^^^^^^^^^

Call a function, passing a block of template code as a 'lambda' parameter.  Note
thnat this is a special case of calling when you wish to insert some templated text in the
expansion of a function call.  In normal circumstances, you would just use `${my_function(args)}`.

>>> Template = kajiki.XMLTemplate('''<div
... ><py:def function="quote(caller, speaker)"
... ><ul>
...    <li py:for="i in range(sz)">Quoth $speaker, ${caller(i)}</li>
... </ul></py:def
... ><py:call args="n" function="quote(%caller, 'the raven')"
... >Nevermore $n</py:call></div>''')
>>> print Template(dict(sz=3)).render()
<div><ul>
   <li>Quoth the raven, Nevermore 0</li><li>Quoth the raven, Nevermore 1</li><li>Quoth the raven, Nevermore 2</li>
</ul></div>

py:include
^^^^^^^^^^^^^^^^^^^^^^^^

Includes the text of another template verbatim.  The precise semantics of this
tag depend on the `TemplateLoader` being used, as the `TemplateLoader` is used to
parse the name of the template being included and render its contents into the
current template.  For instance, with the `FileLoader`, you might use the
following:

.. code-block:: xml

    <py:include href="path/to/base.txt"/>

whereas in the `PackageLoader` you would use

.. code-block:: xml

    <py:include href="package1.package2.base"/>

py:import
^^^^^^^^^^^^^^^^^^^^^^

With `py:import`, you can make the functions defined in another template available
without expanding the full template in-place.  Suppose that we saved the
following template in a file `lib.xml`:

.. code-block:: xml

    <py:def function="evenness(n)">
       <py:if test="n%2==0">even</py:if><py:else>odd</py:else>
    </py:def>

Then (using the `FileLoader`) we could write a template using the `evenness`
function as follows:

.. code-block:: xml

    <div>
       <py:import hef="lib.xml" alias="lib"/>
       <ul>
          <li py:for="i in range(sz)">$i is ${lib.evenness(i)}</li>
       </ul>
    </div>      

py:with
----------

Using `py:with`, you can temporarily assign variables values for the extent of
the block: 

>>> Template = kajiki.XMLTemplate('''<div py:with="a='foo'">
... <div>$a</div>
... <div py:with="a=5">$a</div>
... <div>$a</div>
... </div>''')
>>> print Template().render()
<div>
<div>foo</div>
<div>5</div>
<div>foo</div>
</div>

Content Generation
=========================

py:attrs
^^^^^^^^^^^^^^

With the `py:attrs` custom attribute, you can include dynamic attributes in an
xml/html tag by passing a either a Python dict or a list of pairs:

>>> Template = kajiki.XMLTemplate('<div py:attrs="attrs"/>')
>>> print Template(dict(attrs={'id':'foo', 'class':'bar'})).render()
<div id="foo" class="bar"/>
>>> print Template(dict(attrs=[('id', 'foo'), ('class', 'bar')])).render()
<div id="foo" class="bar"/>

Any attribute values that evaluate to `None` will not be emitted in the generated
markup:

>>> Template = kajiki.XMLTemplate('<div py:attrs="attrs"/>')
>>> print Template(dict(attrs={'id':'foo', 'class':None})).render()
<div id="foo"/>

py:strip
^^^^^^^^^^^^^^

With `py:strip`, you can remove the tag to which the attribute is attached
without removing the content of the tag:

>>> Template = kajiki.XMLTemplate('<div><div py:strip="True">Foo</div></div>')
>>> print Template().render()
<div>Foo</div>

py:content
^^^^^^^^^^^^^^

With `py:content`, you can remove the tag to which the attribute is attached
without removing the content of the tag:

>>> Template = kajiki.XMLTemplate('<div py:content="content"/>')
>>> print Template(dict(content="Foo")).render()
<div>Foo</div>

py:replace
^^^^^^^^^^^^^^

With `py:replace`, you can replace the entire tag to which the document is
attached and its children:

>>> Template = kajiki.XMLTemplate('<div py:replace="content"/>')
>>> print Template(dict(content="Foo")).render()
Foo

Inheritance (py:extends, py:block)
===================================

Kajiki supports a concept of inheritance whereby child templates can extend
parent templates, replacing their "methods" (functions) and "blocks" (to be defined below).
For instance, consider the following template "parent.xml":

.. code-block:: xml

    <div>
       <py:def function="greet(name)"
          >Hello, $name!</py:def>
       <py:def function="sign(name)"
          >Sincerely,<br/>
          <em>$name</em></py:def>
       ${greet(to)}

       <p py:block="body">It was good seeing you last Friday.
       Thanks for the gift!</p>

       ${sign(from_)}
    </div>

This would render to something similar to the following (assuming a context of 
`dict(to=Mark, from_=Rick)`:

.. code-block:: xml

   <div>
      Hello, Mark!

      <p>It was good seeing you last friday.  
      Thanks for the gift!</p>

      Sincerely, <br/>
      Rick
   </div>

Now we can extend "parent.xml" with "child.xml":

.. code-block:: xml

   <py:extends href="parent.xml">
      <py:def function="greet(name)"
      >Dear $name:</py:def>
      <py:block name="body">${parent_block()}
      <p>And don't forget you owe me money!</p>
      </py:block>
   </py:extends>

Rendering this template would then give us:

.. code-block:: xml

   <div>
      Dear, Mark:

      <p>It was good seeing you last friday.  
      Thanks for the gift!</p>
      <p>And don't forget you owe me money!</p>

      Sincerely, <br/>
      Rick
   </div>

Notice how in the child block, we have overridden both the block "body" and the
function "greet."  When overriding a block, we always have access to the parent
template's block of the same name via the `parent_block()` function.  

If you ever need to access the parent template itself (perhaps to call another
function), kajiki provides access to a special variable in child templates
`parent`.  Likewise, if a template is being extended, the variable `child` is
available.  Kajiki also provides the special variables `local` (the template
currently being defined) and `self` (the child-most template of an inheritance
chain).  The following example illustrates these variables in a 3-level
inheritance hierarchy:

>>> parent = kajiki.XMLTemplate('''<div
... ><h1 py:def="header()">Header name=$name</h1
... ><h6 py:def="footer()">Footer</h6
... ><div py:def="body()">
... id() = ${id()}
... local.id() = ${local.id()}
... self.id() = ${self.id()}
... child.id() = ${child.id()}
... </div><span py:def="id()">parent</span>
... ${header()}
... ${body()}
... ${footer()}
... </div>''')
>>> mid = kajiki.XMLTemplate('''<py:extends href="parent.html"
... ><span py:def="id()">mid</span
... ></py:extends>''')
>>> child=kajiki.XMLTemplate('''<py:extends href="mid.html"
... ><span py:def="id()">child</span
... ><div py:def="body()">
... <h2>Child Body</h2>
... ${parent.body()}
... </div></py:extends>''')
>>> loader = kajiki.MockLoader({
... 'parent.html':parent,
... 'mid.html':mid,
... 'child.html':child})
>>> Template = loader.import_('child.html')
>>> print Template(dict(name='Rick')).render()
<div>
<h1>Header name=Rick</h1>
<div>
<h2>Child Body</h2>
<div>
id() = <span>child</span>
local.id() = <span>parent</span>
self.id() = <span>child</span>
child.id() = <span>mid</span>
</div>
</div>
<h6>Footer</h6>
</div>


