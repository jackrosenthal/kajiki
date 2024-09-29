from unittest import TestCase

import kajiki


class TestBasic(TestCase):
    def setUp(self):
        class Tpl:
            @kajiki.expose
            def __main__():
                yield "Hello,"
                yield name  # noqa: F821
                yield "\n"

        self.tpl = kajiki.Template(Tpl)

    def test_basic(self):
        rsp = self.tpl({"name": "Rick"}).render()
        assert rsp == "Hello,Rick\n", rsp


class TestSwitch(TestCase):
    def setUp(self):
        class Tpl:
            @kajiki.expose
            def __main__():
                for i in range(2):
                    yield local.__kj__.escape(i)  # noqa: F821
                    yield " is "
                    local.__kj__.push_switch(i % 2)  # noqa: F821
                    if local.__kj__.case(0):  # noqa: F821
                        yield "even\n"
                    else:
                        yield "odd\n"

        self.tpl = kajiki.Template(Tpl)

    def test_basic(self):
        rsp = self.tpl().render()
        assert rsp == "0 is even\n1 is odd\n", rsp


class TestFunction(TestCase):
    def setUp(self):
        class Tpl:
            @kajiki.expose
            def evenness(self):
                if self % 2 == 0:
                    yield "even"
                else:
                    yield "odd"

            @kajiki.expose
            def __main__():
                for i in range(2):
                    yield local.__kj__.escape(i)  # noqa: F821
                    yield " is "
                    yield evenness(i)  # noqa: F821
                    yield "\n"

        self.tpl = kajiki.Template(Tpl)

    def test_basic(self):
        rsp = self.tpl({"name": "Rick"}).render()
        assert rsp == "0 is even\n1 is odd\n", rsp


class TestCall(TestCase):
    def setUp(self):
        class Tpl:
            @kajiki.expose
            def quote(self, speaker):
                for i in range(2):
                    yield "Quoth "
                    yield speaker
                    yield ', "'
                    yield self(i)
                    yield '."\n'

            @kajiki.expose
            def __main__():
                @__kj__.flattener.decorate  # noqa: F821
                def _kj_lambda(n):
                    yield "Nevermore "
                    yield local.__kj__.escape(n)  # noqa: F821

                yield quote(_kj_lambda, "the raven")  # noqa: F821
                del _kj_lambda

        self.tpl = kajiki.Template(Tpl)

    def test_basic(self):
        rsp = self.tpl({"name": "Rick"}).render()
        assert rsp == 'Quoth the raven, "Nevermore 0."\n' 'Quoth the raven, "Nevermore 1."\n', rsp


class TestImport(TestCase):
    def setUp(self):
        class LibUndec:
            @kajiki.expose
            def evenness(self):
                if self % 2 == 0:
                    yield "even"
                else:
                    yield "odd"

            @kajiki.expose
            def half_evenness(self):
                yield " half of "
                yield local.__kj__.escape(self)  # noqa: F821
                yield " is "
                yield evenness(self / 2)  # noqa: F821

        lib = kajiki.Template(LibUndec)

        class Tpl:
            @kajiki.expose
            def __main__():
                simple_function = lib(dict(globals()))
                for i in range(4):
                    yield local.__kj__.escape(i)  # noqa: F821
                    yield " is "
                    yield simple_function.evenness(i)
                    yield simple_function.half_evenness(i)
                    yield "\n"

        self.tpl = kajiki.Template(Tpl)

    def test_import(self):
        rsp = self.tpl({"name": "Rick"}).render()
        assert (
            rsp == "0 is even half of 0 is even\n"
            "1 is odd half of 1 is odd\n"
            "2 is even half of 2 is odd\n"
            "3 is odd half of 3 is odd\n"
        ), rsp


class TestInclude(TestCase):
    def setUp(self):
        class HdrUndec:
            @kajiki.expose
            def __main__():
                yield "# header\n"

        hdr = kajiki.Template(HdrUndec)

        class TplUndec:
            @kajiki.expose
            def __main__():
                yield "a\n"
                yield hdr().__main__()
                yield "b\n"

        tpl = kajiki.Template(TplUndec)
        self.tpl = tpl

    def test_include(self):
        rsp = self.tpl({"name": "Rick"}).render()
        assert rsp == "a\n# header\nb\n", rsp


class TestExtends(TestCase):
    def setUp(_self):
        class ParentTplUndec:
            @kajiki.expose
            def __main__():
                yield header()  # noqa: F821
                yield body()  # noqa: F821
                yield footer()  # noqa: F821

            @kajiki.expose
            def header():
                yield "# Header name="
                yield name  # noqa: F821
                yield "\n"

            @kajiki.expose
            def body():
                yield "## Parent Body\n"
                yield "local.id() = "
                yield local.id()  # noqa: F821
                yield "\n"
                yield "self.id() = "
                yield self.id()  # noqa: F821
                yield "\n"
                yield "child.id() = "
                yield child.id()  # noqa: F821
                yield "\n"

            @kajiki.expose
            def footer():
                yield "# Footer"
                yield "\n"

            @kajiki.expose
            def id():
                yield "parent"

        parent_tpl = kajiki.Template(ParentTplUndec)

        class MidTplUndec:
            @kajiki.expose
            def __main__():
                yield local.__kj__.extend(parent_tpl).__main__()  # noqa: F821

            @kajiki.expose
            def id():
                yield "mid"

        mid_tpl = kajiki.Template(MidTplUndec)

        class ChildTplUndec:
            @kajiki.expose
            def __main__():
                yield local.__kj__.extend(mid_tpl).__main__()  # noqa: F821

            @kajiki.expose
            def body():
                yield "## Child Body\n"
                yield parent.body()  # noqa: F821

            @kajiki.expose
            def id():
                yield "child"

        child_tpl = kajiki.Template(ChildTplUndec)
        _self.parent_tpl = parent_tpl
        _self.child_tpl = child_tpl

    def test_extends(self):
        rsp = self.child_tpl({"name": "Rick"}).render()
        assert (
            rsp == "# Header name=Rick\n"
            "## Child Body\n"
            "## Parent Body\n"
            "local.id() = parent\n"
            "self.id() = child\n"
            "child.id() = mid\n"
            "# Footer\n"
        ), rsp


class TestDynamicExtends(TestCase):
    def setUp(_self):
        class Parent0Undec:
            @kajiki.expose
            def __main__():
                yield "Parent 0"

        parent_0 = kajiki.Template(Parent0Undec)

        class Parent1Undec:
            @kajiki.expose
            def __main__():
                yield "Parent 1"

        parent_1 = kajiki.Template(Parent1Undec)

        class ChildTpl:
            @kajiki.expose
            def __main__():
                if p == 0:  # noqa: F821
                    yield local.__kj__.extend(parent_0).__main__()  # noqa: F821
                else:
                    yield local.__kj__.extend(parent_1).__main__()  # noqa: F821

        _self.child_tpl = kajiki.Template(ChildTpl)

    def test_extends(self):
        rsp = self.child_tpl({"p": 0}).render()
        assert rsp == "Parent 0", rsp
        rsp = self.child_tpl({"p": 1}).render()
        assert rsp == "Parent 1", rsp
