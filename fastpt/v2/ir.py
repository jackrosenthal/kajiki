class Node(object):

    def __init__(self):
        self._tpl = None

    def py(self):
        return []

    def line(self, text):
        return PyLine(self._tpl, 0, text)

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

    def __init__(self, tpl, lineno, text, indent=0):
        self._tpl = tpl
        self._lineno = lineno
        self._text = text
        self._indent = indent

    def indent(self, sz=4):
        return PyLine(self._tpl, self._lineno, self._text, self._indent + sz)

    def __str__(self):
        return (' ' * self._indent) + self._text

