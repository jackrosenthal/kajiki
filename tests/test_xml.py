import os
import sys
import traceback
import xml.dom.minidom
from io import BytesIO
from unittest import TestCase

import pytest

import kajiki
from kajiki import FileLoader, MockLoader, PackageLoader, XMLTemplate, i18n
from kajiki.ir import TranslatableTextNode
from kajiki.template import KajikiSyntaxError
from kajiki.xml_template import (
    XMLTemplateCompileError,
    XMLTemplateParseError,
    _Compiler,
    _Parser,
)

DATA = os.path.join(os.path.dirname(__file__), "data")


class TestParser(TestCase):
    def test_parser(self):
        doc = kajiki.xml_template._Parser(
            "<string>",
            """<?xml version="1.0"?>
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
</div>""",
        ).parse()
        xml.dom.minidom.parseString(doc.toxml().encode("utf-8"))


class TestExpand(TestCase):
    def test_expand(self):
        doc = kajiki.xml_template._Parser(
            "<string>",
            """<div
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
        py:extends="extends">Foo</div>""",
        ).parse()
        doc = kajiki.xml_template._DomTransformer(doc).transform()
        node = doc.childNodes[0]
        for tagname, attr in kajiki.markup_template.QDIRECTIVES:
            if node.tagName == "div":
                node = node.childNodes[0]
                continue
            assert node.tagName == tagname, f"{node.tagName} != {tagname}"
            if attr:
                if node.tagName != "py:case":
                    assert len(node.attributes) == 1, node.attributes.items()
                    assert node.hasAttribute(attr)
                    assert node.getAttribute(attr) == tagname.split(":")[-1]
                else:
                    assert len(node.attributes) == 2
            else:
                assert len(node.attributes) == 0
            assert len(node.childNodes) == 1
            node = node.childNodes[0]


def perform(source, expected_output, context=None, **options):
    context = context or {"name": "Rick"}
    tpl = XMLTemplate(source, **options)
    rsp = tpl(context).render()
    assert isinstance(rsp, str), "render() must return a string."
    assert rsp == expected_output, (rsp, expected_output)
    return tpl


class TestSimple(TestCase):
    def test_empty_attr(self):
        perform(
            source='<img src="/foo/bar.baz.gif" alt="" />',
            mode="html",
            expected_output='<img alt="" src="/foo/bar.baz.gif">',
        )

    def test_pre_whitespace(self):
        src = '<pre name="foo">\nHey there.  \n\n    I am indented.\n' "</pre>"
        perform(src, src, mode="html")
        perform(src, src, mode="xml")

    def test_textarea_whitespace(self):
        src = '<textarea name="foo">\nHey there.  \n\n    I am indented.\n' "</textarea>"
        perform(src, src, mode="html")
        perform(src, src, mode="xml")

    def test_script(self):
        "Always close script tags, even in xml mode."
        source = '<html><script src="public"/></html>'
        output = '<html><script src="public"></script></html>'
        perform(source, output, mode="html")
        perform(source, output, mode="xml")

    def test_script_escaping(self):
        """In HTML script and style tags are automatically CDATA; in XML they
        must be explicitly be made so.
        """
        script = 'if (1 < 2) { doc.write("<p>Offen&nbsp;bach</p>"); }\n'
        src = f"<script><![CDATA[\n{script}]]></script>"
        perform(src, mode="html", expected_output=f"<script>\n{script}</script>")
        perform(src, f"<script>/*<![CDATA[*/\n{script}/*]]>*/</script>", mode="xml")

    def test_style_escaping(self):
        style = "html > body { display: none; }\n"
        src = f"<style><![CDATA[\n{style}]]></style>"
        perform(src, f"<style>/*<![CDATA[*/\n{style}/*]]>*/</style>", mode="xml")
        perform(src, f"<style>\n{style}</style>", mode="html")

    def test_script_variable(self):
        """Interpolate variables inside <script> tags"""
        src = "<script><![CDATA[ $name ]]></script>"
        perform(src, "<script>/*<![CDATA[*/ Rick /*]]>*/</script>", mode="xml")
        perform(src, "<script> Rick </script>", mode="html")

    def test_cdata_disabled(self):
        src = "<script> $name </script>"
        perform(src, "<script> Rick </script>", mode="xml", cdata_scripts=False)
        perform(src, "<script> Rick </script>", mode="html", cdata_scripts=False)

    def test_cdata_escaping(self):
        src = """<myxml><data><![CDATA[&gt;&#240; $name]]></data></myxml>"""
        perform(src, "<myxml><data><![CDATA[&gt;&#240; Rick]]></data></myxml>", mode="xml")
        perform(src, "<myxml><data><![CDATA[&gt;&#240; Rick]]></data></myxml>", mode="html")

    def test_cdata_escaping_mixed(self):
        src = """<myxml><data><![CDATA[&gt;&#240; $name]]> &gt;</data></myxml>"""
        perform(
            src,
            "<myxml><data><![CDATA[&gt;&#240; Rick]]> &gt;</data></myxml>",
            mode="xml",
        )
        perform(
            src,
            "<myxml><data><![CDATA[&gt;&#240; Rick]]> &gt;</data></myxml>",
            mode="html",
        )

    def test_script_commented_cdata(self):
        script = 'if (1 < 2) { doc.write("<p>Offen&nbsp;bach</p>"); }\n'
        src = f"<script>/*<![CDATA[*/\n{script}/*]]>*/</script>"
        perform(
            src,
            mode="html",
            expected_output=f"<script>/**/\n{script}/**/</script>",
        )
        perform(
            src,
            f"<script>/*<![CDATA[*//**/\n{script}/**//*]]>*/</script>",
            mode="xml",
        )

    def test_escape_dollar(self):
        perform("<div>$$</div>", "<div>$</div>")

    def test_escape_dollar_followed_by_dollar(self):
        perform("<div>$$$</div>", "<div>$$</div>")

    def test_double_escape_dollar(self):
        perform("<div>$$$$</div>", "<div>$$</div>")

    def test_preserve_dollar_not_variable_brace(self):
        perform("<div>$(</div>", "<div>$(</div>")
        perform("<div>$.</div>", "<div>$.</div>")

    def test_expr_name(self):
        perform("<div>Hello, $name</div>", "<div>Hello, Rick</div>")

    def test_expr_braced(self):
        perform("<div>Hello, ${name}</div>", "<div>Hello, Rick</div>")

    def test_expr_brace_complex(self):
        perform("<div>Hello, ${{'name':name}['name']}</div>", "<div>Hello, Rick</div>")

    def test_expr_multiline(self):
        perform(
            """<div>Hello, ${{'name': 'Rick',
                                 'age': 26}['name']}</div>""",
            "<div>Hello, Rick</div>",
        )

    def test_expr_multiline_and_indentation_error(self):
        with pytest.raises(XMLTemplateCompileError) as e:
            XMLTemplate(
                """<div>Hello, ${ 'pippo' +
                'baudo'}</div>"""
            )().render()
        assert "`'pippo' +\n                'baudo'`" in str(e.value)
        assert "Hello" in str(e.value)
        assert "baudo" in str(e.value)

    def test_expr_multiline_cdata(self):
        perform(
            """<script><![CDATA[Hello, ${{'name': 'Rick',
                                 'age': 26}['name']}]]></script>""",
            "<script>/*<![CDATA[*/Hello, Rick/*]]>*/</script>",
        )

    def test_jquery_call_is_not_expr(self):
        """Ensure we handle '$(' as a text literal, since it cannot be a
        valid variable sequence.  This simplifies, for example,
        templates containing inline scripts with jQuery calls
        which otherwise have to be written '$$(...'
        """
        js = "$(function () { alert('.ready()'); });"
        src = "<html><pre>" + js + "</pre><script>" + js + "</script></html>"
        out = "<html><pre>" + js + "</pre><script>/*<![CDATA[*/" + js + "/*]]>*/</script></html>"
        perform(src, out)

    def test_jquery_shortcut_is_not_expr(self):
        """Ensure we handle '$.' as a text literal in script blocks"""

        js = "$.extend({}, {foo: 'bar'})"
        src = "<html><pre>" + js + "</pre><script>" + js + "</script></html>"
        out = "<html><pre>" + js + "</pre><script>/*<![CDATA[*/" + js + "/*]]>*/</script></html>"
        perform(src, out)

    def test_xml_entities(self):
        source = "<div>Cookies &amp; Cream</div>"
        perform(source, source)

    def test_html_entities(self):
        source = "<div>Spam&nbsp;Spam &lt; Spam &gt; Spam &hellip;</div>"
        output = "<div>Spam\xa0Spam &lt; Spam &gt; Spam \u2026</div>"
        assert chr(32) in output  # normal space
        assert chr(160) in output  # non breaking space
        perform(source, output)


class TestSwitch(TestCase):
    def test_switch(self):
        perform(
            """<div py:for="i in range(2)">
$i is <py:switch test="i % 2">
<py:case value="0">even</py:case>
<py:else>odd</py:else>
</py:switch></div>""",
            """<div>
0 is even</div><div>
1 is odd</div>""",
        )

    def test_switch_multi(self):
        perform(
            """<div py:for="i in range(8)">
$i is <py:switch test="i % 4">
<py:case value="0">ok</py:case>
<py:case value="1">nearly</py:case>
<py:else>nope</py:else>
</py:switch></div>""",
            """<div>
0 is ok</div><div>
1 is nearly</div><div>
2 is nope</div><div>
3 is nope</div><div>
4 is ok</div><div>
5 is nearly</div><div>
6 is nope</div><div>
7 is nope</div>""",
        )

    def test_case_elem(self):
        perform(
            """<div>
    <py:switch test="True">
      <span py:case="0 == 1">0</span>
      <span py:case="1 == 1">1</span>
      <span py:else="">2</span>
    </py:switch>
  </div>""",
            "<div>\n    <span>1</span>\n  </div>",
        )

    def test_switch_div(self):
        with pytest.raises(XMLTemplateCompileError) as e:
            perform(
                """
        <div class="test" py:switch="5 == 3">
            <p py:case="True">True</p>
            <p py:else="">False</p>
        </div>""",
                "<div><div>False</div></div>",
            )
        assert "py:switch directive can only contain py:case and py:else nodes" in str(e)


class TestMatch:
    def setup_class(self):
        if sys.version_info < (3, 10):
            pytest.skip("pep622 unavailable before python3.10")

    def test_match(self):
        perform(
            """<div py:for="i in range(2)">
$i is <py:match on="i % 2">
<py:case match="0">even</py:case>
<py:case match="_">odd</py:case>
</py:match></div>""",
            """<div>
0 is even</div><div>
1 is odd</div>""",
        )

    def test_match_div(self):
        with pytest.raises(
            XMLTemplateCompileError,
            match="case must have either value or match attribute, the former for py:switch, the latter for py:match",
        ):
            perform(
                """
        <div class="test" py:match="5 == 3">
            <p py:case="True">True</p>
            <p py:case="_">False</p>
        </div>""",
                "<div><div>False</div></div>",
            )

    def test_match_aliens(self):
        with pytest.raises(
            XMLTemplateCompileError,
            match="py:match directive can only contain py:case",
        ):
            perform(
                """<div py:for="i in range(2)">
$i is <py:match on="i % 2">
alien
<py:case match="0">even</py:case>
<py:case match="_">odd</py:case>
</py:match></div>""",
                """<div>
0 is even</div><div>
1 is odd</div>""",
            )


class TestElse(TestCase):
    def test_pyif_pyelse(self):
        with pytest.raises(XMLTemplateCompileError) as e:
            perform(
                """
            <div>
                <div py:if="False">True</div>
                <py:else>False</py:else>
            </div>""",
                """<div>False</div>""",
            )
        assert "py:else directive must be inside a py:switch or directly after py:if" in str(e)

    def test_pyiftag_pyelse_continuation(self):
        perform(
            """<div><div py:if="False">True</div><py:else>False</py:else></div>""",
            """<div>False</div>""",
        )

    def test_pyif_pyelse_continuation(self):
        perform(
            """<div><py:if test="False">True</py:if><py:else>False</py:else></div>""",
            """<div>False</div>""",
        )


class TestWith(TestCase):
    def test_with(self):
        perform(
            """<div py:with="a='foo'">
<div>$a</div>
<div py:with="a=5">$a</div>
<div>$a</div>
</div>""",
            """<div>
<div>foo</div>
<div>5</div>
<div>foo</div>
</div>""",
        )

    def test_with_multiple(self):
        perform(
            """<div py:with="a='foo';b=3">
<div>$a - $b</div>
<div py:with="a=5;b=1">$a - $b</div>
<div>$a - $b</div>
</div>""",
            """<div>
<div>foo - 3</div>
<div>5 - 1</div>
<div>foo - 3</div>
</div>""",
        )

    def test_with_multiple_and_whitespace(self):
        perform(
            """<div py:with="a = 'foo';
                                 b = 3">$a - $b</div>""",
            "<div>foo - 3</div>",
        )

    def test_with_trailing_semicolon(self):
        perform("""<div py:with="a = 'foo';">$a</div>""", "<div>foo</div>")

    def test_with_ordered_multiple(self):
        perform(
            """<div py:with="a='foo';b=a * 2;c=b[::-1];d=c[:3]">""" """$a $b $c $d</div>""",
            "<div>foo foofoo oofoof oof</div>",
        )

    def test_with_multiple_with_embedded_semicolons(self):
        perform("""<div py:with="a=';';b='-)'">$a$b</div>""", "<div>;-)</div>")

    def test_standalone(self):
        perform(
            """<div><py:with vars="a=';';b='-)'">$a$b</py:with></div>""",
            "<div>;-)</div>",
        )


class TestFunction(TestCase):
    def test_function(self):
        perform(
            """<div
><div py:def="evenness(n)"
><py:if test="n % 2 == 0">even</py:if><py:else>odd</py:else></div>
<py:for each="i in range(2)">$i is ${evenness(i)}
</py:for
></div>""",
            """<div>
0 is <div>even</div>
1 is <div>odd</div>
</div>""",
        )

    def test_empty_function(self):
        """Do not crash if a function has no content."""
        perform('<div><py:def function="bruhaha()"></py:def></div>', "<div></div>")

    def test_function_in_attr(self):
        """Attribute value with a function call."""
        perform(
            """<div
><py:def function="attrtest(n, sz=16)">text/$sz/$n</py:def><img
src="${attrtest(name)}"/></div>""",
            '<div><img src="text/16/Rick"/></div>',
        )


class TestCall(TestCase):
    def test_call(self):
        perform(
            """<div
><py:def function="quote(caller, speaker)"
><ul>
    <li py:for="i in range(2)">Quoth $speaker, ${caller(i)}</li>
</ul></py:def
><py:call args="n" function="quote(%caller, 'the raven')"
>Nevermore $n</py:call></div>""",
            """<div><ul>
    <li>Quoth the raven, Nevermore 0</li><li>Quoth the raven, Nevermore 1</li>
</ul></div>""",
        )


class TestImport(TestCase):
    def test_import(self):
        loader = MockLoader(
            {
                "lib.html": XMLTemplate(
                    source="""<div>
<span py:def="evenness(n)"
    ><py:if test="n % 2 == 0"
        >even</py:if
    ><py:else
        >odd</py:else
></span>
<py:def function="half_evenness(n)"
    >half of $n is ${evenness(n/2)}</py:def>
</div>"""
                ),
                "tpl.html": XMLTemplate(
                    source="""<div>
<py:import href="lib.html" alias="simple_function"
/><ul>
    <li py:for="i in range(4)">
        $i is ${simple_function.evenness(i)} ${simple_function.half_evenness(i)}
    </li>
</ul>
</div>"""
                ),
            }
        )
        tpl = loader.import_("tpl.html")
        rsp = tpl({"name": "Rick"}).render()
        assert (
            rsp
            == """<div>
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
</div>"""
        ), rsp

    def test_import_auto(self):
        loader = MockLoader(
            {
                "lib.html": XMLTemplate(
                    source="""<div>
<span py:def="evenness(n)"
    ><py:if test="n % 2 == 0"
        >even</py:if
    ><py:else
        >odd</py:else
></span>
<py:def function="half_evenness(n)"
    >half of $n is ${evenness(n/2)}</py:def>
</div>"""
                ),
                "tpl.html": XMLTemplate(
                    source="""<div>
<py:import href="lib.html"
/><ul>
    <li py:for="i in range(4)">
        $i is ${lib.evenness(i)} ${lib.half_evenness(i)}
    </li>
</ul>
</div>"""
                ),
            }
        )
        tpl = loader.import_("tpl.html")
        rsp = tpl({"name": "Rick"}).render()
        assert (
            rsp
            == """<div>
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
</div>"""
        ), rsp

    def test_include(self):
        """Must NOT result in: NameError: global name 'name' is not defined"""
        loader = MockLoader(
            {
                "included.html": XMLTemplate(
                    "<p>The included template must also "
                    "access Kajiki globals and the template context: "
                    '${value_of("name")}</p>\n'
                ),
                "tpl.html": XMLTemplate(
                    "<html><body><p>This is the body</p>\n" '<py:include href="included.html"/></body></html>'
                ),
            }
        )
        tpl = loader.import_("tpl.html")
        rsp = tpl({"name": "Rick"}).render()
        assert (
            rsp == "<html><body><p>This is the body</p>\n"
            "<p>The included template must also access Kajiki globals and "
            "the template context: Rick</p></body></html>"
        )

    def test_include_html5(self):
        """Should not have DOCTYPE"""

        class XMLSourceLoader(MockLoader):
            """Fakes a FileLoader, but with source in a lookup table.

            It differs from MockLoader because MockLoader doesn't
            create the template on load, it's already pre-instantiated
            by the user of the MockLoader
            """

            def __init__(self, sources):
                self.sources = sources
                super().__init__({})

            def _load(self, name, encoding="utf-8", **kwargs):
                del encoding
                return XMLTemplate(source=self.sources[name], mode="html5", **kwargs)

        loader = XMLSourceLoader(
            {
                "included.html": "<p>The included template must also "
                "access Kajiki globals and the template context: "
                '${value_of("name")}</p>\n',
                "tpl.html": "<html><body><p>This is the body</p>\n" '<py:include href="included.html"/></body></html>',
            }
        )
        tpl = loader.import_("tpl.html")
        rsp = tpl({"name": "Rick"}).render()
        assert (
            rsp == "<!DOCTYPE html>\n<html><body><p>This is the body</p>\n"
            "<p>The included template must also access Kajiki globals and "
            "the template context: Rick</p></body></html>"
        ), rsp


class TestExtends(TestCase):
    def test_basic(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate(
                    """<div
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
</div>"""
                ),
                "mid.html": XMLTemplate(
                    """<py:extends href="parent.html"
><span py:def="id()">mid</span
></py:extends>"""
                ),
                "child.html": XMLTemplate(
                    """<py:extends href="mid.html"
><span py:def="id()">child</span
><div py:def="body()">
<h2>Child Body</h2>
${parent.body()}
</div></py:extends>"""
                ),
            }
        )
        tpl = loader.import_("child.html")
        rsp = tpl({"name": "Rick"}).render()
        assert (
            rsp
            == """<div>
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
</div>"""
        ), rsp

    def test_dynamic(self):
        loader = MockLoader(
            {
                "parent0.html": XMLTemplate("<span>Parent 0</span>"),
                "parent1.html": XMLTemplate("<span>Parent 1</span>"),
                "child.html": XMLTemplate(
                    """<div
><py:if test="p == 0"><py:extends href="parent0.html"/></py:if
><py:else><py:extends href="parent1.html"/></py:else
></div>
"""
                ),
            }
        )
        tpl = loader.import_("child.html")
        rsp = tpl({"p": 0}).render()
        assert rsp == "<div><span>Parent 0</span></div>", rsp
        rsp = tpl({"p": 1}).render()
        assert rsp == "<div><span>Parent 1</span></div>", rsp

    def test_block(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate(
                    """<div
><py:def function="greet(name)"
>Hello, $name!</py:def
><py:def function="sign(name)"
>Sincerely,<br/><em>$name</em></py:def
>${greet(to)}

<p py:block="body">It was good seeing you last Friday.
Thanks for the gift!</p>

${sign(from_)}
</div>"""
                ),
                "child.html": XMLTemplate(
                    """<py:extends href="parent.html"
><py:def function="greet(name)"
>Dear $name:</py:def
><py:block name="body">${parent_block()}
<p>And don't forget you owe me money!</p>
</py:block
></py:extends>
"""
                ),
            }
        )
        parent = loader.import_("parent.html")
        rsp = parent({"to": "Mark", "from_": "Rick"}).render()
        assert (
            rsp
            == """<div>Hello, Mark!

<p>It was good seeing you last Friday.
Thanks for the gift!</p>

Sincerely,<br/><em>Rick</em>
</div>"""
        ), rsp
        child = loader.import_("child.html")
        rsp = child({"to": "Mark", "from_": "Rick"}).render()
        assert (
            rsp
            == """<div>Dear Mark:

<p>It was good seeing you last Friday.
Thanks for the gift!</p>
<p>And don't forget you owe me money!</p>


Sincerely,<br/><em>Rick</em>
</div>"""
        ), rsp

    def test_autoblocks(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate(
                    """
<html py:strip="">
<head></head>
<body>
    <p py:block="body">It was good seeing you last Friday.
    Thanks for the gift!</p>
</body>
</html>"""
                ),
                "child.html": XMLTemplate(
                    """
<html>
<py:extends href="parent.html"/>
<body><em>Great conference this weekend!</em></body>
</html>""",
                    autoblocks=["body"],
                ),
            }
        )

        parent = loader.import_("parent.html")
        rsp = parent().render()
        assert (
            rsp
            == """
<head/>
<body>
    <p>It was good seeing you last Friday.
    Thanks for the gift!</p>
</body>
"""
        ), rsp

        child = loader.import_("child.html")
        rsp = child().render()
        assert (
            rsp
            == """<html>

<head/>
<body>
    <em>Great conference this weekend!</em>
</body>


</html>"""
        ), rsp

    def test_autoblocks_disabling(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate(
                    """
<html py:strip="">
<head></head>
<body py:autoblock="False">
    <p py:block="body">It was good seeing you last Friday.
    Thanks for the gift!</p>
</body>
</html>""",
                    autoblocks=["body"],
                ),
                "child.html": XMLTemplate(
                    """
<html>
<py:extends href="parent.html"/>
<body><em>Great conference this weekend!</em></body>
</html>""",
                    autoblocks=["body"],
                ),
            }
        )

        parent = loader.import_("parent.html")
        rsp = parent().render()
        assert (
            rsp
            == """
<head/>
<body>
    <p>It was good seeing you last Friday.
    Thanks for the gift!</p>
</body>
"""
        ), rsp

        child = loader.import_("child.html")
        rsp = child().render()
        assert (
            rsp
            == """<html>

<head/>
<body>
    <em>Great conference this weekend!</em>
</body>


</html>"""
        ), rsp


class TestClosure(TestCase):
    def test(self):
        perform(
            """<div
><py:def function="add(x)"
    ><py:def function="inner(y)"
        >${x+y}</py:def
    >${inner(x*2)}</py:def
>${add(5)}</div>""",
            "<div>15</div>",
        )


class TestPython(TestCase):
    def test_basic(self):
        perform(
            """<div
><?py
import os
?>${os.path.join('a', 'b', 'c')}</div>""",
            "<div>a/b/c</div>",
        )

    def test_indent(self):
        perform(
            """<div
><?py #
    import os
    import re
?>${os.path.join('a','b','c')}</div>""",
            "<div>a/b/c</div>",
        )

    def test_short(self):
        perform(
            """<div
><?py import os
?>${os.path.join('a', 'b', 'c')}</div>""",
            "<div>a/b/c</div>",
        )

    def test_mod(self):
        perform(
            """<div
><?py %import os
?><py:def function="test()"
>${os.path.join('a', 'b', 'c')}</py:def
>${test()}</div>""",
            "<div>a/b/c</div>",
        )


class TestComment(TestCase):
    def test_basic(self):
        perform(
            "<div><!-- This comment is preserved. -->" "<!--! This comment is stripped. --></div>",
            "<div><!--  This comment is preserved.  --></div>",
        )


class TestAttributes(TestCase):
    def test_basic(self):
        perform("""<div id="foo"/>""", '<div id="foo"/>')

    def test_content(self):
        perform("""<div py:content="'foo'"/>""", "<div>foo</div>")

    def test_replace(self):
        perform("""<div py:replace="'foo'"/>""", "foo")

    def test_attrs(self):
        perform('<div py:attrs="dict(a=5, b=6)"/>', '<div a="5" b="6"/>')
        perform("""<div py:attrs="[('a', 5), ('b', 6)]"/>""", """<div a="5" b="6"/>""")
        perform('<div py:attrs="None"/>', "<div/>")
        perform('<div py:attrs="dict(checked=True)"/>', '<div checked="checked"/>')
        perform('<div py:attrs="dict(checked=False)"/>', "<div/>")
        perform('<div py:attrs="dict(checked=None)"/>', "<div/>")

    def test_strip(self):
        tpl = '<div><h1 py:strip="header">Header</h1></div>'
        perform(tpl, "<div>Header</div>", context={"header": True})
        perform(tpl, "<div><h1>Header</h1></div>", context={"header": False})
        tpl = """<div><p py:strip="">It's...</p></div>"""
        perform(tpl, "<div>It's...</div>")

    def test_html_attrs(self):
        tpl = '<input type="checkbox" checked="$checked"/>'
        context0 = {"checked": None}
        context1 = {"checked": True}
        perform(tpl, '<input type="checkbox"/>', context0, mode="xml")
        perform(tpl, '<input checked="True" type="checkbox"/>', context1, mode="xml")
        perform(tpl, '<input type="checkbox">', context0, mode="html")
        perform(tpl, '<input checked type="checkbox">', context1, mode="html")
        perform(
            tpl,
            '<!DOCTYPE html>\n<input checked type="checkbox">',
            context1,
            mode="html5",
            is_fragment=False,
        )
        perform(
            "<!DOCTYPE html>\n" + tpl,
            '<!DOCTYPE html>\n<input checked type="checkbox">',
            context1,
            mode=None,
            is_fragment=False,
        )

    def test_xml_namespaces(self):
        """Namespaced attributes pass through."""
        tpl = '<p xml:lang="en">English text</p>'
        perform(tpl, tpl, mode="xml")
        perform(tpl, tpl, mode="html")

    def test_escape_attr_values(self):
        """Escape static and dynamic attribute values."""
        context = {"url": "https://domain.com/path?a=1&b=2"}
        source = """<a title='"Ha!"' href="$url">Link</a>"""
        output = '<a href="https://domain.com/path?a=1&amp;b=2" ' 'title="&quot;Ha!&quot;">Link</a>'
        perform(source, output, context, mode="html")
        perform(source, output, context, mode="xml")


class TestDebug(TestCase):
    def test_debug(self):
        loader = FileLoader(path=os.path.join(os.path.dirname(__file__), "data"))
        tpl = loader.import_("debug.html")
        with pytest.raises(ValueError, match="Test error") as exc_info:
            tpl().render()

        # Verify we have stack trace entries in the template
        for tb_entry in exc_info.traceback:
            if tb_entry.path.name == "debug.html":
                break
        else:
            pytest.fail("Stacktrace is all python")


class TestPackageLoader(TestCase):
    def test_pkg_loader(self):
        loader = PackageLoader()
        loader.import_("kajiki_test_data.debug")


class TestBuiltinFunctions(TestCase):
    def test_defined(self):
        perform(
            """<div>\
<div py:if="defined('albatross')">$albatross</div>\
<p py:if="defined('parrot')">$parrot</p></div>""",
            expected_output="<div><p>Bereft of life, it rests in peace</p></div>",
            context={"parrot": "Bereft of life, it rests in peace"},
        )

    def test_value_of(self):
        tpl = "<p>${value_of('albatross', 'Albatross!!!')}</p>"
        perform(tpl, expected_output="<p>It's</p>", context={"albatross": "It's"})
        perform(tpl, expected_output="<p>Albatross!!!</p>")

    def test_literal(self):
        """Escape by default; literal() marks as safe."""
        context = {"albatross": "<em>Albatross!!!</em>"}
        expected_output = "<p><em>Albatross!!!</em></p>"
        perform("<p>${literal(albatross)}</p>", expected_output, context)
        perform("<p>${Markup(albatross)}</p>", expected_output, context)
        perform("<p>$albatross</p>", "<p>&lt;em&gt;Albatross!!!&lt;/em&gt;</p>", context)
        from kajiki.util import literal

        markup = '<b>"&amp;"</b>'
        assert "".join(list(literal(markup))) == markup


class TestTranslation(TestCase):
    def test_scripts_non_translatable(self):
        src = "<xml><div>Hi</div><script>hello world</script>" "<style>hello style</style></xml>"
        doc = _Parser("<string>", src).parse()

        for n in _Compiler("<string>", doc).compile():
            text = getattr(n, "text", "")
            if text in ("hello world", "hello style"):
                assert not isinstance(n, TranslatableTextNode)

        for n in _Compiler("<string>", doc, cdata_scripts=False).compile():
            text = getattr(n, "text", "")
            if text in ("hello world", "hello style"):
                assert not isinstance(n, TranslatableTextNode)

    def test_extract_translate(self):
        src = """<xml><div>Hi</div><p>

        Hello
        World</p></xml>"""
        expected = {
            False: """<xml><div>TRANSLATED(Hi)</div><p>\n\n        TRANSLATED(Hello
        World)</p></xml>""",
            True: """<xml><div>TRANSLATED(Hi)</div><p>TRANSLATED(Hello
        World)</p></xml>""",
        }

        for strip_text in (False, True):
            # Build translation table
            messages = {}
            for _, _, msgid, _ in i18n.extract(BytesIO(src.encode("utf-8")), None, None, {"strip_text": strip_text}):
                messages[msgid] = f"TRANSLATED({msgid})"

            # Provide a fake translation function
            default_gettext = i18n.gettext
            i18n.gettext = messages.__getitem__
            try:
                perform(src, expected[strip_text], strip_text=strip_text)
            finally:
                i18n.gettext = default_gettext

    def test_extract_python_inside(self):
        src = """<xml><div>${_('hi')}</div><p>

        Hello
        World</p></xml>"""
        expected = """<xml><div>xi</div><p>\n\n        TRANSLATED(Hello
        World)</p></xml>"""

        # Build translation table
        messages = {"hi": "xi"}
        for _, _, msgid, _ in i18n.extract(BytesIO(src.encode("utf-8")), [], None, {"extract_python": True}):
            messages[msgid] = f"TRANSLATED({msgid})"

        # Provide a fake translation function
        default_gettext = i18n.gettext
        i18n.gettext = lambda s: messages[s]
        try:
            perform(src, expected)
        finally:
            i18n.gettext = default_gettext

    def test_extract_python_inside_invalid(self):
        src = """<xml><div>${_('hi' +)}</div></xml>"""
        with pytest.raises(XMLTemplateCompileError, match=r"_\('hi' \+\)"):
            list(i18n.extract(BytesIO(src.encode("utf-8")), [], None, {"extract_python": True}))

    def test_substituting_gettext_with_lambda(self):
        src = """<xml>hi</xml>"""
        expected = """<xml>spam</xml>"""

        perform(src, expected, context={"gettext": lambda _: "spam"})

    def test_substituting_gettext_with_lambda_extending(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate("""<div>parent</div>"""),
                "child.html": XMLTemplate("""<py:extends href="parent.html"><div>child</div></py:extends>"""),
            }
        )
        tpl = loader.import_("child.html")
        rsp = tpl({"gettext": lambda _: "egg"}).render()
        assert rsp == """<div>egg</div><div>egg</div>""", rsp

    def test_substituting_gettext_with_lambda_extending_twice(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate("<div>parent</div>"),
                "mid.html": XMLTemplate('<py:extends href="parent.html"><div>${variable}</div></py:extends>'),
                "child.html": XMLTemplate('<py:extends href="mid.html"><div>child</div></py:extends>'),
            }
        )
        tpl = loader.import_("child.html")
        rsp = tpl({"variable": "spam", "gettext": lambda _: "egg"}).render()
        # variables must not be translated
        assert rsp == """<div>egg</div><div>spam</div><div>egg</div>""", rsp

    def test_substituting_gettext_with_lambda_extending_file(self):
        loader = FileLoader(
            path=os.path.join(os.path.dirname(__file__), "data"),
            base_globals={"gettext": lambda _: "egg"},
        )
        tpl = loader.import_("file_child.html")
        rsp = tpl({}).render()
        assert rsp == """<div>egg</div><div>egg</div>""", rsp

    def test_without_substituting_gettext_with_lambda_extending_file(self):
        # this should use i18n.gettext
        loader = FileLoader(path=os.path.join(os.path.dirname(__file__), "data"))
        tpl = loader.import_("file_child.html")
        rsp = tpl({}).render()
        assert rsp == """<div>parent</div><div>child</div>""", rsp


class TestDOMTransformations(TestCase):
    def test_empty_text_extraction(self):
        doc = kajiki.xml_template._Parser("<string>", """<span>  text  </span>""").parse()
        doc = kajiki.xml_template._DomTransformer(doc, strip_text=False).transform()
        text_data = [n.data for n in doc.firstChild.childNodes]
        assert ["  ", "text", "  "] == text_data

    def test_empty_text_extraction_lineno(self):
        doc = kajiki.xml_template._Parser(
            "<string>",
            """<span>

          text

            </span>""",
        ).parse()
        doc = kajiki.xml_template._DomTransformer(doc, strip_text=False).transform()
        linenos = [n.lineno for n in doc.firstChild.childNodes]
        assert [1, 3, 3] == linenos  # Last node starts on same line as it starts with \n


class TestErrorReporting(TestCase):
    def test_syntax_error(self):
        for strip_text in (False, True):
            with pytest.raises(
                KajikiSyntaxError,
                match=r"-->         for i i range\(1, 2\):",
            ):
                perform(
                    '<div py:for="i i range(1, 2)">${i}</div>',
                    "",
                    strip_text=strip_text,
                )

    @pytest.mark.skipif(sys.implementation.name == "pypy", reason="lnotab has issues with pypy")
    def test_code_error(self):
        for strip_text in (False, True):
            child = FileLoader(os.path.join(os.path.dirname(__file__), "data")).load(
                "error.html", strip_text=strip_text
            )
            with pytest.raises(ZeroDivisionError) as exc_info:
                child().render()
            formatted = traceback.format_exception(None, exc_info.value, exc_info.tb)
            last_line = formatted[-2]
            assert "${3/0}" in last_line


class TestBracketsInExpression(TestCase):
    def test_simple(self):
        perform("<x>${'ok'}</x>", "<x>ok</x>")

    def test_some_brackets(self):
        perform("<x>${'{ok}'}</x>", "<x>{ok}</x>")

    def test_brackets_asymmetric(self):
        perform("<x>${'{o{k}k  { '}</x>", "<x>{o{k}k  { </x>")

    def test_complex(self):
        perform(
            "<xml><div>${'ciao {  } {' + \"a {} b {{{{} w}}rar\"}${'sd{}'}" " ${1+1}</div></xml>",
            "<xml><div>ciao {  } {a {} b {{{{} w}}rarsd{} 2</div></xml>",
        )

    def test_with_padding_space(self):
        perform(
            '<x y="${ 1 + 1}"> ${  "hello"     +   "world"   }  </x>',
            '<x y="2"> helloworld  </x>',
        )

    def test_raise_unclosed_string(self):
        with pytest.raises(XMLTemplateCompileError) as e:
            XMLTemplate('<x>${"ciao}</x>')
        # assert "can't compile" in str(e)  # different between pypy and cpython
        assert '"ciao' in str(e)

    def test_raise_plus_with_an_operand(self):
        with pytest.raises(XMLTemplateCompileError) as e:
            XMLTemplate('<x>${"ciao" + }</x>')
        assert "detected an invalid python expression" in str(e)
        assert '"ciao" +' in str(e)

    def test_unclosed_braced(self):
        with pytest.raises(
            XMLTemplateCompileError,
            match="Braced expression not terminated",
        ):
            XMLTemplate('<x>${"ciao"</x>')

    def test_leading_opening_brace(self):
        with pytest.raises(
            XMLTemplateCompileError,
            match="Braced expression not terminated",
        ):
            XMLTemplate('<x>${{"a", "b"}</x>')


class TestMultipleChildrenInDOM(TestCase):
    def test_ok(self):
        XMLTemplate("<xml><!--  a  --><x>${1+1}</x></xml>")

    def test_comment(self):
        res = XMLTemplate("<!-- a --><x>${1+1}</x>")().render()
        assert res == "<x>2</x>"

    def test_multiple_nodes(self):
        with pytest.raises(XMLTemplateParseError, match="junk after document"):
            XMLTemplate("<!-- a --><x>${1+1}</x><y>${1+1}</y>")

    def test_only_comment(self):
        with pytest.raises(XMLTemplateParseError, match="no element found"):
            XMLTemplate("<!-- a -->")


class TestSyntaxErrorCallingWithTrailingParenthesis(TestCase):
    def test_raise(self):
        with pytest.raises(XMLTemplateCompileError):
            XMLTemplate(
                """<div py:strip="True"
><py:def function="echo(x)">$x</py:def
>${echo('hello'))}</div>"""
            )


class TestExtendsWithImport(TestCase):
    def test_extends_with_import(self):
        loader = MockLoader(
            {
                "parent.html": XMLTemplate("<div>" '<py:import href="lib.html"/>' "${lib.foo()}" "</div>"),
                "lib.html": XMLTemplate("<div>" '<py:def function="foo()"><b>foo</b></py:def>' "</div>"),
                "child.html": XMLTemplate('<py:extends href="parent.html"/>'),
            }
        )
        child = loader.import_("child.html")
        r = child().render()
        assert r == "<div><b>foo</b></div>"
