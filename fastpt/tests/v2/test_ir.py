from unittest import TestCase, main

from fastpt import v2 as fpt
from fastpt.v2 import ir 

class TestBasic(TestCase):

    def setUp(self):
        self.tpl = ir.TemplateNode(
            ir.DefNode(
                '__call__()',
                ir.TextNode('Hello, '),
                ir.ExprNode('name'),
                ir.TextNode('\n')))

    def test(self):
        text =  '\n'.join(map(str, self.tpl.py()))
        dct = dict(fpt=fpt)
        exec text in dct
        tpl =  dct['template']
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

class TestSwitch(TestCase):

    def setUp(self):
        self.tpl = ir.TemplateNode(
            ir.DefNode(
                '__call__()',
                ir.ForNode(
                    'i in range(2)',
                    ir.ExprNode('i'),
                    ir.TextNode(' is '),
                    ir.SwitchNode(
                        'i % 2',
                        ir.CaseNode(
                            '0',
                            ir.TextNode('even\n')),
                        ir.ElseNode(
                            ir.TextNode('odd\n'))))))

    def test_basic(self):
        text =  '\n'.join(map(str, self.tpl.py()))
        dct = dict(fpt=fpt)
        exec text in dct
        tpl =  dct['template']
        rsp = tpl(dict()).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp
        

if __name__ == '__main__':
    main()
