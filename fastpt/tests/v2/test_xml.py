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
        assert rsp == '<div >Hello, Rick</div>', rsp

    def test_expr_braced(self):
        tpl = XMLTemplate(source='<div>Hello, ${name}</div>')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '<div >Hello, Rick</div>', rsp

    def test_expr_brace_complex(self):
        tpl = XMLTemplate(source="<div>Hello, ${{'name':name}['name']}\n</div>")
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '<div >Hello, Rick</div>', rsp

if __name__ == '__main__':
    main()
