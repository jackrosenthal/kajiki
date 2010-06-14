import re

from lxml import etree

from core import QDIRECTIVES, NS

re_sub = re.compile(r'''\$(?:
    (?P<p0>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)
|
    \{(?P<p1>[^}]*)})
''', re.VERBOSE)

ELEMENT_DISPATCH=None

def on_import():
    global ELEMENT_DISPATCH

    ELEMENT_DISPATCH = {
        '{%s}def' % NS: (DefDirective, 'def', 'function'),
        '{%s}for' % NS: (SimpleDirective, 'for', 'each'),
        '{%s}if' % NS: (SimpleDirective, 'if', 'test'),
        '{%s}replace' % NS: (ReplaceDirective,),
        '{%s}choose' % NS: (ChooseDirective,),
        '{%s}when' % NS: (WhenDirective,),
        '{%s}otherwise' % NS: (OtherwiseDirective,),
        '{%s}with' % NS: (WithDirective,),
        '{%s}slot' % NS: (SlotDirective,),
        '{%s}extends' % NS: (ExtendsDirective,),
        etree.ProcessingInstruction: (PythonDirective,),
        }
    
def compile_el(tpl, el):
    '''CompiledNode = compile(etree.element)

    Compiles some fastpt etree into a block of Python code and
    a sensitivity set
    '''
    r = ELEMENT_DISPATCH.get(el.tag, (Suite,))
    result = r[0](tpl, el, *r[1:])
    for part in compile_text(tpl, el.text):
        result.append(part)
    for child in el:
        result.append(compile_el(tpl, child))
        for part in compile_text(tpl, child.tail):
            result.append(part)
    return result

def compile_text(tpl, text):
    if text:
        last_match = 0
        for mo in re_sub.finditer(text):
            b,e = mo.span()
            if b != last_match:
                yield TextNode(tpl, text[last_match:b])
            last_match = e
            yield ExprNode(mo.group('p0') or mo.group('p1'))
        if last_match < len(text):
            yield TextNode(tpl, text[last_match:])

class ResultNode(object):

    def __init__(self, tpl):
        self._tpl = tpl

    def py(self):
        pass

class TemplateNode(ResultNode):

    def __init__(self, tpl, child):
        self._tpl = tpl
        self.child = child

    def py(self):
        yield 'def template(__fpt__):'
        for line in self.child.py():
            yield '    ' + line

class TextNode(ResultNode):
    def __init__(self, tpl, text):
        self._tpl = tpl
        self._text = text
    def py(self):
        yield '__fpt__.append(%r)' % self._text

class ExprNode(ResultNode):

    def __init__(self, tpl, text):
        self._tpl = tpl
        self._text = text

    def py(self):
        yield '__fpt__.append(__fpt__.escape(%s))' % self._text
    
class Suite(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.content = []
        self.disable_append = False
        self.strip_if = None
        # Build prefix
        self.prefix = [TextNode(self._tpl, '<%s' % self._el.tag)]
        for k,v in self._el.attrib.iteritems():
            if k == '{%s}content' % NS:
                self.content.append(ExprNode(v))
                self.disable_append = True
                continue
            elif k == '{%s}strip' % NS:
                self.strip_if = v
                continue
            self.prefix.append(TextNode(self._tpl, ' %s="' % k))
            self.prefix += list(compile_text(v))
            self.prefix.append(TextNode(self._tpl, '"'))
        self.prefix.append(TextNode(self._tpl, '>'))
        self.suffix = [ TextNode(self._tpl, '</%s>' % self._el.tag)  ]

    def append(self, result):
        if not self.disable_append:
            self.content.append(result)

    def py(self):
        indent = ''
        if self.strip_if:
            yield 'if not (%s):' % self.strip_if
            indent = '    '
        for part in self.prefix:
            for pp in part.py():
                yield indent + pp
        for part in self.content:
            for pp in part.py():
                yield pp
        if self.strip_if:
            yield 'if not (%s):' % self.strip_if
        for part in self.suffix:
            for pp in part.py():
                yield indent + pp
            

class SimpleDirective(ResultNode):
    
    def __init__(self, tpl, el, keyword, attrib):
        self._tpl = tpl
        self._el = el
        self._keyword = keyword
        self._attrib = attrib
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def py(self):
        yield '%s %s:' % (self._keyword, self._el.attrib[self._attrib])
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp


class ReplaceDirective(ResultNode):
    
    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._replacement = ExprNode(el.attrib['value'])

    def append(self, result):
        pass

    def py(self):
        for part in self._replacement.py():
            yield part

class DefDirective(SimpleDirective):
    
    def __init__(self, tpl, el, keyword, attrib):
        super(DefDirective, self).__init__(tpl, el, keyword, attrib)

    def py(self):
        yield '%s %s:' % (self._keyword, self._el.attrib[self._attrib])
        yield '    __fpt__.push()'
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp
        yield '    __fpt__.pop()'

class ChooseDirective(ResultNode):
    _stack = []

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._test = el.attrib['test'] or 'True'
        self.parts = []
        self.choices = []

    def append(self, result):
        self.parts.append(result)

    def py(self):
        ChooseDirective._stack.append(self)
        for part in self.parts:
            for pp in part.py():
                yield pp
        ChooseDirective._stack.pop()

class WhenDirective(ResultNode):
    
    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._test = el.attrib['test']
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def py(self):
        choose = ChooseDirective._stack[-1]
        test = '(%s) == (%s)' % (choose._test, self._test)
        if choose.choices:
            yield 'elif %s:' % test
        else:
            yield 'if %s:' % test
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp

class OtherwiseDirective(ResultNode):
    
    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def py(self):
        yield 'else:'
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp

class WithDirective(ResultNode):
    _ctr = 0

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._stmt = el.attrib['vars']
        self.parts = []
        self._name = '_with_%s' % WithDirective._ctr
        WithDirective._ctr += 1
        

    def append(self, result):
        self.parts.append(result)

    def py(self):
        yield 'def %s(%s):' % (self._name, self._stmt.replace(';', ','))
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp
        yield '%s()' % self._name

class SlotDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._name = el.attrib['name']
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def py(self):
        yield 'if __fpt__.push_slot(%r):' % self._name
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp
        yield '__fpt__.pop()'

class ExtendsDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []
        self.parent = self._tpl.load(self._el.attrib['parent'])

    def append(self, result):
        self.parts.append(result)

    def py(self):
        yield '__fpt__.push()'
        for part in self.parts:
            for pp in part.py():
                yield pp
        yield '__fpt__.pop(False)'
        for line in compile_el(self.parent, self.parent.expand()).py():
            yield line
        
class PythonDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        assert el.target == 'python'

    def append(self, v):
        pass

    def py(self):
        lines = self._el.text.split('\n')
        if len(lines) == 1:
            yield lines[0]
        else:
            import pdb; pdb.set_trace()
            prefix = lines[1][:-len(lines[1].strip())]
            for line in lines[1:]:
                if line.startswith(prefix):
                    yield line[len(prefix):]
                else:
                    yield line

def expand(tree, parent=None):
    if not isinstance(tree.tag, basestring): return tree
    for directive, attr in QDIRECTIVES:
        value = tree.attrib.pop(directive, None)
        if value is None: continue
        nsmap = parent and parent.nsmap or tree.nsmap
        node = etree.Element(directive)
        node.attrib[attr] = value
        if parent is not None:
            parent.replace(tree, node)
        node.append(tree)
        node.tail = tree.tail
        tree.tail = ''
        node.append(expand(tree, node))
        return node
    new_children = []
    for child in tree:
        new_children.append(expand(child, tree))
    tree[:] = new_children
    return tree


on_import()
