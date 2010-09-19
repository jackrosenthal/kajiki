==================================
Kajiki Text Templates
==================================

Basic Expressions
=========================

Let's start with a hello world template:

.. code-block:: none      

    Hello, World!

This converts to the equivalent Python::

    @fpt.expose
    def __call__():
        yield 'Hello, World!\n'

Slightly more verbose "hello_name.txt":

.. code-block:: none

    Hello, $name!

This converts to the equivalent Python::

    @fpt.expose
    def __call__():
         yield 'Hello, '
         yield name
         yield '!\n'

By default, the $-syntax picks up any identifiers following it, as well as any
periods.  If you want something more explicit, use the extended expression form
as in "hello_arithmetic.txt":

.. code-block:: none
     
    Hello, 2 + 2 is ${2+2}! 

This converts to::

    @fpt.expose
    def __call__():
        yield 'Hello, 2 + 2 is '
        yield 2+2
        yield '!'

If you wish to include a literal $, simply prefix it with a backslash.

Control Flow
============

Kajiki provides several tags that affect the rendering of a template.  The
following template "control_flow.txt" illustrates:

.. code-block:: none

    A{%for i in range(5)%}
        {%if i < 2%}Low{%elif i < 4%}Mid{%else%}High{%end%}$i
        {%switch i % 2%}
            {%case 0%}
                even
            {%default%}
                odd    
            {%end%}{%end%}{%end%}

This yields the following Python::

    @fpt.expose
    def __call__():
        yield 'A\n' # from the {%for... line
        for i in range(10):
            yield '\n        ' # from the newline and initial indent of next line
            if i < 2:
                yield 'Low'
            elif i < 4:
                yield 'Mid'
            else:
                yield 'High'
            yield i
            yield '\n        ' # from the {%if... newline and next indent
            local.__fpt__.push_switch(i%2)
            # whitespace after {%switch is always stripped
            if local.__fpt__.case(0):
                yield '\n            even\n        '
            else:    
                yield '\n            odd\n        '
            local.__fpt__.pop_switch()

Which would in turn generate the following text:

.. code-block:: none

    A
        Low0
        
            even
        
        Low1

            odd
        
        Mid2

            even

        Mid3

            odd

        High4

            even

This can be quite inconvient, however.  If you want to strip whitespace before or
after a tag, just replace {%with {%-(for stripping leading whitespace) or %}
with -%} (for stripping trailing whitespace).  If you would like to remove
newlines, just end a line with a backslash.  Here is the equivalent template with
whitespace removed "control_flow_ws.txt":

.. code-block:: none

    A{%-for i in range(5) -%}\
        {%-if i < 2%}Low{%elif i < 4%}Mid{%else%}High{%end%}$i
        {%-switch i % 2%}\
            {%-case 0%}\
                even
            {%-default%}\
                odd    
            {%-end%}\
        {%-end%}\
    {%-end%}\

This would generate the following Python::

    @fpt.expose
    def __call__():
        yield 'A' 
        for i in range(10):
            if i < 2:
                yield 'Low'
            elif i < 4:
                yield 'Mid'
            else:
                yield 'High'
            yield i
            yield '\n'
            local.__fpt__.push_switch(i%2)
            if local.__fpt__.case(0):
                yield 'even\n'
            else:    
                yield 'odd\n'
            local.__fpt__.pop_switch()

Which would generate the following text:

.. code-block:: none

    ALow0
    even
    Low1
    odd
    Mid2
    even
    Mid3
    odd
    High4
    even

which is probably closer to what you wanted.  There is also a shorthand syntax
that allows for line-oriented control flow as seen in
"control_flow_ws_short.txt":

.. code-block:: none

    A\
    %for i in range(5)
        %if i < 2 
            Low\
        %elif i < 4
            Mid\
        %else
            High\
        {%-end%}$i    
        %switch i % 2
            %case 0
                even
            %default
                odd    
            %end    
        %end    
    %end

This syntax yields exactly the same results as "control_flow_ws.txt" above.

Python Blocks
==============

You can insert literal Python code into your template using the following syntax
in "simple_py_block.txt":

.. code-block:: none

    {%py%}\
        yield 'Prefix'
    {%end%}\
    Body

or alternatively:

.. code-block:: none

    %py
        yield 'Prefix'
    %end    
    Body

or even more succinctly:

.. code-block:: none

    %py yield 'Prefix'
    Body

all of which will generate the following Python::

    def __call__():
        yield 'Prefix'
        yield 'Body'

Note in particular that the Python block can have any indentation, as long as it
 is consistent (the amount of leading whitespace in the first non-empty line of
 the block is stripped from all lines within the block).  You can insert
 module-level Python (imports, etc.) by using the %py% directive (or {%py%%} as in
 "module_py_block.txt": 

.. code-block:: none

    %py%
        import sys
        import re
    %end
    Hello
    %py% import os
    %end

This yields the following Python::

    import sys
    import re

    import os

    @fpt.expose
    def __call__():
        yield 'Hello'

Functions and Imports
====================================

Kajiki provides for code reuse via the %def and %import directives.  First, let's
see %def in action in "simple_function.txt":

.. code-block:: none

    %def evenness(n)
        %if n % 2 == 0
            even\
        %else
            odd\
        %end
    %end        
    %for i in range(5)
    $i is ${evenness(i)}
    %end

This compiles to the following Python::

    @fpt.expose
    def evenness(n):
        if n % 2:
            yield 'even'
        else:
            yield 'odd'

    @fpt.expose
    def __call__():    
        for i in range(5):
            yield i
            yield ' is '
            yield evenness(i)

The %import directive allows you to package up your functions for reuse in
another template file (or even in a Python package).  For instance, consider the
following file "import_test.txt":

.. code-block:: none

    %import "simple_function.txt" as simple_function
    %for i in range(5)
    $i is ${simple_function.evenness(i)}
    %end

This would then compile to the following Python::

    @fpt.expose
    def __call__():
        simple_function = local.__fpt__.import_("simple_function.txt")
        for i in range(5):
            yield i
            yield ' is '
            yield simple_function.evenness(i)

Note that when using the %import directive, any "body" in the imported template
is ignored and only functions are imported.  If you actually wanted to insert the
body of the imported template, you would simply call the imported template as a
function itself (e.g. ${simple_function()}).

Sometimes it is convenient to pass the contents of a tag to a function.  In this
case, you can use the %call directive as shown in "call.txt":

.. code-block:: none

    %def quote(caller, speaker)
        %for i in range(5)
    Quoth $speaker, "${caller(i)}."
        %end
    %end
    %call(n) quote('the raven')
    Nevermore $n\
    %end

This results in the following Python::

    @fpt.expose
    def quote(caller, speaker):
        for i in range(5):
            yield 'Quoth '
            yield speaker
            yield ', "'
            yield caller(i)
            yield '."'

    @fpt.expose
    def __call__():    
        @fpt.expose
        def _fpt_lambda(n):
            yield 'Nevermore '
            yield n
        yield quote(_fpt_lambda, 'the raven')
        del _fpt_lambda

Which in turn yields the following output:

.. code-block:: none

       Quoth the raven, "Nevermore 0."
       Quoth the raven, "Nevermore 1."
       Quoth the raven, "Nevermore 2."
       Quoth the raven, "Nevermore 3."
       Quoth the raven, "Nevermore 4."

Includes
===============

Sometimes you just want to pull the text of another template into your template
verbatim.  For this, you use the %include directive as in "include_example.txt":

.. code-block:: none

    This is my story:
    %include "call.txt"
    Isn't it good?

which yields the following Python::

    @fpt.expose
    def __call__():
        yield 'This is my story:\n'
        yield _fpt.import("simple_function.txt")()
        yield 'Isn't it good?\n'

Which of course yields:
        
.. code-block:: none

    This is my story:
    Quoth the raven, "Nevermore 0."
    Quoth the raven, "Nevermore 1."
    Quoth the raven, "Nevermore 2."
    Quoth the raven, "Nevermore 3."
    Quoth the raven, "Nevermore 4."
    Isn't it good?

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

    @fpt.expose
    def greet(name):
        yield 'Hello, '
        yield name
        yield '!'

    @fpt.expose
    def sign(name):
        yield 'Sincerely,\n'
        yield name

    @fpt.expose
    def _fpt_block_body():
        yield 'It was good seeing you last Friday! Thanks for the gift!\n'

    @fpt.expose
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

    @fpt.expose
    def greet(name):
        yield 'Dear '
        yield name
        yield ':'

    @fpt.expose
    def _fpt_block_body():
        yield parent._fpt_block_body()
        yield '\n\n'
        yield 'And don\'t forget you owe me money!\n'

    @fpt.expose
    def __call__():
        yield local.__fpt__.extend(local.__fpt__.import_('parent.txt')).__call__()

The final text would be (assuming context had to='Mark' and from='Rick':

.. code-block:: none

    Dear Mark:

    It was good seeing you last Friday! Thanks for the gift!

    And don't forget you owe me money!

    Sincerely,
    Rick

