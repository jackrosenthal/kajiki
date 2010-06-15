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
        self.lnotab = {} # lnotab[python_lineno] = xml_lineno

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
            self._text = '\n'.join(self._result.py())
            ns = {}
            exec self._text in ns
            self._func_code_orig = ns['template'].func_code
            self._func_code = self._translate_code(self._func_code_orig)
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

    def _translate_code(self, code):
        lnotab = map(ord, code.co_lnotab)
        lnotab = zip(lnotab[::2], lnotab[1::2])
        new_tab = []
        cur_line = code.co_firstlineno
        print code.co_firstlineno
        for i, line in enumerate(self._text.split('\n')):
            print '%s: %s' % (i+1, line)
        print self.lnotab
        for b_off, l_off in lnotab:
            new_loff = self.lnotab[cur_line+l_off]-self.lnotab[cur_line]
            cur_line += l_off
            if new_loff < 0:
                continue
            new_tab.append(b_off)
            new_tab.append(new_loff)
        lnotab = ''.join(map(chr, new_tab))
        return types.CodeType(
            code.co_argcount,
            code.co_nlocals,
            code.co_stacksize,
            code.co_flags,
            code.co_code,
            code.co_consts,
            code.co_names,
            code.co_varnames,
            self.filename,
            code.co_name,
            self.lnotab[code.co_firstlineno],
            lnotab,
            code.co_freevars,
            code.co_cellvars)
            
            
