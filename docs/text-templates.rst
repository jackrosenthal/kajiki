.. testsetup:: *

   import kajiki

==================================
Kajiki Text Templates
==================================

Kajiki provides a full-featured text template engine in addition to the XML
templating engine for cases where you don't want to necessarily generate markup.
This document describes that language.  Templates are text files that include
template directives that control how the template is rendered and expressions
that are substituted into the generated text at render time.

Please see :doc:`templating-basics` for general information on embedding Python
code in templates.

Basic Expressions
=========================

Let's start with a hello world template:

.. doctest::

    >>> Template = kajiki.TextTemplate('Hello, $name!')
    >>> print Template(dict(name='world')).render()
    Hello, world!

By default, the $-syntax picks up any identifiers following it, as well as any
periods.  If you want something more explicit, use the extended expression form
as follows:

.. doctest::

    >>> Template = kajiki.TextTemplate('Hello, 2+2 is ${2+2}')
    >>> print Template().render()
    Hello, 2+2 is 4

If you wish to include a literal $, simply double it::

.. doctest::

    >>> Template = kajiki.TextTemplate('The price is $$${price}')
    >>> print Template(dict(price='5.00')).render()
    The price is $5.00

Control Flow
============

Kajiki provides several directives that affect the rendering of a template.  This
section describes the various directives.  Directives in text templates can
either be enclosed by `{% ... %}` characters or they can exist on a line by
themselves prefixed by a `%`.  Template directives must always be terminated by
an 'end' directive (either `{%end%}` or `%end`.

.. note::

   Whitespace can sometimes be tricky in text templates.  Kajiki provides a bit
   of help in managing it.  First, if you wish to break a line without having the
   newline included in the generated text, simply end the line with a backslash
   (\).  Kajiki will also remove any whitespace before a tag that begins with the
   delimiter `{%-`.  Directives that appear on their own line via the `%` prefix
   never appear in the output, and neither they do not generate any whitespace.

%if, %else
^^^^^^^^^^^^^^^

Only render the enclosed content if the expression evaluates to a truthy value:

.. doctest::

   >>> Template = kajiki.TextTemplate('{%if foo %}bar{%else%}baz{%end%}')
   >>> print Template(dict(foo=True)).render()
   bar
   >>> print Template(dict(foo=False)).render()
   baz

%switch, %case, %else
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Perform multiple tests to render one of several alternatives.  The first matching
`case` is rendered, and if no `case` matches, the `else` branch is rendered:

.. doctest::

   >>> Template = kajiki.TextTemplate('''$i is \
   ... {%switch i % 2 %}{%case 0%}even{%else%}odd{%end%}''')
   >>> print Template(dict(i=4)).render()
   4 is even
   >>> print Template(dict(i=3)).render()
   3 is odd

%for
^^^^^^^^^^^^^

Repeatedly render the content for each item in an iterable:

.. doctest::

   >>> Template = kajiki.TextTemplate('''%for i in range(3)
   ... $i
   ... %end''')
   >>> print Template().render(),
   0
   1
   2

%def
^^^^^^^^^^^^^^

Defines a function that can be used elsewhere in the template:

.. doctest::

   >>> Template = kajiki.TextTemplate('%def evenness(n)
   ...     {%-if n % 2 %}even{%else%}odd{%end%}\
   ... %end
   ... for i in range(2)
   ... $i is %{evenness(i)}
   ... %end''')
   >>> print Template().render()
   0 is even
   1 is odd
   
%call
^^^^^^^^^^^^^^^^^^

Call a function, passing a block of template code as a 'lambda' parameter.  Note
that this is a special case of calling when you wish to insert some templated text in the
expansion of a function call.  In normal circumstances, you would just use `${my_function(args)}`.

.. doctest::

   >>> Template = kajiki.TextTemplate('''%def quote(caller, speaker)
   ...     %for i in range(2)
   ... Quoth $speaker, ${caller(i)}
   ...     %end
   ... %end
   ... %call(n) quote(%caller, 'the raven')
   ... Nevermore $n\
   ... %end''')    
   >>> print Template().render()
   Quoth the raven, "Nevermore 0."
   Quoth the raven, "Nevermore 1."

%include
^^^^^^^^^^^^^^^^^^^^^^^^

Includes the text of another template verbatim.  The precise semantics of this
tag depend on the `TemplateLoader` being used, as the `TemplateLoader` is used to
parse the name of the template being included and render its contents into the
current template.  For instance, with the `FileLoader`, you might use the
following:

.. code-block:: none

    %include "path/to/base.txt"

whereas in the `PackageLoader` you would use

.. code-block:: none

    %include package1.package2.base

%import
^^^^^^^^^^^^^^^^^^^^^^

With `%import`, you can make the functions defined in another template available
without expanding the full template in-place.  Suppose that we saved the
following template in a file `lib.txt`:

.. code-block:: none

    %def evenness(n)
        %if n % 2 == 0
            even\
        %else
            odd\
        %end
    %end        

Then (using the `FileLoader`) we could write a template using the `evenness`
function as follows:

.. code-block:: none

   %import "lib.txt" as lib
   %for i in range(5)
   %i is ${lib.evenness(i)}
   %end

Inheritance
==============

Kajiki supports a concept of inheritance whereby child templates can extend
parent templates, replacing their methods and "blocks" (to be defined below).
For instance, consider the following template "parent.txt":

.. code-block:: none

    %def greet(name)
    Hello, $name!\
    %end
    %def sign(name)
    Sincerely,
    $name\
    %end
    ${greet(to)}

    %block body
    It was good seeing you last Friday.  Thanks for the gift!
    %end

    ${sign(from)}

This would generate the following Python::

    @kajiki.expose
    def greet(name):
        yield 'Hello, '
        yield name
        yield '!'

    @kajiki.expose
    def sign(name):
        yield 'Sincerely,\n'
        yield name

    @kajiki.expose
    def _fpt_block_body():
        yield 'It was good seeing you last Friday! Thanks for the gift!\n'

    @kajiki.expose
    def __call__():
        yield greet(to)
        yield '\n\n'
        yield self._fpt_block_body()
        yield '\n\n'
        yield sign(from)

Here is the corresponding "child.txt":

.. code-block:: none

    %extends "parent.txt"
    %def greet(name)
    Dear $name:\
    %end
    %block body
    ${parent_block()}\\
    
    And don't forget you owe me money!
    %end

This would then yield the following Python::

    @kajiki.expose
    def greet(name):
        yield 'Dear '
        yield name
        yield ':'

    @kajiki.expose
    def _fpt_block_body():
        yield parent._fpt_block_body()
        yield '\n\n'
        yield 'And don\'t forget you owe me money!\n'

    @kajiki.expose
    def __call__():
        yield local.__kj__.extend(local.__kj__.import_('parent.txt')).__call__()

The final text would be (assuming context had to='Mark' and from='Rick':

.. code-block:: none

    Dear Mark:

    It was good seeing you last Friday! Thanks for the gift!

    And don't forget you owe me money!

    Sincerely,
    Rick

