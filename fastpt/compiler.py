import re
import string

# from lxml import etree
from . import etree

from core import QDIRECTIVES, QDIRECTIVES_DICT, NS, XI_NS

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
        '{%s}super' % NS: (SuperDirective,),
        '{%s}call-slot' % NS: (CallSlotDirective,),
        '{%s}extends' % NS: (ExtendsDirective,),
        '{%s}include' % NS: (IncludeDirective,),
        '{%s}include' % XI_NS: (IncludeDirective,),
        '{%s}nop' % NS: (NopDirective,),
        etree.ProcessingInstruction: (PythonDirective,),
        etree.Comment: (PassThru,),
        }
    
def compile_el(tpl, el):
    '''CompiledNode = compile(etree.element)

    Compiles some fastpt etree into a block of Python code and
    a sensitivity set
    '''
    r = ELEMENT_DISPATCH.get(el.tag, (Suite,))
    result = r[0](tpl, el, *r[1:])
    for part in compile_text(tpl, el, el.text):
        result.append(part)
    for child in el:
        result.append(compile_el(tpl, child))
        for part in compile_text(tpl, child, child.tail):
            result.append(part)
    return result

def compile_text(tpl, el, text):
    ESCAPE_STARTERS=string.letters+'_'+'{'
    if text is None: text = ''
    def get_errpos(s):
        # SyntaxError sometimes returns the wrong offset, so we can't use it
        # http://bugs.python.org/issue1778
        for pos in xrange(len(s), 0, -1):
            try:
                compile(s[:pos], '', 'eval')
                return pos + 1
            except SyntaxError:
                pass
    def get_end_shorthand(s):
        for i, ch in enumerate(s):
            if ch not in string.letters + string.digits + '_' + '.':
                return i
        return i+1
    tok = []
    p = 0
    while p < len(text):
        ch = text[p]
        p += 1
        # Non-escaped
        if ch != '$':
            tok.append(ch)
            continue
        # Escape as last char -- must be literal
        if p == len(text):
            tok.append(ch)
            continue
        # Doubled escape char
        if text[p] == '$':
            tok.append(ch)
            p += 1
            continue
        # Check for non-expression 'escapes'
        if text[p] not in ESCAPE_STARTERS:
            tok.append(text[p])
            continue
        # Real escape -- emit a token            
        if tok:
            yield TextNode(tpl, el, ''.join(tok))
            tok = []
        if text[p] == '{':
            p += 1
            end_expr = get_errpos(text[p:])
            compile(text[p:p+end_expr-1], '', 'eval')
            yield ExprNode(tpl, el, text[p:p+end_expr-1])
            p += end_expr
        else:
            end_expr = get_end_shorthand(text[p:])
            yield ExprNode(tpl, el, text[p:p+end_expr])
            p += end_expr
    if tok:
        yield TextNode(tpl, el, ''.join(tok))

class TemplateNode(object):

    def __init__(self, tpl, child):
        self._tpl = tpl
        self.child = child

    def py(self):
        yield 'def template(__fpt__):'
        yield '    __fpt__.doctype()'
        self._tpl.lnotab[1] = 0
        self._tpl.lnotab[2] = 0
        for i, line in enumerate(self.child.py()):
            self._tpl.lnotab[i+2] = line._line
            yield str(line.indent())

class ResultNode(object):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el

    def _py(self):
        raise NotImplementedError, '_py'

    def py(self):
        for x in self._py():
            if isinstance(x, basestring):
                yield PyLine(self._tpl, self._el, x)
            else:
                yield x

class TextNode(ResultNode):

    def __init__(self, tpl, el, text):
        self._tpl = tpl
        self._el = el
        self._text = text

    def _py(self):
        yield '__fpt__.stack[-1].append(%r)' % self._text.encode('utf-8')

    def __repr__(self):
        return '<TextNode %r>' % self._text

class PassThru(TextNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._text = unicode(el)

    def append(self, v):
        pass

class AttrsNode(ResultNode):

    def __init__(self, tpl, el, attrs):
        self._tpl = tpl
        self._el = el
        self._text = attrs

    def _py(self):
        yield '__fpt__.attrs(%s)' % self._text

class ExprNode(ResultNode):

    def __init__(self, tpl, el, text):
        self._tpl = tpl
        self._el = el
        self._text = text

    def _py(self):
        yield '__fpt__.append(%s)' % self._text

    def __repr__(self):
        return '<ExprNode %s>' % self._text

class AttrNode(ResultNode):

    def __init__(self, tpl, el, k, v):
        self._tpl = tpl
        self._el = el
        self._k = k
        self._v = compile_text(tpl, el, v)

    def _py(self):
        yield '__fpt__.push()'
        for vv in self._v:
            for pp in vv.py():
                yield pp
        yield '__fpt__.pop_attr(%r)' % self._k
    
class Suite(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.content = []
        self.disable_append = False
        self.strip_if = None
        self.attrs = None
        # Build prefix
        self.prefix = [TextNode(self._tpl, el, '<%s' % strip_ns(self._el.tag))]
        for k,v in self._el.attrib.iteritems():
            if k == '{%s}content' % NS:
                self.content.append(ExprNode(tpl, el, v))
                self.disable_append = True
                continue
            elif k == '{%s}strip' % NS:
                self.strip_if = v
                continue
            elif k == '{%s}attrs' % NS:
                self.prefix.append(AttrsNode(self._tpl, el, v))
                continue
            self.prefix.append(AttrNode(tpl, el, k, v))
        self.prefix.append(TextNode(self._tpl, el, '>'))
        self.suffix = [ TextNode(self._tpl, el, '</%s>' % strip_ns(self._el.tag))  ]

    def append(self, result):
        if not self.disable_append:
            self.content.append(result)

    def _py(self):
        indent = 0
        if self.strip_if:
            yield 'if not (%s):' % self.strip_if
            indent = 4
        for part in self.prefix:
            for pp in part.py():
                yield pp.indent(indent)
        for part in self.content:
            for pp in part.py():
                yield pp
        if self.strip_if:
            yield 'if not (%s):' % self.strip_if
        for part in self.suffix:
            for pp in part.py():
                yield pp.indent(indent)
            

class SimpleDirective(ResultNode):
    
    def __init__(self, tpl, el, keyword, attrib):
        self._tpl = tpl
        self._el = el
        self._keyword = keyword
        self._attrib = attrib
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        yield '%s %s:' % (self._keyword, self._el.attrib[self._attrib])
        for part in self.parts:
            for pp in part.py():
                yield pp.indent()


class ReplaceDirective(ResultNode):
    
    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._replacement = ExprNode(tpl, el, el.attrib['value'])

    def append(self, result):
        pass

    def _py(self):
        for part in self._replacement.py():
            yield part

class DefDirective(SimpleDirective):
    
    def __init__(self, tpl, el, keyword, attrib):
        super(DefDirective, self).__init__(tpl, el, keyword, attrib)

    def _py(self):
        fname = self._el.attrib[self._attrib].split('(')[0]
        yield 'global ' + fname
        if '(' in self._el.attrib[self._attrib]:
            yield '%s %s:' % (self._keyword, self._el.attrib[self._attrib])
        else:
            yield '%s %s():' % (self._keyword, self._el.attrib[self._attrib])
        yield '    __fpt__.push()'
        for part in self.parts:
            for pp in part.py():
                yield pp.indent()
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

    def _py(self):
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

    def _py(self):
        choose = ChooseDirective._stack[-1]
        test = '(%s) == (%s)' % (choose._test, self._test)
        if choose.choices:
            yield 'elif %s:' % test
        else:
            yield 'if %s:' % test
        for part in self.parts:
            for pp in part.py():
                yield pp.indent()

class OtherwiseDirective(ResultNode):
    
    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        yield 'else:'
        for part in self.parts:
            for pp in part.py():
                yield pp.indent()

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

    def _py(self):
        yield 'def %s(%s):' % (self._name, self._stmt.replace(';', ','))
        for part in self.parts:
            for pp in part.py():
                yield pp.indent()
        yield '%s()' % self._name

class SlotDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self._name = el.attrib['name']
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        yield 'def __slot_%s__(__fpt__, __slot_depth__=-1):' % self._name
        yield '    __slot_name__ = %r' % self._name
        yield '    __fpt__.push()'
        for part in self.parts:
            for pp in part.py():
                yield pp.indent()
        yield '    return __fpt__.generate()'
        yield '__fpt__.def_slot(%r, __slot_%s__)' % (self._name, self._name)

class SuperDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        yield '__fpt__.super_slot(__slot_name__, __slot_depth__-1)'

class CallSlotDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        yield '__fpt__.call_slot(%r, %r)' % (
            self._el.attrib['href'],
            self._el.attrib['name'])

class ExtendsDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []
        # self.parent = self._tpl.load(self._el.attrib['parent'])

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        yield '__fpt__.include(%r, True)' % self._el.attrib['href']
        yield '__fpt__.push()'
        for part in self.parts:
            for pp in part.py():
                yield pp
        yield '__fpt__.pop(False)'
        
class IncludeDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el

    def append(self, result):
        pass

    def _py(self):
        yield '__fpt__.include(%r)' % self._el.attrib['href']
        
class PythonDirective(ResultNode):

    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        assert el.target == 'python'

    def append(self, v):
        pass

    def _py(self):
        lines = self._el.text.split('\n')
        if len(lines) == 1:
            yield lines[0]
        else:
            if lines[0] != '#':
                for line in lines: yield line
            else:
                prefix = lines[1][:-len(lines[1].strip())]
                for line in lines[1:]:
                    if line.startswith(prefix):
                        yield line[len(prefix):]
                    else:
                        yield line

class NopDirective(ResultNode):
    
    def __init__(self, tpl, el):
        self._tpl = tpl
        self._el = el
        self.parts = []

    def append(self, result):
        self.parts.append(result)

    def _py(self):
        for part in self.parts:
            for pp in part.py():
                yield pp


class PyLine(object):

    def __init__(self, tpl, el_or_lineno, text):
        self._tpl = tpl
        self._line = getattr(el_or_lineno, 'sourceline', el_or_lineno)
        self._text = text

    def indent(self, sz=4):
        return PyLine(self._tpl, self._line, (' '*sz)+self._text)

    def __str__(self):
        return self._text#  + '\t# %s:%d' % (self._tpl.filename, self._line)

def expand(tree, parent=None):
    if not isinstance(tree.tag, basestring): return tree
    if tree.tag in QDIRECTIVES_DICT:
        tree.attrib[tree.tag] = tree.attrib.pop(QDIRECTIVES_DICT[tree.tag])
        tree.tag = '{%s}nop' % NS
    for directive, attr in QDIRECTIVES:
        value = tree.attrib.pop(directive, None)
        if value is None: continue
        # nsmap = (parent is not None) and parent.nsmap or tree.nsmap
        node = etree.Element(directive)
        node.sourceline = tree.sourceline
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

def expand_entities(tree):
    if not isinstance(tree.tag, basestring): return 
    new_children = []
    for child in tree:
        if child.tag == etree.Entity:
            if new_children:
                c = new_children[-1]
                c.tail = (c.tail or '') + etree.tounicode(child)
            else:
                tree.text = (tree.text or '') + etree.tounicode(child)
        else:
            new_children.append(child)
    tree[:] = new_children
    for child in tree:
        expand_entities(child)

def strip_ns(s):
    return s.rsplit('}', 1)[-1]


on_import()
