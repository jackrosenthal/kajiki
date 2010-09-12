from unittest import TestCase, main

from fastpt import v2 as fpt

class TestBasic(TestCase):

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

class TestSwitch(TestCase):

    def setUp(self):
        @fpt.Template
        class tpl:
            @fpt.expose
            def __call__():
                for i in range(2):
                    yield i
                    yield ' is '
                    local.__fpt__.push_switch(i % 2)
                    if local.__fpt__.case(0):
                        yield 'even\n'
                    else:
                        yield 'odd\n'
        self.tpl = tpl

    def test_basic(self):
        rsp = self.tpl().__fpt__.render()
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestFunction(TestCase):
    
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

class TestCall(TestCase):
    
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

class TestImport(TestCase):
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

class TestInclude(TestCase):
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
        assert rsp == 'a\n# header\nb\n', rsp

class TestExtends(TestCase):
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
                yield 'local.id() = '
                yield local.id()
                yield '\n'
                yield 'self.id() = '
                yield self.id()
                yield '\n'
                yield 'child.id() = '
                yield child.id()
                yield '\n'
            @fpt.expose
            def footer():
                yield '# Footer'
                yield '\n'
            @fpt.expose
            def id():
                yield 'parent'

        @fpt.Template
        class mid_tpl:
            @fpt.expose
            def __call__():
                yield local.__fpt__.extend(parent_tpl).__call__()
            @fpt.expose
            def id():
                yield 'mid'

        @fpt.Template
        class child_tpl:
            @fpt.expose
            def __call__():
                yield local.__fpt__.extend(mid_tpl).__call__()
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
        assert (rsp == '# Header name=Rick\n'
                '## Child Body\n'
                '## Parent Body\n'
                'local.id() = parent\n'
                'self.id() = child\n'
                'child.id() = mid\n'
                '# Footer\n'), rsp

class TestDynamicExtends(TestCase):
    def setUp(_self):
        @fpt.Template
        class parent_0:
            @fpt.expose
            def __call__():
                yield 'Parent 0'
        @fpt.Template
        class parent_1:
            @fpt.expose
            def __call__():
                yield 'Parent 1'
        @fpt.Template
        class child_tpl:
            @fpt.expose
            def __call__():
                if p == 0:
                    yield local.__fpt__.extend(parent_0).__call__()
                else:
                    yield local.__fpt__.extend(parent_1).__call__()
        _self.child_tpl = child_tpl

    def test_extends(self):
        rsp = self.child_tpl(dict(p=0)).__fpt__.render()
        assert rsp == 'Parent 0', rsp
        rsp = self.child_tpl(dict(p=1)).__fpt__.render()
        assert rsp == 'Parent 1', rsp

if __name__ == '__main__':
    main()
