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
        rsp = self.tpl(fpt.Context(name='Rick')).render()
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
        rsp = self.tpl(fpt.Context(name='Rick')).render()
        assert rsp == '0 is even\n1 is odd\n', rsp

if __name__ == '__main__':
    main()
