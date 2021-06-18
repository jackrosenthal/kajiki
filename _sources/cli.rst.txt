Command Line Interface
======================

Kajiki includes a simple command line interface, useful for testing
templates, integrating into shell scripts or a ``Makefile``, or even
wire up to your email software.

Usage
-----

.. code-block:: none

   kajiki [options...] file_or_package [output_file]

``file_or_package`` should be the file path to the template.  If you
wish to load by package name instead, pass the ``-p`` or ``--package``
option, and Kajiki will assume this is a package name instead of a
filename.

By default, the template result will be written to standard output,
unless ``output_file`` is given.

Specifying Mode
^^^^^^^^^^^^^^^

Kajiki will auto-detect the mode (i.e., text vs. xml) based on the
file extension:

+-----------+---------------------------------------+
| Extension | Mode                                  |
+===========+=======================================+
| ``txt``   | Text                                  |
+-----------+---------------------------------------+
| ``xml``   | XML, rendering mode inferred from DTD |
+-----------+---------------------------------------+
| ``html``  | XML, rendering mode is ``html``       |
+-----------+---------------------------------------+
| ``html5`` | XML, rendering mode is ``html5``      |
+-----------+---------------------------------------+

If your file extension is not one of the above, or you wish override
the auto-detection process, you may pass the ``-m`` or ``--mode``
flag.  Supported values are ``text``, ``xml``, ``html``, or ``html5``.

Setting Template Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^

To set a template variable, pass the flag ``-v KEY=VALUE`` (or
``--var KEY=VALUE``), where ``KEY`` is the variable name, and
``VALUE`` is the value you want it to take.

If you need to set multiple variables, the flag can be passed multiple
times.

Extending the Load Path
^^^^^^^^^^^^^^^^^^^^^^^

By default, the command line interface will add the directory of the
file to render to the load path.

For example, consider the following directory structure::

  .
  └── templates
      ├── index.xml
      ├── main.xml
      └── pages
          ├── about.xml
          └── contact.xml

And Kajiki is being run from ``.`` like this::

  kajiki templates/pages/about.xml

Since the file to render is automatically be added to the load path,
if you wanted to include ``contact.xml`` from ``about.xml``, you could
do this:

.. code:: xml

   <py:include href="contact.xml" />

Now suppose you also want to be able to include ``main.xml`` from
``about.xml``.  One option is to add the ``templates`` directory to
the load paths using the ``-i`` or ``--path`` option::

  kajiki -i templates templates/pages/about.xml

``-i`` or ``--path`` can be passed multiple times to add multiple
directories to the load path.

.. note::

   When using the package loader (via ``-p`` or ``--package``), using
   ``-i`` will call site.addsitedir_ on each directory specified.

.. _site.addsitedir: https://docs.python.org/library/site.html#site.addsitedir
