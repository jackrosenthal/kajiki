from unittest import TestCase, main

from fastpt.v2.text import TextTemplate

class TestBasic(TestCase):

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
$i is {%switch i % 2 %}{%case 0%}even\n{%else%}odd\n{%end%}\
%end''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp
        tpl = TextTemplate('''     {%-for i in range(2)%}
$i is {%switch i % 2 %}{%case 0%}even{%else%}odd{%end%}
    {%-end%}''')
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp

if __name__ == '__main__':
    main()
