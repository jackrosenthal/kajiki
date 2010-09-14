from .util import gen_name

class Node(object):

    def __init__(self):
        self.filename = '<string>'
        self.lineno = 0

    def py(self): # pragma no cover
        return []

    def line(self, text):
        return PyLine(self.filename, self.lineno, text)

class TemplateNode(Node):

    def __init__(self, mod_py=None, defs=None):
        super(TemplateNode, self).__init__()
        if mod_py is None: mod_py = []
        if defs is None: defs = []
        self.mod_py = [ x for x in mod_py if x is not None ]
        self.defs = [ x for x in defs if x is not None ]

    def py(self):
        for block in self.mod_py:
            for  line in block.py():
                yield line
        yield self.line('@fpt.Template')
        yield self.line('class template:')
        for child in self.defs:
            for line in child.py():
                yield line.indent()

class ImportNode(Node):

    def __init__(self, tpl_name, alias=None):
        super(ImportNode, self).__init__()
        self.tpl_name = tpl_name
        self.alias = alias

    def py(self):
        yield self.line(
            'local.__fpt__.import_(%r, %r, globals())' % (
                self.tpl_name, self.alias))

class IncludeNode(Node):

    def __init__(self, tpl_name):
        super(IncludeNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__fpt__.import_(%r, None, {}).__call__()' % (
                self.tpl_name))

class ExtendNode(Node):

    def __init__(self, tpl_name):
        super(ExtendNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__fpt__.extend(%r).__call__()' % (
                self.tpl_name))

class DefNode(Node):
    prefix = '@fpt.expose'

    def __init__(self, decl, *body):
        super(DefNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line(self.prefix)
        yield self.line('def %s:' % (self.decl))
        for child in self.body:
            for line in child.py():
                yield line.indent()

class InnerDefNode(DefNode):
    prefix='@__fpt__.flattener.decorate'

class CallNode(Node):

    def __init__(self, caller, callee, *body):
        super(CallNode, self).__init__()
        fname = gen_name()
        self.decl = caller.replace('$caller', fname)
        self.call = callee.replace('$caller', fname)
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('@__fpt__.flattener.decorate')
        yield self.line('def %s:' % (self.decl))
        for child in self.body:
            for line in child.py():
                yield line.indent()
        yield self.line('yield ' + self.call)

class ForNode(Node):

    def __init__(self, decl, *body):
        super(ForNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('for %s:' % (self.decl))
        for child in self.body:
            for line in child.py():
                yield line.indent()

class SwitchNode(Node):

    def __init__(self, decl, *body):
        super(SwitchNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('local.__fpt__.push_switch(%s)' % self.decl)
        for child in self.body:
            for line in child.py():
                yield line
        yield self.line('local.__fpt__.pop_switch()')

class CaseNode(Node):

    def __init__(self, decl, *body):
        super(CaseNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('if local.__fpt__.case(%s):' % self.decl)
        for child in self.body:
            for line in child.py():
                yield line.indent()

class IfNode(Node):

    def __init__(self, decl, *body):
        super(IfNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('if %s:' % self.decl)
        for child in self.body:
            for line in child.py():
                yield line.indent()

class ElseNode(Node):

    def __init__(self,  *body):
        super(ElseNode, self).__init__()
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('else:')
        for child in self.body:
            for line in child.py():
                yield line.indent()

class TextNode(Node):

    def __init__(self, text):
        super(TextNode, self).__init__()
        self.text = text

    def py(self):
        yield self.line('yield %r' % self.text)

class ExprNode(Node):

    def __init__(self, text):
        super(ExprNode, self).__init__()
        self.text = text

    def py(self):
        yield self.line('yield self.__fpt__.escape(%s)' % self.text)

class PythonNode(Node):

    def __init__(self, *body):
        super(PythonNode, self).__init__()
        self.module_level = False
        blocks = []
        for b in body:
            assert isinstance(b, TextNode)
            blocks.append(b.text)
        text = ''.join(blocks)
        if text[0] == '%':
            self.module_level = True
            text = text[1:]
        self.lines = list(self._normalize(text))

    def py(self):
        for line in self.lines:
            yield self.line(line)

    def _normalize(self, text):
        if text.startswith('#\n'):
            text = text[2:]
        prefix = None
        for line in text.splitlines():
            if prefix is None:
                rest = line.lstrip()
                prefix = line[:len(line)-len(rest)]
            assert line.startswith(prefix)
            yield line[len(prefix):]

class PyLine(object):

    def __init__(self, filename, lineno, text, indent=0):
        self._filename = filename
        self._lineno = lineno
        self._text = text
        self._indent = indent

    def indent(self, sz=4):
        return PyLine(self._filename, self._lineno, self._text, self._indent + sz)

    def __str__(self):
        return (' ' * self._indent) + self._text

