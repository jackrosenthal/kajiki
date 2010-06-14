import os

from lxml import etree

from . import compiler
from . import runtime

class Template(object):

    def __init__(self, filename=None, text=None, directory=None):
        if filename:
            if directory is None:
                directory = os.path.dirname(filename)
            text = open(filename).read()
        else:
            filename='<string>'
        self.filename = filename
        self.text = text
        self.directory = directory
        self._tree = self._tree_expanded = self._result = None
        self._code = None

    def parse(self):
        if self._tree is None:
            self._tree = etree.fromstring(self.text)
        return self._tree

    def expand(self):
        if self._tree_expanded is None:
            self._tree_expanded = compiler.expand(self.parse())
        return self._tree_expanded

    def compile(self):
        if self._result is None:
            self._result = compiler.compile_el(self.expand())
            self._text = '\n'.join(self._result.py())
            self._code = compile(self._text, self.filename, 'exec')
        return self._result

    def render(self, **local_ns):
        self.compile()
        rt = runtime.Runtime()
        global_ns = dict(__fpt__=rt)
        exec self._code in global_ns, local_ns
        return rt.render()

