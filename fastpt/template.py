import os
import types
from cStringIO import StringIO

from lxml import etree

from . import compiler
from . import runtime

class Template(object):

    def __init__(self, filename=None, text=None, directory=None):
        if filename:
            if directory is None:
                directory = os.path.dirname(filename)
        else:
            filename='<string>'
        if text is None:
            text = open(filename).read()
        self.filename = filename
        self.text = text
        self.directory = directory
        self._tree = self._tree_expanded = self._result = None
        self._func_code = None
        self._lnotab = LineNumberTable(self)

    def parse(self):
        if self._tree is None:
            parser = etree.XMLParser(strip_cdata=False)
            self._tree = etree.parse(StringIO(self.text), parser).getroot()
            # self._tree = etree.fromstring(self.text)
        return self._tree

    def expand(self):
        if self._tree_expanded is None:
            self._tree_expanded = compiler.expand(self.parse())
        return self._tree_expanded

    def compile(self):
        if self._result is None:
            self._result = compiler.TemplateNode(self, compiler.compile_el(self, self.expand()))
            self._text = '\n'.join(map(str, self._result.py()))
            ns = {}
            exec self._text in ns
            self._func_code = ns['template'].func_code
        return self._result

    def render(self, **ns):
        self.compile()
        rt = runtime.Runtime()
        global_ns = dict(ns, __builtins__=__builtins__)
        func = types.FunctionType(self._func_code, global_ns)
        func(rt)
        return rt.render()

    def load(self, spec):
        fn = os.path.join(
            self.directory,
            spec)
        return Template(fn)

class LineNumberTable(object):

    def __init__(self, tpl):
        self._xml_from_py = {}
        self._cur_xml_line = None
        self._cur_py_line = 0

    def enter_xml(self, line):
        self._cur_xml_line = line

    def pyline(self, line):
        self._cur_py_line += 1
        self._xml_from_py[self._cur_py_line] = self._cur_xml_line
        return line
