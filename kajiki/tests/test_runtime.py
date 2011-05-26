from unittest import TestCase, main

import kajiki

class TestBasic(TestCase):

    def setUp(self):
        class tpl:
            @kajiki.expose
            def __main__():
                yield 'Hello,'
                yield name
                yield '\n'
        self.tpl = kajiki.Template(tpl)

    def test_basic(self):
        rsp = self.tpl(dict(name='Rick')).render()
        assert rsp == 'Hello,Rick\n', rsp

class TestSwitch(TestCase):

    def setUp(self):
        class tpl:
            @kajiki.expose
            def __main__():
                for i in range(2):
                    yield local.__kj__.escape(i)
                    yield ' is '
                    local.__kj__.push_switch(i % 2)
                    if local.__kj__.case(0):
                        yield 'even\n'
                    else:
                        yield 'odd\n'
        self.tpl = kajiki.Template(tpl)

    def test_basic(self):
        rsp = self.tpl().render()
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestFunction(TestCase):
    
    def setUp(self):
        class tpl:
            @kajiki.expose
            def evenness(n):
                if n % 2 == 0: yield 'even'
                else: yield 'odd'
            @kajiki.expose
            def __main__():
                for i in range(2):
                    yield local.__kj__.escape(i)
                    yield ' is '
                    yield evenness(i)
                    yield '\n'
        self.tpl = kajiki.Template(tpl)

    def test_basic(self):
        rsp = self.tpl(dict(name='Rick')).render()
        assert rsp == '0 is even\n1 is odd\n', rsp

class TestCall(TestCase):
    
    def setUp(self):
        class tpl:
            @kajiki.expose
            def quote(caller, speaker):
                for i in range(2):
                    yield 'Quoth '
                    yield speaker
                    yield ', "'
                    yield caller(i)
                    yield '."\n'
            @kajiki.expose
            def __main__():
                @__kj__.flattener.decorate
                def _kj_lambda(n):
                    yield 'Nevermore '
                    yield local.__kj__.escape(n)
                yield quote(_kj_lambda, 'the raven')
                del _kj_lambda
        self.tpl = kajiki.Template(tpl)

    def test_basic(self):
        rsp = self.tpl(dict(name='Rick')).render()
        assert (
            rsp == 'Quoth the raven, "Nevermore 0."\n'
            'Quoth the raven, "Nevermore 1."\n'), rsp

class TestImport(TestCase):
    def setUp(self):
        class lib_undec:
            @kajiki.expose
            def evenness(n):
                if n % 2 == 0: yield 'even'
                else: yield 'odd'
            @kajiki.expose
            def half_evenness(n):
                yield ' half of '
                yield local.__kj__.escape(n)
                yield ' is '
                yield evenness(n/2)
        lib = kajiki.Template(lib_undec)
        class tpl:
            @kajiki.expose
            def __main__():
                simple_function = lib(dict(globals()))
                for i in range(4):
                    yield local.__kj__.escape(i)
                    yield ' is '
                    yield simple_function.evenness(i)
                    yield simple_function.half_evenness(i)
                    yield '\n'
        self.tpl = kajiki.Template(tpl)

    def test_import(self):
        rsp = self.tpl(dict(name='Rick')).render()
        assert (rsp=='0 is even half of 0 is even\n'
                '1 is odd half of 1 is even\n'
                '2 is even half of 2 is odd\n'
                '3 is odd half of 3 is odd\n'), rsp

class TestInclude(TestCase):
    def setUp(self):
        class hdr_undec:
            @kajiki.expose
            def __main__():
                yield '# header\n'
        hdr = kajiki.Template(hdr_undec)
        class tpl_undec:
            @kajiki.expose
            def __main__():
                yield 'a\n'
                yield hdr().__main__()
                yield 'b\n'
        tpl = kajiki.Template(tpl_undec)
        self.tpl = tpl

    def test_include(self):
        rsp = self.tpl(dict(name='Rick')).render()
        assert rsp == 'a\n# header\nb\n', rsp

class TestExtends(TestCase):
    def setUp(_self):
        class parent_tpl_undec:
            @kajiki.expose
            def __main__():
                yield header()
                yield body()
                yield footer()
            @kajiki.expose
            def header():
                yield '# Header name='
                yield name
                yield '\n'
            @kajiki.expose
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
            @kajiki.expose
            def footer():
                yield '# Footer'
                yield '\n'
            @kajiki.expose
            def id():
                yield 'parent'
        parent_tpl = kajiki.Template(parent_tpl_undec)
        
        class mid_tpl_undec:
            @kajiki.expose
            def __main__():
                yield local.__kj__.extend(parent_tpl).__main__()
            @kajiki.expose
            def id():
                yield 'mid'
        mid_tpl = kajiki.Template(mid_tpl_undec)

        class child_tpl_undec:
            @kajiki.expose
            def __main__():
                yield local.__kj__.extend(mid_tpl).__main__()
            @kajiki.expose
            def body():
                yield '## Child Body\n'
                yield parent.body()
            @kajiki.expose
            def id():
                yield 'child'
        child_tpl = kajiki.Template(child_tpl_undec)
        _self.parent_tpl = parent_tpl
        _self.child_tpl = child_tpl

    def test_extends(self):
        rsp = self.child_tpl(dict(name='Rick')).render()
        assert (rsp == '# Header name=Rick\n'
                '## Child Body\n'
                '## Parent Body\n'
                'local.id() = parent\n'
                'self.id() = child\n'
                'child.id() = mid\n'
                '# Footer\n'), rsp

class TestDynamicExtends(TestCase):
    def setUp(_self):
        class parent_0_undec:
            @kajiki.expose
            def __main__():
                yield 'Parent 0'
        parent_0 = kajiki.Template(parent_0_undec)
        class parent_1_undec:
            @kajiki.expose
            def __main__():
                yield 'Parent 1'
        parent_1 = kajiki.Template(parent_1_undec)
        class child_tpl:
            @kajiki.expose
            def __main__():
                if p == 0:
                    yield local.__kj__.extend(parent_0).__main__()
                else:
                    yield local.__kj__.extend(parent_1).__main__()
        _self.child_tpl = kajiki.Template(child_tpl)

    def test_extends(self):
        rsp = self.child_tpl(dict(p=0)).render()
        assert rsp == 'Parent 0', rsp
        rsp = self.child_tpl(dict(p=1)).render()
        assert rsp == 'Parent 1', rsp

if __name__ == '__main__':
    main()
