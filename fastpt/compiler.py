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
        etree.ProcessingInstruction: (PythonDirective,),
        }
    
def compile_el(el):
    '''CompiledNode = compile(etree.element)

    Compiles some fastpt etree into a block of Python code and
    a sensitivity set
    '''
    r = ELEMENT_DISPATCH.get(el.tag, (Suite,))
    result = r[0](el, *r[1:])
    for part in compile_text(el.text):
        result.append(part)
    for child in el:
        result.append(compile_el(child))
        for part in compile_text(child.tail):
            result.append(part)
    return result

def compile_text(text):
    if text:
        last_match = 0
        for mo in re_sub.finditer(text):
            b,e = mo.span()
            if b != last_match:
                yield TextNode(text[last_match:b])
            last_match = e
            yield ExprNode(mo.group('p0') or mo.group('p1'))
        if last_match < len(text):
            yield TextNode(text[last_match:])

class ResultNode(object):

    def py(self):
        pass

class TemplateNode(ResultNode):

    def __init__(self, child):
        self.child = child

    def py(self):
        yield 'def template(__fpt__):'
        for line in self.child.py():
            yield '    ' + line

class TextNode(ResultNode):
    def __init__(self, text):
        self._text = text
    def py(self):
        yield '__fpt__.append(%r)' % self._text

class ExprNode(ResultNode):
    def __init__(self, text):
        self._text = text
    def py(self):
        yield '__fpt__.append(__fpt__.escape(%s))' % self._text
    
class Suite(ResultNode):

    def __init__(self, el):
        self._el = el
        self.content = []
        self.disable_append = False
        self.strip_if = None
        # Build prefix
        self.prefix = [TextNode('<%s' % self._el.tag)]
        for k,v in self._el.attrib.iteritems():
            if k == '{%s}content' % NS:
                self.content.append(ExprNode(v))
                self.disable_append = True
                continue
            elif k == '{%s}strip' % NS:
                self.strip_if = v
                continue
            self.prefix.append(TextNode(' %s="' % k))
            self.prefix += list(compile_text(v))
            self.prefix.append(TextNode('"'))
        self.prefix.append(TextNode('>'))
        self.suffix = [ TextNode('</%s>' % self._el.tag)  ]

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
    
    def __init__(self, el, keyword, attrib):
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
    
    def __init__(self, el):
        self._el = el
        self._replacement = ExprNode(el.attrib['value'])

    def append(self, result):
        pass

    def py(self):
        for part in self._replacement.py():
            yield part

class DefDirective(SimpleDirective):
    
    def __init__(self, el, keyword, attrib):
        super(DefDirective, self).__init__(el, keyword, attrib)

    def py(self):
        yield '%s %s:' % (self._keyword, self._el.attrib[self._attrib])
        yield '    __fpt__.push()'
        for part in self.parts:
            for pp in part.py():
                yield '    ' + pp
        yield '    __fpt__.pop()'

class ChooseDirective(ResultNode):
    _stack = []

    def __init__(self, el):
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
    
    def __init__(self, el):
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
    
    def __init__(self, el):
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

    def __init__(self, el):
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

class PythonDirective(ResultNode):

    def __init__(self, el):
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
        print '***Expand***', directive, etree.tostring(tree)
        nsmap = parent and parent.nsmap or tree.nsmap
        node = etree.Element(directive)
        node.attrib[attr] = value
        if parent is not None:
            parent.replace(tree, node)
        node.append(tree)
        node.append(expand(tree, node))
        return node
    new_children = []
    for child in tree:
        new_children.append(expand(child, tree))
    tree[:] = new_children
    return tree


on_import()
