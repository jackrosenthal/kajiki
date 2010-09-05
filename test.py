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
        print self.tpl(fpt.Context(name='Rick')).render()

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
                for i in range(5):
                    yield i
                    yield ' is '
                    yield evenness(i)
                    yield '\n'
        self.tpl = tpl

    def test_basic(self):
        print self.tpl(fpt.Context(name='Rick')).render()

if __name__ == '__main__':
    main()
