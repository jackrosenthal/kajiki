Migrating from Genshi
======================================

FastPt uses syntax derived from the syntax of Genshi.  In particular, the
following directives are supported, with semantics intended to be nearly identical to
those of Genshi_.

 * `py:def`
 * `py:when`
 * `py:otherwise`
 * `py:for`
 * `py:if`
 * `py:choose`
 * `py:with`
 * `py:replace`
 * `py:content`
 * `py:attrs`
 * `py:strip`
 * `xi:include`

Note that, in particular, `py:match` is not supported.  In addition, FastPt
supports the following additional directives: 

 * `py:include` - same semantics as `xi:include`, use if you don't like lots of
   namespaces in your xml
 * `py:extends` - indicates that this is an extension template.  The parent
   template will be read in and used for layout, with any `py:slot` directives in
   the child template overriding the `py:slot` directives defined in the parent.
 * `py:slot` - used to name a replaceable 'slot' in a parent template, or to
   specify a slot override in a child template.  The `py:slot` semantics are
   modeled after the `{% block %}` semantics of Jinja2_.
 * `py:super` - used to insert the contents of a parent `py:slot`, modeled after
   `{% super %}` in Jinja2_. 

Generally, migration consists of a few steps that can be simple or quite
difficult based on your fondness of the `py:match` directive in Genshi.  In
simple cases where you have one `master.html` template with a few `py:match`
directives that is `xi:included` into all your page templates, the following
steps should suffice:

 * Make sure all your templates have `<!DOCTYPE>` declarations -- this is
   required because FastPt uses lxml_ to parse the templates, and lxml_ requires
   a doctype declaration (of some type) in order to allow certain entites to
   parse (such as &nbsp;).
 * You may need to rewrite some of our `xi:include` directives to use FastPt's
   module naming system and relative imports.
 * In a simple case where you have only a few `py:match` directives, all of which
   are in a `master.html` template that is being included from child templates,
   I recommend that you rewrite the `master.html` as `layout.html`, defining
   named `py:slot` regions that will be overridden in child templates.
 * In your child templates, remove the `<xi:include href="master.html">` that
   probably lurks near the top.  Then add a `py:extends` directive to the
   top-level tag (usually `<html>`).  The tag the parts of the child template
   that are intended to override parts of the parent template with the `py:slot`
   directive.

Example Migration
==========================

TODO: starting from a TG quickstart, show how to migrate to FastPt


.. _Genshi: http://genshi.edgewall.org/
.. _Jinja2: http://jinja.pocoo.org/2/documentation/
.. _lxml: http://codespeak.net/lxml/
