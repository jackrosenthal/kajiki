from unittest import TestCase, main

from fastpt import v2 as fpt
from fastpt.v2 import ir 

class TestBasic(TestCase):

    def setUp(self):
        self.tpl = ir.TemplateNode(
            defs=[ir.DefNode(
                '__call__()',
                ir.TextNode('Hello, '),
                ir.ExprNode('name'),
                ir.TextNode('\n'))])

    def test(self):
        tpl = fpt.template.from_ir(self.tpl)
        rsp = tpl(dict(name='Rick')).__fpt__.render() 
        assert rsp == 'Hello, Rick\n', rsp

class TestSwitch(TestCase):

    def setUp(self):
        self.tpl = ir.TemplateNode(
            defs=[ir.DefNode(
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
                                ir.TextNode('odd\n')))))])
            
    def test_basic(self):
        tpl = fpt.template.from_ir(self.tpl)
        rsp = tpl(dict()).__fpt__.render() 
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestFunction(TestCase):

    def setUp(self):
        self.tpl = ir.TemplateNode(
            defs=[ir.DefNode(
                    'evenness(n)',
                    ir.IfNode(
                        'n % 2 == 0',
                        ir.TextNode('even')),
                    ir.ElseNode(
                        ir.TextNode('odd'))),
                  ir.DefNode(
                    '__call__()',
                    ir.ForNode(
                        'i in range(2)',
                        ir.ExprNode('i'),
                        ir.TextNode(' is '),
                        ir.ExprNode('evenness(i)'),
                        ir.TextNode('\n')))])

    def test_basic(self):
        tpl = fpt.template.from_ir(self.tpl)
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestCall(TestCase):
    
    def setUp(self):
        self.tpl = ir.TemplateNode(
            defs=[ir.DefNode(
                    'quote(caller, speaker)',
                    ir.ForNode(
                        'i in range(2)',
                        ir.TextNode('Quoth '),
                        ir.ExprNode('speaker'),
                        ir.TextNode(', "'),
                        ir.ExprNode('caller(i)'),
                        ir.TextNode('."\n'))),
                  ir.DefNode(
                    '__call__()',
                    ir.CallNode(
                        '$caller(n)',
                        "quote($caller, 'the raven')",
                        ir.TextNode('Nevermore '),
                        ir.ExprNode('n')))])
            
    def test_basic(self):
        tpl = fpt.template.from_ir(self.tpl)
        rsp = tpl(dict(name='Rick')).__fpt__.render()
        assert (
            rsp == 'Quoth the raven, "Nevermore 0."\n'
            'Quoth the raven, "Nevermore 1."\n'), rsp

class TestImport(TestCase):
    
    def setUp(self):
        lib = ir.TemplateNode(
            defs=[ir.DefNode(
                    'evenness(n)',
                    ir.IfNode(
                        'n % 2 == 0',
                        ir.TextNode('even')),
                    ir.ElseNode(
                        ir.TextNode('odd'))),
                  ir.DefNode(
                    'half_evenness(n)',
                    ir.TextNode(' half of '),
                    ir.ExprNode('n'),
                    ir.TextNode(' is '),
                    ir.ExprNode('evenness(n/2)'))])
        tpl = ir.TemplateNode(
            defs=[ir.DefNode(
                    '__call__()',
                    ir.ImportNode(
                        'lib.txt',
                        'simple_function'),
                    ir.ForNode(
                        'i in range(4)',
                        ir.ExprNode('i'),
                        ir.TextNode(' is '),
                        ir.ExprNode('simple_function.evenness(i)'),
                        ir.ExprNode('simple_function.half_evenness(i)'),
                        ir.TextNode('\n')))])
        loader = fpt.loader.MockLoader({
            'lib.txt':fpt.template.from_ir(lib),
            'tpl.txt':fpt.template.from_ir(tpl)})
        self.tpl = loader.import_('tpl.txt')

    def test_import(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert (rsp=='0 is even half of 0 is even\n'
                '1 is odd half of 1 is even\n'
                '2 is even half of 2 is odd\n'
                '3 is odd half of 3 is odd\n'), rsp

class TestInclude(TestCase):
    
    def setUp(self):
        hdr = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.TextNode('# header\n'))])
        tpl = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.TextNode('a\n'),
                    ir.IncludeNode('hdr.txt'),
                    ir.TextNode('b\n'))])
        loader = fpt.loader.MockLoader({
            'hdr.txt':fpt.template.from_ir(hdr),
            'tpl.txt':fpt.template.from_ir(tpl)})
        self.tpl = loader.import_('tpl.txt')

    def test_include(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'a\n# header\nb\n', rsp

class TestExtends(TestCase):

    def setUp(self):
        parent_tpl = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.ExprNode('header()'),
                    ir.ExprNode('body()'),
                    ir.ExprNode('footer()')),
                ir.DefNode(
                    'header()',
                    ir.TextNode('# Header name='),
                    ir.ExprNode('name'),
                    ir.TextNode('\n')),
                ir.DefNode(
                    'body()',
                    ir.TextNode('## Parent Body\n'),
                    ir.TextNode('local.id() = '),
                    ir.ExprNode('local.id()'),
                    ir.TextNode('\n'),
                    ir.TextNode('self.id() = '),
                    ir.ExprNode('self.id()'),
                    ir.TextNode('\n'),
                    ir.TextNode('child.id() = '),
                    ir.ExprNode('child.id()'),
                    ir.TextNode('\n')),
                ir.DefNode(
                    'footer()',
                    ir.TextNode('# Footer\n')),
                ir.DefNode(
                    'id()',
                    ir.TextNode('parent'))])
        mid_tpl = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.ExtendNode('parent.txt')),
                ir.DefNode(
                    'id()',
                    ir.TextNode('mid'))])
        child_tpl = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.ExtendNode('mid.txt')),
                ir.DefNode(
                    'body()',
                    ir.TextNode('## Child Body\n'),
                    ir.ExprNode('parent.body()')),
                ir.DefNode(
                    'id()',
                    ir.TextNode('child'))])
        loader = fpt.loader.MockLoader({
            'parent.txt':fpt.template.from_ir(parent_tpl),
            'mid.txt':fpt.template.from_ir(mid_tpl),
            'child.txt':fpt.template.from_ir(child_tpl)})
        self.loader = loader
        self.tpl = loader.import_('child.txt')
        
    def test_extends(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert (rsp == '# Header name=Rick\n'
                '## Parent Body\n'
                'local.id() = parent\n'
                'self.id() = child\n'
                'child.id() = mid\n'
                '# Footer\n'), rsp

class TestDynamicExtends(TestCase):
    def setUp(self):
        p0 = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.TextNode('Parent 0'))])
        p1 = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.TextNode('Parent 1'))])
        child = ir.TemplateNode(
            defs=[
                ir.DefNode(
                    '__call__()',
                    ir.IfNode(
                        'p==0',
                        ir.ExtendNode('parent0.txt')),
                    ir.ElseNode(
                        ir.ExtendNode('parent1.txt')))])
        loader = fpt.loader.MockLoader({
            'parent0.txt':fpt.template.from_ir(p0),
            'parent1.txt':fpt.template.from_ir(p1),
            'child.txt':fpt.template.from_ir(child)})
        self.loader = loader
        self.tpl = loader.import_('child.txt')

    def test_extends(self):
        rsp = self.tpl(dict(p=0)).__fpt__.render()
        assert rsp == 'Parent 0', rsp
        rsp = self.tpl(dict(p=1)).__fpt__.render()
        assert rsp == 'Parent 1', rsp

if __name__ == '__main__':
    main()
