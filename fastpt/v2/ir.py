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

    def __init__(self, *body):
        super(TemplateNode, self).__init__()
        self.body = body

    def py(self):
        yield self.line('@fpt.Template')
        yield self.line('class template:')
        for child in self.body:
            for line in child.py():
                yield line.indent()

class ImportNode(Node):

    def __init__(self, tpl_name, alias):
        super(ImportNode, self).__init__()
        self.tpl_name = tpl_name
        self.alias = alias

    def py(self):
        yield self.line(
            '%s = local.__fpt__.import_(%r)(globals())' % (
                self.alias, self.tpl_name))

class IncludeNode(Node):

    def __init__(self, tpl_name):
        super(IncludeNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__fpt__.import_(%r)().__call__()' % (
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

    def __init__(self, decl, *body):
        super(DefNode, self).__init__()
        self.decl = decl
        self.body = body

    def py(self):
        yield self.line('@fpt.expose')
        yield self.line('def %s:' % (self.decl))
        for child in self.body:
            for line in child.py():
                yield line.indent()

class CallNode(Node):

    def __init__(self, caller, callee, *body):
        super(CallNode, self).__init__()
        fname = gen_name()
        self.decl = caller.replace('$caller', fname)
        self.call = callee.replace('$caller', fname)
        self.body = body

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
        self.body = body

    def py(self):
        yield self.line('for %s:' % (self.decl))
        for child in self.body:
            for line in child.py():
                yield line.indent()

class SwitchNode(Node):

    def __init__(self, decl, *body):
        super(SwitchNode, self).__init__()
        self.decl = decl
        self.body = body

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
        self.body = body

    def py(self):
        yield self.line('if local.__fpt__.case(%s):' % self.decl)
        for child in self.body:
            for line in child.py():
                yield line.indent()

class IfNode(Node):

    def __init__(self, decl, *body):
        super(IfNode, self).__init__()
        self.decl = decl
        self.body = body

    def py(self):
        yield self.line('if %s:' % self.decl)
        for child in self.body:
            for line in child.py():
                yield line.indent()

class ElseNode(Node):

    def __init__(self,  *body):
        super(ElseNode, self).__init__()
        self.body = body

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
        yield self.line('yield %s' % self.text)

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

