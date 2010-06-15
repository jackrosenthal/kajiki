import unittest

from lxml import etree 

from fastpt import Template, NS_DECL

def nospace(s):
    if isinstance(s, basestring):
        return ''.join(ch for ch in s if ch not in (' \t\r\n'))
    else:
        return nospace(etree.tostring(s))

class TestErrors(unittest.TestCase):

    def test_assert(self):
        t0 = Template('fastpt/tests/data/assert.html')
        print t0.render()

class TestExpand(unittest.TestCase):

    def test_def(self):
        t0 = Template(text='<div %s py:def="foo(x)"/>' % NS_DECL)
        t1 = Template(text='<py:def %s function="foo(x)"><div/></py:def>' % NS_DECL)
        assert nospace(t0.expand()) == nospace(t1.expand()), \
            '%s\nis not\n%s' % (etree.tostring(t0.expand()),
                                etree.tostring(t1.expand()))
        
    def test_complex(self):
        t0 = Template(text='''<div %s>
    <ul>
        <li py:for="i,line in enumerate(lines)" py:if="i %% 2">$i: $line</li>
    </ul>
</div>
''' % NS_DECL)
        t1 = Template(text='''<div %s>
    <ul>
        <py:for each="i, line in enumerate(lines)">
            <py:if test="i %% 2">
                <li>$i: $line</li>
            </py:if>
        </py:for>
    </ul>
</div>
''' % NS_DECL)
        assert nospace(t0.expand()) == nospace(t1.expand()), \
            '%s\nis not\n%s' % (etree.tostring(t0.expand()),
                                etree.tostring(t1.expand()))

class TestCompile(unittest.TestCase):

    def test_compile_simple(self):
        t0 = Template(text='<span>Hello there, $name! ${1+1+444}</span>')
        for line in t0.compile().py():
            print line

    def test_compile_if(self):
        t0 = Template(text='''<span %s py:if="name">
    <ul>
        <li py:for="i in range(10)"
            >Hello there, $name! ${i*i} <py:if
              test="i %% 2">Odd</py:if><py:if
              test="not i %% 2">Even</py:if
        ></li>
    </ul>
</span>
''' % NS_DECL)
        t0.compile()
        print t0._text
        print t0.render(name='Rick')

    def test_compile_def(self):
        t0 = Template(text='''<div %s>
    <py:def function="greet(name)">
        Hi, <h1>$name</h1>
    </py:def>
    <py:for each="i in range(10)">
        $i: ${greet(name)}
    </py:for>
</div>
''' % NS_DECL)
        t0.compile()
        print t0._text
        print t0.render(name='Rick')

    def test_large(self):
        t0 = Template(text='''<div %s py:strip="name != 'Rick'">
    <py:def function="greet(name)">
        Hi, <h1>$name</h1>
    </py:def>
    <ul>
        <li py:for="i in range(5)"
            class="${'odd' if i%%2 else 'even'}"
            py:content="greet(name)"/>
    </ul>
    <span py:replace="name">Name Placeholder</span>
    <div py:choose="name" py:with="l = len(name)">
      <span py:when="'Rick'">Rick Copeland $l</span>
      <span py:when="'Mark'">Mark Ramm $l</span>
    </div>
</div>
''' % NS_DECL)
        t0.compile()
        print etree.tostring(t0._tree_expanded)
        print t0._text
        print t0.render(name='Rick')
        print t0.render(name='Mark')

    def test_python(self):
        t0 = Template(text='''<div %s>
    <?python import sys ?>
    <?python #
        for x in range(10):
            print x
        print 'Done!' ?>
</div>''' % NS_DECL)
        t0.compile()
        print 'EXPANDED'
        print etree.tostring(t0._tree_expanded)
        print 'TEXT'
        print t0._text
        t0.render(name='Rick')

    def test_inheritance(self):
        t0 = Template('fastpt/tests/data/parent.html')
        t0.compile()
        print t0._text
        print etree.tostring(t0._tree_expanded)
        print t0.render()
        t1 = Template('fastpt/tests/data/child.html')
        t1.compile()
        print t1._text
        print etree.tostring(t1._tree_expanded)
        print t1.render()
        
    def test_include(self):
        t0 = Template('fastpt/tests/data/test_include.html')
        t0.compile()
        print t0._text
        print etree.tostring(t0._tree_expanded)
        print t0.render(name='Rick')

        
