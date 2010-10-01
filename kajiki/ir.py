from .util import gen_name, flattener

def generate_python(ir):
    cur_indent = 0
    for node in flattener(ir):
        if isinstance(node, IndentNode):
            cur_indent += 4
        elif isinstance(node, DedentNode):
            cur_indent -= 4
        for line in node.py():
            yield line.indent(cur_indent)

class Node(object):

    def __init__(self):
        self.filename = '<string>'
        self.lineno = 0

    def py(self): # pragma no cover
        return []

    def __iter__(self):
        yield self

    def line(self, text):
        return PyLine(self.filename, self.lineno, text)

class HierNode(Node):

    def __init__(self, body):
        super(HierNode, self).__init__()
        self.body = tuple(x for x in body if x is not None)

    def body_iter(self):
        for x in optimize(flattener(map(flattener, self.body))):
            yield x

    def __iter__(self):
        yield self
        yield IndentNode()
        for x in self.body_iter(): yield x
        yield DedentNode()

class IndentNode(Node): pass
class DedentNode(Node): pass

class TemplateNode(HierNode):

    def __init__(self, mod_py=None, defs=None):
        super(TemplateNode, self).__init__(defs)
        if mod_py is None: mod_py = []
        if defs is None: defs = []
        self.mod_py = [ x for x in mod_py if x is not None ]

    def py(self):
        yield self.line('@kajiki.Template')
        yield self.line('class template:')

    def __iter__(self):
        for x in flattener(self.mod_py):
            yield x
        for x in super(TemplateNode, self).__iter__():
            yield x

class ImportNode(Node):

    def __init__(self, tpl_name, alias=None):
        super(ImportNode, self).__init__()
        self.tpl_name = tpl_name
        self.alias = alias

    def py(self):
        yield self.line(
            'local.__kj__.import_(%r, %r, globals())' % (
                self.tpl_name, self.alias))

class IncludeNode(Node):

    def __init__(self, tpl_name):
        super(IncludeNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__kj__.import_(%r, None, {}).__main__()' % (
                self.tpl_name))

class ExtendNode(Node):

    def __init__(self, tpl_name):
        super(ExtendNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__kj__.extend(%r).__main__()' % (
                self.tpl_name))

class DefNode(HierNode):
    prefix = '@kajiki.expose'

    def __init__(self, decl, *body):
        super(DefNode, self).__init__(body)
        self.decl = decl

    def py(self):
        yield self.line(self.prefix)
        yield self.line('def %s:' % (self.decl))

class InnerDefNode(DefNode):
    prefix='@__kj__.flattener.decorate'

class CallNode(HierNode):

    class CallTail(Node):
        def __init__(self, call):
            super(CallNode.CallTail, self).__init__()
            self.call = call
        def py(self):
            yield self.line('yield ' + self.call) 

    def __init__(self, caller, callee, *body):
        super(CallNode, self).__init__(body)
        fname = gen_name()
        self.decl = caller.replace('$caller', fname)
        self.call = callee.replace('$caller', fname)

    def py(self):
        yield self.line('@__kj__.flattener.decorate')
        yield self.line('def %s:' % (self.decl))

    def __iter__(self):
        yield self
        yield IndentNode()
        for x in self.body_iter(): yield x
        yield DedentNode()
        yield self.CallTail(self.call)

class ForNode(HierNode):

    def __init__(self, decl, *body):
        super(ForNode, self).__init__(body)
        self.decl = decl

    def py(self):
        yield self.line('for %s:' % (self.decl))

class SwitchNode(HierNode):

    class SwitchTail(Node):
        def py(self):
            yield self.line('local.__kj__.pop_switch()')

    def __init__(self, decl, *body):
        super(SwitchNode, self).__init__(body)
        self.decl = decl

    def py(self):
        yield self.line('local.__kj__.push_switch(%s)' % self.decl)

    def __iter__(self):
        yield self
        for x in self.body_iter(): yield x
        yield self.SwitchTail()

class CaseNode(HierNode):

    def __init__(self, decl, *body):
        super(CaseNode, self).__init__(body)
        self.decl = decl

    def py(self):
        yield self.line('if local.__kj__.case(%s):' % self.decl)

class IfNode(HierNode):

    def __init__(self, decl, *body):
        super(IfNode, self).__init__(body)
        self.decl = decl

    def py(self):
        yield self.line('if %s:' % self.decl)

class ElseNode(HierNode):

    def __init__(self,  *body):
        super(ElseNode, self).__init__(body)

    def py(self):
        yield self.line('else:')

class TextNode(Node):

    def __init__(self, text, guard=None):
        super(TextNode, self).__init__()
        self.text = text
        self.guard = guard

    def py(self):
        s = 'yield %r' % self.text
        if self.guard:
            yield self.line('if %s: %s' % (self.guard, s))
        else:
            yield self.line(s)

class TranslatableTextNode(TextNode):

    def py(self):
        text = self.text.strip()
        if text:
            s = 'yield local.__kj__.gettext(%r)' % self.text
        else:
            s = 'yield %r' % self.text
        if self.guard:
            yield self.line('if %s: %s' % (self.guard, s))
        else:
            yield self.line(s)

class ExprNode(Node):

    def __init__(self, text):
        super(ExprNode, self).__init__()
        self.text = text

    def py(self):
        yield self.line('yield self.__kj__.escape(%s)' % self.text)

class PassNode(Node):

    def py(self):
        yield self.line('pass')

class AttrNode(HierNode):

    class AttrTail(Node):
        def __init__(self, parent):
            super(AttrNode.AttrTail, self).__init__()
            self.p = parent
        def py(self):
            gen = self.p.genname
            x = gen_name()
            yield self.line("%s = ''.join(%s())" % (gen, gen))
            yield self.line(
                'for %s in self.__kj__.render_attrs({%r:%s}, %r):'
                % (x, self.p.attr, gen, self.p.mode))
            yield self.line('    yield %s' % x)

    def __init__(self, attr, value, guard=None, mode='xml'):
        super(AttrNode, self).__init__(value)
        self.attr = attr
        # self.value = value
        self.guard = guard
        self.mode = mode
        self.attrname, self.genname = gen_name(), gen_name()

    def py(self):
        x,gen = gen_name(), gen_name()
        def _body():
            yield self.line('def %s():' % gen)
            for part in self.value:
                import pdb; pdb.set_trace()
                for line in part.py():
                    yield line.indent()
            yield self.line("%s = ''.join(%s())" % (gen,gen))
            yield self.line(
                'for %s in self.__kj__.render_attrs({%r:%s}, %r):'
                % (x, self.attr, gen, self.mode))
            yield self.line('    yield %s' % x)
        if self.guard:
            yield self.line('if %s:' % self.guard)
            for l in _body():
                yield l.indent()
        else:
            for l in _body(): yield l

    def py(self):
        yield self.line('def %s():' % self.genname)

    def __iter__(self):
        if self.guard:
            new_body = IfNode(
                'if %s' % self.guard,
                AttrNode(self.attr, value=self.body, mode=self.mode))
            for x in new_body:
                yield x
        else:
            yield self
            yield IndentNode()
            for part in self.body_iter():
                yield part
            yield DedentNode()
            yield self.AttrTail(self)

class AttrsNode(Node):

    def __init__(self, attrs, guard=None, mode='xml'):
        super(AttrsNode, self).__init__()
        self.attrs = attrs
        self.guard = guard
        self.mode = mode

    def py(self):
        x = gen_name()
        def _body():
            yield self.line(
                'for %s in self.__kj__.render_attrs(%s, %r):' % (x, self.attrs, self.mode))
            yield self.line('    yield %s' % x)
        if self.guard:
            yield self.line('if %s:' % self.guard)
            for l in _body():
                yield l.indent()
        else:
            for l in _body(): yield l

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

def optimize(iter_node):
    last_node = None
    for node in iter_node:
        if type(node) == TextNode:
            if (type(last_node) == TextNode
                and last_node.guard == node.guard):
                last_node.text += node.text
            else:
                if last_node is not None: yield last_node
                last_node = node
        else:
            if last_node is not None: yield last_node
            last_node = node
    if last_node is not None:
        yield last_node

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
        if self._lineno:
            return (' ' * self._indent) + self._text + '\t# %s:%d' % (self._filename, self._lineno)
        else:
            return (' ' * self._indent) + self._text

    def __repr__(self):
        return '%s:%s %s' % (self._filename, self._lineno, self)

