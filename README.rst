Kajiki provides fast well-formed XML templates
==============================================

Because Kajiki's input is XML, it can ensure that your HTML/XML output is
well-formed. The Genshi-like syntax, based on XML attributes or tags, is simply
beautiful and easily understood (or ignored) by web designers.
But instead of the slow performance of Genshi_, Kajiki compiles
templates to Python code that renders with blazing-fast speed, so Kajiki can
compete with the speed of Jinja_, Mako_, Chameleon_ and others.
Also, one of Genshi's misfeatures -- py:match -- is replaced with blocks which
work like Jinja's blocks.

By combining the best ideas out there -- XML input,
Genshi's syntax and features, Jinja's template inheritance and final
compilation to Python --, Kajiki is ready to become
the most widely used templating engine for web development in Python.
And more features are coming soon; stay tuned!

Example
=======

    >>> import kajiki
    >>> Template = kajiki.XMLTemplate('''<html>
    ...     <head><title>$title</title></head>
    ...     <body>
    ...         <h1>$title</h1>
    ...         <ul>
    ...             <li py:for="x in range(repetitions)">$title</li>
    ...         </ul>
    ...     </body>
    ... </html>''')
    >>> print(Template(dict(title='Kajiki is teh awesome!', repetitions=3)).render())
    <html>
        <head><title>Kajiki is teh awesome!</title></head>
        <body>
            <h1>Kajiki is teh awesome!</h1>
            <ul>
                <li>Kajiki is teh awesome!</li><li>Kajiki is teh awesome!</li><li>Kajiki is teh awesome!</li>
            </ul>
        </body>
    </html>


Links
=====

Documentation_

Kajiki is licensed under an MIT-style license_.

The git repository and `issue tracker`_ are at GitHub_. Previously the project
used SourceForge_ for the hg repository, issue tracker and forums.

We use Travis_ for continuous integration.


.. _Documentation: http://pythonhosted.org/Kajiki/
.. _license: https://github.com/nandoflorestan/kajiki/blob/master/LICENSE.rst
.. _`issue tracker`: https://github.com/nandoflorestan/kajiki/issues
.. _GitHub: https://github.com/nandoflorestan/kajiki
.. _SourceForge: http://sourceforge.net/p/kajiki/
.. _Travis: https://travis-ci.org/nandoflorestan/kajiki
.. _Genshi: https://pypi.python.org/pypi/Genshi
.. _Jinja: https://pypi.python.org/pypi/Jinja2
.. _Mako: https://pypi.python.org/pypi/Mako
.. _Chameleon: https://pypi.python.org/pypi/Chameleon
