from unittest import TestCase, main

from fastpt import v2 as fpt

class BasicTest(TestCase):

    def setUp(self):
        @fpt.Template
        class tpl:
            @fpt.expose
            def __call__():
                yield 'Hello,'
                yield name
                yield '\n'
        self.tpl = tpl

    def test_basic(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == 'Hello,Rick\n', rsp

class FunctionTest(TestCase):
    
    def setUp(self):
        @fpt.Template
        class tpl:
            @fpt.expose
            def evenness(n):
                if n % 2 == 0: yield 'even'
                else: yield 'odd'
            @fpt.expose
            def __call__():
                for i in range(2):
                    yield i
                    yield ' is '
                    yield evenness(i)
                    yield '\n'
        self.tpl = tpl

    def test_basic(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert rsp == '0 is even\n1 is odd\n', rsp

class CallTest(TestCase):
    
    def setUp(self):
        @fpt.Template
        class tpl:
            @fpt.expose
            def quote(caller, speaker):
                for i in range(2):
                    yield 'Quoth '
                    yield speaker
                    yield ', "'
                    yield caller(i)
                    yield '."\n'
            @fpt.expose
            def __call__():
                @__fpt__.flattener.decorate
                def _fpt_lambda(n):
                    yield 'Nevermore '
                    yield n
                yield quote(_fpt_lambda, 'the raven')
                del _fpt_lambda
        self.tpl = tpl

    def test_basic(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert (
            rsp == 'Quoth the raven, "Nevermore 0."\n'
            'Quoth the raven, "Nevermore 1."\n'), rsp

class ImportTest(TestCase):
    def setUp(self):
        @fpt.Template
        class lib:
            @fpt.expose
            def evenness(n):
                if n % 2 == 0: yield 'even'
                else: yield 'odd'
            @fpt.expose
            def half_evenness(n):
                yield ' half of '
                yield n
                yield ' is '
                yield evenness(n/2)
        @fpt.Template
        class tpl:
            @fpt.expose
            def __call__():
                simple_function = lib(dict(globals()))
                for i in range(4):
                    yield i
                    yield ' is '
                    yield simple_function.evenness(i)
                    yield simple_function.half_evenness(i)
                    yield '\n'
        self.tpl = tpl

    def test_import(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        assert (rsp=='0 is even half of 0 is even\n'
                '1 is odd half of 1 is even\n'
                '2 is even half of 2 is odd\n'
                '3 is odd half of 3 is odd\n'), rsp

class IncludeTest(TestCase):
    def setUp(self):
        @fpt.Template
        class hdr:
            @fpt.expose
            def __call__():
                yield '# header\n'
        @fpt.Template
        class tpl:
            @fpt.expose
            def __call__():
                yield 'a\n'
                yield hdr().__call__()
                yield 'b\n'
        self.tpl = tpl

    def test_include(self):
        rsp = self.tpl(dict(name='Rick')).__fpt__.render()
        print rsp

class ExtendsTest(TestCase):
    def setUp(_self):
        @fpt.Template
        class parent_tpl:
            @fpt.expose
            def __call__():
                yield header()
                yield body()
                yield footer()
            @fpt.expose
            def header():
                yield '# Header name='
                yield name
                yield '\n'
            @fpt.expose
            def body():
                yield '## Parent Body\n'
                yield 'local =  '
                yield local
                yield '\n'
                yield 'self =  '
                yield self
                yield '\n'
                yield 'child =  '
                yield child
                yield '\n'
            @fpt.expose
            def footer():
                yield '# Footer'
                yield '\n'
            @fpt.expose
            def id():
                yield 'parent'

        @fpt.Template
        class child_tpl:
            @fpt.expose
            def __call__():
                yield local.__fpt__.extend(parent_tpl).__call__()
            @fpt.expose
            def body():
                yield '## Child Body\n'
                yield parent.body()
            @fpt.expose
            def id():
                yield 'child'
        _self.parent_tpl = parent_tpl
        _self.child_tpl = child_tpl

    def test_extends(self):
        rsp = self.child_tpl(dict(name='Rick')).__fpt__.render()
        print rsp

        
        
if __name__ == '__main__':
    main()
