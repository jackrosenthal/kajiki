import re

from lxml import etree

from core import QDIRECTIVES

re_sub = re.compile(r'''\$(?:
    (?P<p0>[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)
|
    \{(?P<p1>[^}]*)})
''', re.VERBOSE)

def compile_el(el):
    '''CompiledNode = compile(etree.element)

    Compiles some fastpt etree into a block of Python code and
    a sensitivity set
    '''
    if el.tag.endswith('def'):
        result = DefDirective(el, 'def', 'function')
    elif el.tag.endswith('for'):
        result = SimpleDirective(el, 'for', 'each')
    elif el.tag.endswith('if'):
        result = SimpleDirective(el, 'if', 'test')
    else:
        result = Suite(el)
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
        if '$' in text: import pdb; pdb.set_trace()
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
        attrs = ' '.join('%s="%s"' % (k,v) for k,v in self._el.attrib.iteritems())
        self.parts = [
            TextNode('<%s %s>' % (self._el.tag, attrs)) ]
        self.last = TextNode('</%s>' % self._el.tag) 

    def append(self, result):
        self.parts.append(result)

    def py(self):
        for part in self.parts + [self.last]:
            for pp in part.py():
                yield pp

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


def expand(tree, parent=None):
    for directive, attr in QDIRECTIVES:
        value = tree.attrib.pop(directive, None)
        if value is None: continue
        node = etree.Element(directive, nsmap=tree.nsmap)
        node.attrib[attr] = value
        if parent is not None:
            parent.append(node)
            try:
                parent.remove(tree)
            except ValueError:
                pass
        node.append(expand(tree, node))
        return node
    new_children = []
    for child in tree:
        new_children.append(expand(child, tree))
    tree[:] = new_children
    return tree
