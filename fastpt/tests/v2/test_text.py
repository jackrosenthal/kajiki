from unittest import TestCase, main

from fastpt import v2 as fpt
from fastpt.v2.text import TextTemplate

class TestBasic(TestCase):

    def test_auto_escape(self):
        tpl = TextTemplate(source="${'<h1>'}")
        rsp = tpl().__fpt__.render() 
        assert rsp == '&lt;h1&gt;', rsp

    def test_auto_escape_disable(self):
        tpl = TextTemplate(source="${literal('<h1>')}")
        rsp = tpl().__fpt__.render() 
        assert rsp == '<h1>', rsp

    def test_expr_brace(self):
        tpl = TextTemplate(source='Hello, ${name}\n')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

    def test_expr_brace_complex(self):
        tpl = TextTemplate(source="Hello, ${{'name':name}['name']}\n")
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

    def test_expr_name(self):
        tpl = TextTemplate(source='Hello, $name\n')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp
        tpl = TextTemplate(source='Hello, $obj.name\n')
        class Empty: pass
        Empty.name = 'Rick'
        rsp = tpl(dict(obj=Empty)).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

class TestSwitch(TestCase):

    def test_switch(self):
        tpl = TextTemplate('''%for i in range(2)
$i is {%switch i % 2 %}{%case 0%}even\n{%else%}odd\n{%end%}\\
%end''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp

    def test_ljust(self):
        tpl = TextTemplate('''     %for i in range(2)
$i is {%switch i % 2 %}{%case 0%}even\n{%else%}odd\n{%end%}\\
%end''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp
        tpl = TextTemplate('''     {%-for i in range(2)%}\\
$i is {%switch i % 2 %}{%case 0%}even{%else%}odd{%end%}
    {%-end%}''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp

    def test_rstrip(self):
        tpl = TextTemplate('''     %for i in range(2)
$i is {%switch i % 2 %}{%case 0-%}    even\n{%else%}odd\n{%end%}\\
%end''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestFunction(TestCase):

    def test_function(self):
        tpl = TextTemplate('''%def evenness(n)
{%if n % 2 == 0 %}even{%else%}odd{%end%}\\
%end
%for i in range(2)
$i is ${evenness(i)}
%end
''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestCall(TestCase):

    def test_call(self):
        tpl = TextTemplate('''%def quote(caller, speaker)
    %for i in range(2)
Quoth $speaker, "${caller(i)}."
    %end
%end
%call(n) quote(%caller ,'the raven')
Nevermore $n\\
%end''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert (
            rsp == 'Quoth the raven, "Nevermore 0."\n'
            'Quoth the raven, "Nevermore 1."\n'), rsp

class TestImport(TestCase):

    def test_import(self):
        lib = TextTemplate('''%def evenness(n)
%if n % 2 == 0
even\\
%else
odd\\
%end
%end
%def half_evenness(n)
 half of $n is ${evenness(n/2)}\\
%end''')
        tpl = TextTemplate('''%import "lib.txt" as simple_function
%for i in range(4)
$i is ${simple_function.evenness(i)}${simple_function.half_evenness(i)}
%end''')
        loader = fpt.loader.MockLoader({
            'lib.txt':lib,
            'tpl.txt':tpl})
        tpl = loader.import_('tpl.txt')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert (rsp=='0 is even half of 0 is even\n'
                '1 is odd half of 1 is even\n'
                '2 is even half of 2 is odd\n'
                '3 is odd half of 3 is odd\n'), rsp

    def test_import_auto(self):
        lib = TextTemplate('''%def evenness(n)
%if n % 2 == 0
even\\
%else
odd\\
%end
%end
%def half_evenness(n)
 half of $n is ${evenness(n/2)}\\
%end''')
        tpl = TextTemplate('''%import "lib.txt"
%for i in range(4)
$i is ${lib.evenness(i)}${lib.half_evenness(i)}
%end''')
        loader = fpt.loader.MockLoader({
            'lib.txt':lib,
            'tpl.txt':tpl})
        tpl = loader.import_('tpl.txt')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert (rsp=='0 is even half of 0 is even\n'
                '1 is odd half of 1 is even\n'
                '2 is even half of 2 is odd\n'
                '3 is odd half of 3 is odd\n'), rsp

    def test_include(self):
        loader = fpt.loader.MockLoader({
                'hdr.txt': TextTemplate('# header\n'),
                'tpl.txt': TextTemplate('''a
%include "hdr.txt"
b
''')})
        tpl = loader.import_('tpl.txt')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'a\n# header\nb\n', rsp

class TestExtends(TestCase):

    def test_basic(self):
        parent = TextTemplate('''
%def header()
# Header name=$name
%end
%def footer()
# Footer
%end
%def body()
## Parent Body
local.id() = ${local.id()}
self.id() = ${self.id()}
child.id() = ${child.id()}
%end
%def id()
parent\\
%end
${header()}${body()}${footer()}''')
        mid = TextTemplate('''%extends "parent.txt"
%def id()
mid\\
%end
''')
        child = TextTemplate('''%extends "mid.txt"
%def id()
child\\
%end
%def body()
## Child Body
${parent.body()}\
%end
''')
        loader = fpt.loader.MockLoader({
            'parent.txt':parent,
            'mid.txt':mid,
            'child.txt':child})
        tpl = loader.import_('child.txt')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert (rsp == '# Header name=Rick\n'
                '## Parent Body\n'
                'local.id() = parent\n'
                'self.id() = child\n'
                'child.id() = mid\n'
                '# Footer\n'), rsp

    def test_dynamic(self):
        loader = fpt.loader.MockLoader({
                'parent0.txt':TextTemplate('Parent 0'),
                'parent1.txt':TextTemplate('Parent 1'),
                'child.txt':TextTemplate('''%if p == 0
%extends "parent0.txt"
%else
%extends "parent1.txt"
%end
''')
                })
        tpl = loader.import_('child.txt')
        rsp = tpl(dict(p=0)).__fpt__.render()
        assert rsp == 'Parent 0', rsp
        rsp = tpl(dict(p=1)).__fpt__.render()
        assert rsp == 'Parent 1', rsp

    def test_block(self):
        loader = fpt.loader.MockLoader({
                'parent.txt':TextTemplate('''%def greet(name)
Hello, $name!\\
%end
%def sign(name)
Sincerely,
$name\\
%end
${greet(to)}

%block body
It was good seeing you last Friday.  Thanks for the gift!
%end

${sign(from_)}
'''),
                'child.txt':TextTemplate('''%extends "parent.txt"
%def greet(name)
Dear $name:\\
%end
%block body
${parent_block()}\\

And don't forget you owe me money!
%end
''')})
        child = loader.import_('child.txt')
        rsp = child({'to':'Mark', 'from_':'Rick'}).__fpt__.render()
        assert (rsp=='''Dear Mark:
It was good seeing you last Friday.  Thanks for the gift!

And don't forget you owe me money!

Sincerely,
Rick
'''), rsp
        

class TestClosure(TestCase):
    
    def test(self):
        tpl = TextTemplate('''%def add(x)
%def inner(y)
${x+y}\\
%end
${inner(x*2)}\\
%end
${add(5)}
''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '15\n', rsp

class TestPython(TestCase):

    def test_basic(self):
        tpl = TextTemplate('''%py
import os
%end
${os.path.join('a','b','c')}''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'a/b/c'

    def test_indent(self):
        tpl = TextTemplate('''%py
    import os
    import re
%end
${os.path.join('a','b','c')}''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'a/b/c'

    def test_short(self):
        tpl = TextTemplate('''%py import os
${os.path.join('a','b','c')}''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'a/b/c'

    def test_mod(self):
        tpl = TextTemplate('''%py% import os
%def test()
${os.path.join('a','b','c')}\\
%end
${test()}''')
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'a/b/c'

if __name__ == '__main__':
    main()
