import os
import xml.dom.minidom
from unittest import TestCase, main

from fastpt import v2 as fpt
from fastpt.v2.xml_template import XMLTemplate

DATA = os.path.join(
    os.path.dirname(__file__),
    'data')

class TestParser(TestCase):

    def test_parser(self):
        doc = fpt.xml_template._Parser('<string>', '''<?xml version="1.0"?>
<!DOCTYPE div PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
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
        doc = fpt.xml_template._Parser('<string>', '''<div
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
        fpt.xml_template.expand(doc)
        node = doc.childNodes[0]
        for tagname, attr in fpt.markup_template.QDIRECTIVES:
            if node.tagName == 'div':
                node = node.childNodes[0]
                continue
            assert node.tagName == tagname, '%s != %s' %(
                node.tagName, tagname)
            if attr:
                assert len(node.attributes) == 1
                assert node.hasAttribute(attr)
                assert node.getAttribute(attr) == tagname.split(':')[-1]
            else:
                assert len(node.attributes) == 0
            assert len(node.childNodes)==1
            node = node.childNodes[0]

class TestSimple(TestCase):

    def test_expr_name(self):
        tpl = XMLTemplate(source='<div>Hello, $name</div>')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '<div>Hello, Rick</div>', rsp

    def test_expr_braced(self):
        tpl = XMLTemplate(source='<div>Hello, ${name}</div>')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '<div>Hello, Rick</div>', rsp

    def test_expr_brace_complex(self):
        tpl = XMLTemplate(source="<div>Hello, ${{'name':name}['name']}</div>")
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '<div>Hello, Rick</div>', rsp

class TestSwitch(TestCase):

    def test_switch(self):
        tpl = XMLTemplate(source='''<div py:for="i in range(2)">
$i is <py:switch test="i % 2">
<py:case value="0">even</py:case>
<py:else>odd</py:else>
</py:switch></div>''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '''<div>
0 is even</div><div>
1 is odd</div>''', rsp

class TestFunction(TestCase):

    def test_function(self):
        tpl = XMLTemplate(source='''<div
><div py:def="evenness(n)"><py:if test="n % 2 == 0">even</py:if><py:else>odd</py:else></div>
<py:for each="i in range(2)">$i is ${evenness(i)}
</py:for
></div>''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '''<div>
0 is <div>even</div>
1 is <div>odd</div>
</div>''', rsp

class TestCall(TestCase):

    def test_call(self):
        tpl = XMLTemplate(source='''<div
><py:def function="quote(caller, speaker)"
><ul>
    <li py:for="i in range(2)">Quoth $speaker, ${caller(i)}</li>
</ul></py:def
><py:call args="n" function="quote(%caller, 'the raven')"
>Nevermore $n</py:call></div>''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '''<div><ul>
    <li>Quoth the raven, Nevermore 0</li><li>Quoth the raven, Nevermore 1</li>
</ul></div>''', rsp

class TestImport(TestCase):
    
    def test_import(self):
        loader = fpt.loader.MockLoader({
            'lib.html':XMLTemplate(source='''<div>
<span py:def="evenness(n)"
    ><py:if test="n % 2 == 0"
        >even</py:if
    ><py:else
        >odd</py:else
></span>
<py:def function="half_evenness(n)"
    >half of $n is ${evenness(n/2)}</py:def>
</div>'''),
            'tpl.html':XMLTemplate(source='''<div>
<py:import href="lib.html" alias="simple_function"
/><ul>
    <li py:for="i in range(4)">
        $i is ${simple_function.evenness(i)} ${simple_function.half_evenness(i)}
    </li>
</ul>
</div>''')
            })
        tpl = loader.import_('tpl.html')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '''<div>
<ul>
    <li>
        0 is <span>even</span> half of 0 is <span>even</span>
    </li><li>
        1 is <span>odd</span> half of 1 is <span>even</span>
    </li><li>
        2 is <span>even</span> half of 2 is <span>odd</span>
    </li><li>
        3 is <span>odd</span> half of 3 is <span>odd</span>
    </li>
</ul>
</div>''', rsp

    def test_import_auto(self):
        loader = fpt.loader.MockLoader({
            'lib.html':XMLTemplate(source='''<div>
<span py:def="evenness(n)"
    ><py:if test="n % 2 == 0"
        >even</py:if
    ><py:else
        >odd</py:else
></span>
<py:def function="half_evenness(n)"
    >half of $n is ${evenness(n/2)}</py:def>
</div>'''),
            'tpl.html':XMLTemplate(source='''<div>
<py:import href="lib.html"
/><ul>
    <li py:for="i in range(4)">
        $i is ${lib.evenness(i)} ${lib.half_evenness(i)}
    </li>
</ul>
</div>''')
            })
        tpl = loader.import_('tpl.html')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '''<div>
<ul>
    <li>
        0 is <span>even</span> half of 0 is <span>even</span>
    </li><li>
        1 is <span>odd</span> half of 1 is <span>even</span>
    </li><li>
        2 is <span>even</span> half of 2 is <span>odd</span>
    </li><li>
        3 is <span>odd</span> half of 3 is <span>odd</span>
    </li>
</ul>
</div>''', rsp

    def test_include(self):
        loader = fpt.loader.MockLoader({
                'hdr.html':XMLTemplate('<h1>Header</h1>\n'),
                'tpl.html':XMLTemplate('''<html><body>
<py:include href="hdr.html"/>
<p>This is the body</p>
</body></html>''')
                })
        tpl = loader.import_('tpl.html')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '''<html><body>
<h1>Header</h1>
<p>This is the body</p>
</body></html>''', rsp

class TestExtends(TestCase):

    def test_basic(self):
        loader = fpt.loader.MockLoader({
                'parent.html':XMLTemplate('''<div
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
                'mid.html':XMLTemplate('''<py:extends href="parent.html"
><span py:def="id()">mid</span
></py:extends>'''),
                'child.html':XMLTemplate('''<py:extends href="mid.html"
><span py:def="id()">child</span
><div py:def="body()">
<h2>Child Body</h2>
${parent.body()}
</div></py:extends>''')})
        tpl = loader.import_('child.html')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp=='''<div>
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
        loader = fpt.loader.MockLoader({
                'parent0.html':XMLTemplate('<span>Parent 0</span>'),
                'parent1.html':XMLTemplate('<span>Parent 1</span>'),
                'child.html':XMLTemplate('''<div
><py:if test="p == 0"><py:extends href="parent0.html"/></py:if
><py:else><py:extends href="parent1.html"/></py:else
></div>
''')
                })
        tpl = loader.import_('child.html')
        rsp = tpl(dict(p=0)).__fpt__.render()
        assert rsp == '<div><span>Parent 0</span></div>', rsp
        rsp = tpl(dict(p=1)).__fpt__.render()
        assert rsp == '<div><span>Parent 1</span></div>', rsp

    def test_block(self):
        loader = fpt.loader.MockLoader({
                'parent.html':XMLTemplate('''<div
><py:def function="greet(name)"
>Hello, $name!</py:def
><py:def function="sign(name)"
>Sincerely,<br/><em>$name</em></py:def
>${greet(to)}

<p py:block="body">It was good seeing you last Friday.
Thanks for the gift!</p>

${sign(from_)}
</div>'''),
                'child.html':XMLTemplate('''<py:extends href="parent.html"
><py:def function="greet(name)"
>Dear $name:</py:def
><py:block name="body">${parent_block()}
<p>And don't forget you owe me money!</p>
</py:block
></py:extends>
''')})
        parent = loader.import_('parent.html')
        rsp = parent({'to':'Mark', 'from_':'Rick'}).__fpt__.render()
        assert rsp == '''<div>Hello, Mark!

<p>It was good seeing you last Friday.
Thanks for the gift!</p>

Sincerely,<br/><em>Rick</em>
</div>''', rsp
        child = loader.import_('child.html')
        rsp = child({'to':'Mark', 'from_':'Rick'}).__fpt__.render()
        assert rsp=='''<div>Dear Mark:

<p>It was good seeing you last Friday.
Thanks for the gift!</p>
<p>And don't forget you owe me money!</p>


Sincerely,<br/><em>Rick</em>
</div>''', rsp

if __name__ == '__main__':
    main()
