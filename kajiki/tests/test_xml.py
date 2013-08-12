#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import sys
import traceback
import xml.dom.minidom
from unittest import TestCase, main
from nine import chr, str
import kajiki
from kajiki import MockLoader, XMLTemplate, FileLoader, PackageLoader


DATA = os.path.join(os.path.dirname(__file__), 'data')


class TestParser(TestCase):
    def test_parser(self):
        doc = kajiki.xml_template._Parser('<string>', '''<?xml version="1.0"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" \
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<div xmlns="http://www.w3.org/1999/xhtml"
   xmlns:py="http://genshi.edgewall.org/"
   xmlns:xi="http://www.w3.org/2001/XInclude">
  <?py import os ?>
  <!-- This is a comment -->
  <py:for each="x in range(5)">
    Hello, $name &lt;&nbsp;&gt; $x
  </py:for>
</div>''').parse()
        xml.dom.minidom.parseString(doc.toxml().encode('utf-8'))


class TestExpand(TestCase):
    def test_expand(self):
        doc = kajiki.xml_template._Parser('<string>', '''<div
        py:def="def"
        py:call="call"
        py:case="case"
        py:else="else"
        py:for="for"
        py:if="if"
        py:switch="switch"
        py:with="with"
        py:replace="replace"
        py:block="block"
        py:extends="extends">Foo</div>''').parse()
        kajiki.xml_template.expand(doc)
        node = doc.childNodes[0]
        for tagname, attr in kajiki.markup_template.QDIRECTIVES:
            if node.tagName == 'div':
                node = node.childNodes[0]
                continue
            assert node.tagName == tagname, '%s != %s' % (
                node.tagName, tagname)
            if attr:
                assert len(node.attributes) == 1
                assert node.hasAttribute(attr)
                assert node.getAttribute(attr) == tagname.split(':')[-1]
            else:
                assert len(node.attributes) == 0
            assert len(node.childNodes) == 1
            node = node.childNodes[0]


def perform(source, expected_output, context=dict(name='Rick'),
            mode='xml', is_fragment=True):
    tpl = XMLTemplate(source, mode=mode, is_fragment=is_fragment)
    try:
        rsp = tpl(context).render()
        assert isinstance(rsp, str), 'render() must return a unicode string.'
        assert rsp == expected_output, rsp
    except:
        print('\n' + tpl.py_text)
        raise
    else:
        return tpl


class TestSimple(TestCase):
    def test_empty_attr(self):
        perform(source='<img src="/foo/bar.baz.gif" alt="" />', mode='html',
            expected_output='<img alt="" src="/foo/bar.baz.gif">')

    def test_pre_whitespace(self):
        src = '<pre name="foo">\nHey there.  \n\n    I am indented.\n' \
              '</pre>'
        perform(src, src, mode='html')
        perform(src, src, mode='xml')

    def test_textarea_whitespace(self):
        src = '<textarea name="foo">\nHey there.  \n\n    I am indented.\n' \
              '</textarea>'
        perform(src, src, mode='html')
        perform(src, src, mode='xml')

    def test_script(self):
        'Always close script tags, even in xml mode.'
        source = '<html><script src="public"/></html>'
        output = '<html><script src="public"></script>'
        perform(source, output, mode='html')
        perform(source, output + '</html>', mode='xml')

    def test_script_escaping(self):
        '''In HTML script and style tags are automatically CDATA; in XML they
        must be explicitly be made so.
        '''
        script = 'if (1 < 2) { doc.write("<p>Offen&nbsp;bach</p>"); }\n'
        src = '<script><![CDATA[\n{0}]]></script>'.format(script)
        perform(src, mode='html',
                expected_output='<script>\n{0}</script>'.format(script))
        perform(src, '<script>/*<![CDATA[*/\n{0}/*]]>*/</script>'.format(
                script), mode='xml')

    def test_style_escaping(self):
        style = 'html > body { display: none; }\n'
        src = '<style><![CDATA[\n{0}]]></style>'.format(style)
        perform(src, '<style>/*<![CDATA[*/\n{0}/*]]>*/</style>'.format(style),
                mode='xml')
        perform(src, '<style>\n{0}</style>'.format(style), mode='html')

    def test_script_variable(self):
        '''Interpolate variables inside <script> tags'''
        src = '<script><![CDATA[ $name ]]></script>'
        perform(src, '<script>/*<![CDATA[*/ Rick /*]]>*/</script>', mode='xml')
        perform(src, '<script> Rick </script>', mode='html')

    def test_expr_name(self):
        perform('<div>Hello, $name</div>', '<div>Hello, Rick</div>')

    def test_expr_braced(self):
        perform('<div>Hello, ${name}</div>', '<div>Hello, Rick</div>')

    def test_expr_brace_complex(self):
        perform("<div>Hello, ${{'name':name}['name']}</div>",
                '<div>Hello, Rick</div>')

    def test_jquery_call_is_not_expr(self):
        '''Ensure we handle '$(' as a text literal, since it cannot be a
        valid variable sequence.  This simplifies, for example,
        templates containing inline scripts with jQuery calls
        which otherwise have to be written '$$(...'
        '''
        js = "$(function () { alert('.ready()'); });"
        src = "<html><pre>" + js + "</pre><script>" + js + \
              "</script></html>"
        out = "<html><pre>" + js + "</pre><script>/*<![CDATA[*/" + js + \
              "/*]]>*/</script></html>"
        perform(src, out)

    def test_xml_entities(self):
        source = "<div>Cookies &amp; Cream</div>"
        perform(source, source)

    def test_html_entities(self):
        source = "<div>Spam&nbsp;Spam &lt; Spam &gt; Spam</div>"
        output = '<div>Spam Spam &lt; Spam &gt; Spam</div>'
        assert chr(32) in output  # normal space
        assert chr(160) in output  # non breaking space
        perform(source, output)


class TestSwitch(TestCase):
    def test_switch(self):
        perform('''<div py:for="i in range(2)">
$i is <py:switch test="i % 2">
<py:case value="0">even</py:case>
<py:else>odd</py:else>
</py:switch></div>''',   '''<div>
0 is even</div><div>
1 is odd</div>''')


class TestWith(TestCase):
    def test_with(self):
        perform('''<div py:with="a='foo'">
<div>$a</div>
<div py:with="a=5">$a</div>
<div>$a</div>
</div>''',   '''<div>
<div>foo</div>
<div>5</div>
<div>foo</div>
</div>''')


class TestFunction(TestCase):
    def test_function(self):
        perform('''<div
><div py:def="evenness(n)"><py:if test="n % 2 == 0">even</py:if><py:else>odd</py:else></div>
<py:for each="i in range(2)">$i is ${evenness(i)}
</py:for
></div>''',   '''<div>
0 is <div>even</div>
1 is <div>odd</div>
</div>''')

    def test_empty_function(self):
        '''Do not crash if a function has no content.'''
        perform('<div><py:def function="bruhaha()"></py:def></div>',
                '<div></div>')


class TestCall(TestCase):
    def test_call(self):
        perform('''<div
><py:def function="quote(caller, speaker)"
><ul>
    <li py:for="i in range(2)">Quoth $speaker, ${caller(i)}</li>
</ul></py:def
><py:call args="n" function="quote(%caller, 'the raven')"
>Nevermore $n</py:call></div>''',   '''<div><ul>
    <li>Quoth the raven, Nevermore 0</li><li>Quoth the raven, Nevermore 1</li>
</ul></div>''')


class TestImport(TestCase):
    def test_import(self):
        loader = MockLoader({
            'lib.html': XMLTemplate(source='''<div>
<span py:def="evenness(n)"
    ><py:if test="n % 2 == 0"
        >even</py:if
    ><py:else
        >odd</py:else
></span>
<py:def function="half_evenness(n)"
    >half of $n is ${evenness(n/2)}</py:def>
</div>'''),
            'tpl.html': XMLTemplate(source='''<div>
<py:import href="lib.html" alias="simple_function"
/><ul>
    <li py:for="i in range(4)">
        $i is ${simple_function.evenness(i)} ${simple_function.half_evenness(i)}
    </li>
</ul>
</div>''')
        })
        tpl = loader.import_('tpl.html')
        rsp = tpl(dict(name='Rick')).render()
        assert rsp == '''<div>
<ul>
    <li>
        0 is <span>even</span> half of 0 is <span>even</span>
    </li><li>
        1 is <span>odd</span> half of 1 is <span>odd</span>
    </li><li>
        2 is <span>even</span> half of 2 is <span>odd</span>
    </li><li>
        3 is <span>odd</span> half of 3 is <span>odd</span>
    </li>
</ul>
</div>''', rsp

    def test_import_auto(self):
        loader = MockLoader({
            'lib.html': XMLTemplate(source='''<div>
<span py:def="evenness(n)"
    ><py:if test="n % 2 == 0"
        >even</py:if
    ><py:else
        >odd</py:else
></span>
<py:def function="half_evenness(n)"
    >half of $n is ${evenness(n/2)}</py:def>
</div>'''),
            'tpl.html': XMLTemplate(source='''<div>
<py:import href="lib.html"
/><ul>
    <li py:for="i in range(4)">
        $i is ${lib.evenness(i)} ${lib.half_evenness(i)}
    </li>
</ul>
</div>''')
        })
        tpl = loader.import_('tpl.html')
        rsp = tpl(dict(name='Rick')).render()
        assert rsp == '''<div>
<ul>
    <li>
        0 is <span>even</span> half of 0 is <span>even</span>
    </li><li>
        1 is <span>odd</span> half of 1 is <span>odd</span>
    </li><li>
        2 is <span>even</span> half of 2 is <span>odd</span>
    </li><li>
        3 is <span>odd</span> half of 3 is <span>odd</span>
    </li>
</ul>
</div>''', rsp

    def test_include(self):
        '''Must NOT result in: NameError: global name 'name' is not defined'''
        loader = MockLoader({
            'included.html': XMLTemplate('<p>The included template must also '
                'access Kajiki globals and the template context: '
                '${value_of("name")}</p>\n'),
            'tpl.html': XMLTemplate('<html><body><p>This is the body</p>\n'
                '<py:include href="included.html"/></body></html>')
        })
        tpl = loader.import_('tpl.html')
        rsp = tpl(dict(name='Rick')).render()
        assert ('<html><body><p>This is the body</p>\n'
            '<p>The included template must also access Kajiki globals and '
            'the template context: Rick</p></body></html>' == rsp)


class TestExtends(TestCase):
    def test_basic(self):
        loader = MockLoader({
            'parent.html': XMLTemplate('''<div
><h1 py:def="header()">Header name=$name</h1
><h6 py:def="footer()">Footer</h6
><div py:def="body()">
id() = ${id()}
local.id() = ${local.id()}
self.id() = ${self.id()}
child.id() = ${child.id()}
</div><span py:def="id()">parent</span>
${header()}
${body()}
${footer()}
</div>'''),
            'mid.html': XMLTemplate('''<py:extends href="parent.html"
><span py:def="id()">mid</span
></py:extends>'''),
            'child.html': XMLTemplate('''<py:extends href="mid.html"
><span py:def="id()">child</span
><div py:def="body()">
<h2>Child Body</h2>
${parent.body()}
</div></py:extends>''')})
        tpl = loader.import_('child.html')
        rsp = tpl(dict(name='Rick')).render()
        assert rsp == '''<div>
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
</div>''', rsp

    def test_dynamic(self):
        loader = MockLoader({
            'parent0.html': XMLTemplate('<span>Parent 0</span>'),
            'parent1.html': XMLTemplate('<span>Parent 1</span>'),
            'child.html': XMLTemplate('''<div
><py:if test="p == 0"><py:extends href="parent0.html"/></py:if
><py:else><py:extends href="parent1.html"/></py:else
></div>
''')
        })
        tpl = loader.import_('child.html')
        rsp = tpl(dict(p=0)).render()
        assert rsp == '<div><span>Parent 0</span></div>', rsp
        rsp = tpl(dict(p=1)).render()
        assert rsp == '<div><span>Parent 1</span></div>', rsp

    def test_block(self):
        loader = MockLoader({
            'parent.html': XMLTemplate('''<div
><py:def function="greet(name)"
>Hello, $name!</py:def
><py:def function="sign(name)"
>Sincerely,<br/><em>$name</em></py:def
>${greet(to)}

<p py:block="body">It was good seeing you last Friday.
Thanks for the gift!</p>

${sign(from_)}
</div>'''),
            'child.html': XMLTemplate('''<py:extends href="parent.html"
><py:def function="greet(name)"
>Dear $name:</py:def
><py:block name="body">${parent_block()}
<p>And don't forget you owe me money!</p>
</py:block
></py:extends>
''')})
        parent = loader.import_('parent.html')
        rsp = parent({'to': 'Mark', 'from_': 'Rick'}).render()
        assert rsp == '''<div>Hello, Mark!

<p>It was good seeing you last Friday.
Thanks for the gift!</p>

Sincerely,<br/><em>Rick</em>
</div>''', rsp
        child = loader.import_('child.html')
        rsp = child({'to': 'Mark', 'from_': 'Rick'}).render()
        assert rsp == '''<div>Dear Mark:

<p>It was good seeing you last Friday.
Thanks for the gift!</p>
<p>And don't forget you owe me money!</p>


Sincerely,<br/><em>Rick</em>
</div>''', rsp


class TestClosure(TestCase):
    def test(self):
        perform('''<div
><py:def function="add(x)"
    ><py:def function="inner(y)"
        >${x+y}</py:def
    >${inner(x*2)}</py:def
>${add(5)}</div>''',   '<div>15</div>')


class TestPython(TestCase):
    def test_basic(self):
        perform('''<div
><?py
import os
?>${os.path.join('a', 'b', 'c')}</div>''',   '<div>a/b/c</div>')

    def test_indent(self):
        perform('''<div
><?py #
    import os
    import re
?>${os.path.join('a','b','c')}</div>''',   '<div>a/b/c</div>')

    def test_short(self):
        perform('''<div
><?py import os
?>${os.path.join('a', 'b', 'c')}</div>''',   '<div>a/b/c</div>')

    def test_mod(self):
        perform('''<div
><?py %import os
?><py:def function="test()"
>${os.path.join('a', 'b', 'c')}</py:def
>${test()}</div>''',   '<div>a/b/c</div>')


class TestComment(TestCase):
    def test_basic(self):
        perform('<div><!-- This comment is preserved. -->'
                '<!--! This comment is stripped. --></div>',
                '<div><!--  This comment is preserved.  --></div>')


class TestAttributes(TestCase):
    def test_basic(self):
        perform('''<div id="foo"/>''',   '<div id="foo"/>')

    def test_content(self):
        perform('''<div py:content="'foo'"/>''',   '<div>foo</div>')

    def test_replace(self):
        perform('''<div py:replace="'foo'"/>''',   'foo')

    def test_attrs(self):
        perform('<div py:attrs="dict(a=5, b=6)"/>',   '<div a="5" b="6"/>')
        perform('''<div py:attrs="[('a', 5), ('b', 6)]"/>''',
                '''<div a="5" b="6"/>''')
        perform('<div py:attrs="None"/>',   '<div/>')

    def test_strip(self):
        TPL = '<div><h1 py:strip="header">Header</h1></div>'
        perform(TPL, '<div>Header</div>', context=dict(header=True))
        perform(TPL, '<div><h1>Header</h1></div>', context=dict(header=False))
        TPL = '''<div><p py:strip="">It's...</p></div>'''
        perform(TPL, "<div>It's...</div>")

    def test_html_attrs(self):
        TPL = '<input type="checkbox" checked="$checked"/>'
        context0 = dict(checked=None)
        context1 = dict(checked=True)
        perform(TPL, '<input type="checkbox"/>', context0, mode='xml')
        perform(TPL, '<input checked="True" type="checkbox"/>',
                context1, mode='xml')
        perform(TPL, '<input type="checkbox">', context0, 'html')
        perform(TPL, '<input checked type="checkbox">',
                context1, 'html')
        perform(TPL, '<!DOCTYPE html><input checked type="checkbox">',
                context1, mode='html5', is_fragment=False)
        perform('<!DOCTYPE html>\n' + TPL,
                '<!DOCTYPE html><input checked type="checkbox">',
                context1, mode=None, is_fragment=False)

    def test_xml_namespaces(self):
        '''Namespaced attributes pass through.'''
        TPL = '<p xml:lang="en">English text</p>'
        perform(TPL, TPL, mode='xml')
        perform(TPL, TPL[:-4], mode='html')

    def test_escape_attr_values(self):
        '''Escape static and dynamic attribute values.'''
        context = dict(url='https://domain.com/path?a=1&b=2')
        source = '''<a title='"Ha!"' href="$url">Link</a>'''
        output = '<a href="https://domain.com/path?a=1&amp;b=2" ' \
                 'title="&quot;Ha!&quot;">Link</a>'
        perform(source, output, context, mode='html')
        perform(source, output, context, mode='xml')


class TestDebug(TestCase):
    def test_debug(self):
        loader = FileLoader(path=os.path.join(os.path.dirname(__file__),
                            'data'))
        tpl = loader.import_('debug.html')
        try:
            tpl().render()
            assert False, 'Should have raised ValueError'
        except ValueError:
            exc_info = sys.exc_info()
            stack = traceback.extract_tb(exc_info[2])
        # Verify we have stack trace entries in the template
        for fn, lno, func, line in stack:
            if fn.endswith('debug.html'):
                break
        else:
            assert False, 'Stacktrace is all python'


class TestPackageLoader(TestCase):
    def test_pkg_loader(self):
        loader = PackageLoader()
        loader.import_('kajiki.tests.data.debug')


class TestBuiltinFunctions(TestCase):
    def test_defined(self):
        perform('''<div>\
<div py:if="defined('albatross')">$albatross</div>\
<p py:if="defined('parrot')">$parrot</p></div>''',
expected_output='<div><p>Bereft of life, it rests in peace</p></div>',
context=dict(parrot='Bereft of life, it rests in peace'))

    def test_value_of(self):
        TPL = "<p>${value_of('albatross', 'Albatross!!!')}</p>"
        perform(TPL,
            expected_output="<p>It's</p>", context=dict(albatross="It's"))
        perform(TPL, expected_output="<p>Albatross!!!</p>")

    def test_literal(self):
        '''Escape by default; literal() marks as safe.'''
        context = dict(albatross="<em>Albatross!!!</em>")
        expected_output = "<p><em>Albatross!!!</em></p>"
        perform("<p>${literal(albatross)}</p>", expected_output, context)
        perform("<p>${Markup(albatross)}</p>", expected_output, context)
        perform("<p>$albatross</p>",
                "<p>&lt;em&gt;Albatross!!!&lt;/em&gt;</p>", context)
        from kajiki.util import literal
        markup = '<b>"&amp;"</b>'
        assert ''.join(list(literal(markup))) == markup


if __name__ == '__main__':
    main()
