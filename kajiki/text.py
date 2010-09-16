'''Text template compiler

Notable in this module are

TextTemplate - function building a template from text string or filename
_pattern - the regex used to find the beginnings of tags and expressions
_Scanner - scans text and generates a stream of tokens
_Parser - parses a stream of tokens into the internal representation (IR) tree
_Parser._parse_<tagname> - consumes the body of a tag and returns an ir.Node
'''
import re
import shlex
from collections import defaultdict
from itertools import chain

import kajiki
from . import ir

_pattern = r'''
\$(?:
    (?P<expr_escaped>\$) |      # Escape $$
    (?P<expr_named>[_a-z][_a-z0-9.]*) | # $foo.bar
    {(?P<expr_braced>) | # ${....
    (?P<expr_invalid>)
) |
^\s*%(?:
    (?P<tag_bare>[a-z]+) | # %for, %end, etc.
    (?P<tag_bare_invalid>)
)|
^\s*{%-(?P<tag_begin_ljust>[a-z]+)|  # {%-for, {%-end, etc.
{%(?:
    (?P<tag_begin>[a-z]+) | # {%for, {%end, etc.
    (?P<tag_begin_invalid>)
)
'''
_re_pattern = re.compile(_pattern, re.VERBOSE | re.IGNORECASE|re.MULTILINE)

def TextTemplate(
    source=None,
    filename=None):
    if source is None:
        source = open(filename).read()
    if filename is None:
        filename = '<string>'
    scanner = _Scanner(filename, source)
    tree = _Parser(scanner).parse()
    return kajiki.template.from_ir(tree)

class _Scanner(object):

    def __init__(self, filename, source):
        self.filename = filename
        self.source = source
        self.lineno = 1
        self.pos = 0

    def __iter__(self):
        source = self.source
        for mo in _re_pattern.finditer(source):
            start = mo.start()
            if start > self.pos:
                yield self.text(source[self.pos:start])
                self.pos = start
            groups = mo.groupdict()
            if groups['expr_braced'] is not None:
                self.pos = mo.end()
                yield self._get_braced_expr()
            elif groups['expr_named'] is not None:
                self.pos = mo.end()
                yield self.expr(groups['expr_named'])
            elif groups['tag_bare'] is not None:
                self.pos = mo.end()
                yield self._get_tag_bare(groups['tag_bare'])
            elif groups['tag_begin'] is not None:
                self.pos = mo.end()
                yield self._get_tag(groups['tag_begin'])
            elif groups['tag_begin_ljust'] is not None:
                self.pos = mo.end()
                yield self._get_tag(groups['tag_begin_ljust'])
            elif groups['tag_bare_invalid'] is not None:
                continue
            else:
                msg = 'Syntax error %s:%s' % (self.filename, self.lineno)
                for i, line in enumerate(self.source.splitlines()):
                    print '%3d %s' % (i+1, line)
                print msg
                assert False, groups
        if self.pos != len(source):
            yield self.text(source[self.pos:])

    def _get_pos(self):
        return self._pos
    def _set_pos(self, value):
        assert value >= getattr(self, '_pos', 0)
        self._pos = value
    pos = property(_get_pos, _set_pos)

    def text(self, text):
        self.lineno += text.count('\n')
        return _Text(self.filename, self.lineno, text)

    def expr(self, text):
        self.lineno += text.count('\n')
        return _Expr(self.filename, self.lineno, text)

    def tag(self, tagname, body):
        tag = _Tag(self.filename, self.lineno, tagname, body)
        self.lineno += tag.text.count('\n')
        return tag

    def _get_tag_bare(self, tagname):
        end = self.source.find('\n', self.pos)
        if end == -1:
            end = len(self.source)
        body = self.source[self.pos:end]
        self.lineno += 1
        self.pos = end+1
        return self.tag(tagname, body)

    def _get_tag(self, tagname):
        end = self.source.find('%}', self.pos)
        assert end > 0
        body = self.source[self.pos:end]
        self.pos = end+2
        if body.endswith('-'):
            body = body[:-1]
            while self.source[self.pos] in ' \t':
                self.pos += 1
        return self.tag(tagname, body)

    def _get_braced_expr(self):
        try:
            compile(self.source[self.pos:], '', 'eval')
        except SyntaxError, se:
            end = se.offset+self.pos
            text = self.source[self.pos:end-1]
            self.pos = end
            return self.expr(text)
    
class _Parser(object):

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.functions = defaultdict(list)
        self.functions['__call__()'] = []
        self.mod_py = [] # module-level python blocks
        self.iterator = iter(self.tokenizer)
        self._in_def = False
        self._is_child = False

    def parse(self):
        body = list(self._parse_body())
        self.functions['__call__()'] = body[:-1]
        defs = [ ir.DefNode(k, *v) for k,v in self.functions.iteritems() ]
        return ir.TemplateNode(self.mod_py, defs)

    def text(self, token):
        text = ''.join(_unescape_newlines(token.text))
        node = ir.TextNode(text)
        node.filename = token.filename
        node.lineno = token.lineno
        return node

    def expr(self, token):
        node = ir.ExprNode(token.text)
        node.filename = token.filename
        node.lineno = token.lineno
        return node

    def push_tok(self, token):
        self.iterator = chain([token], self.iterator)

    def _parse_body(self, *stoptags):
        while True:
            try:
                token = self.iterator.next()
                if isinstance(token, _Text):
                    yield self.text(token)
                elif isinstance(token, _Expr):
                    yield self.expr(token)
                elif isinstance(token, _Tag):
                    if token.tagname in stoptags:
                        yield token
                        break
                    parser = getattr(self, '_parse_%s' % token.tagname)
                    yield parser(token)
                else:
                    msg = 'Parse error: %r unexpected' % token
                    assert False, msg
            except StopIteration:
                yield None
                break

    def _parse_def(self, token):
        old_in_def, self._in_def = self._in_def, True
        body = list(self._parse_body('end'))
        self._in_def = old_in_def
        if self._in_def:
            return ir.InnerDefNode(token.body, *body[:-1])
        else:
            self.functions[token.body.strip()] = body[:-1]
            return None

    def _parse_call(self, token):
        b = token.body.find('(')
        e = token.body.find(')', b)
        assert e > b > -1
        arglist = token.body[b:e+1]
        call = token.body[e+1:].strip()
        body = list(self._parse_body('end'))
        return ir.CallNode(
            '$caller%s' % arglist,
            call.replace('%caller', '$caller'),
            *body[:-1])

    def _parse_if(self, token):
        body = list(self._parse_body('end', 'else'))
        stoptok = body[-1]
        if stoptok.tagname == 'else':
            self.push_tok(stoptok)
        return ir.IfNode(token.body, *body[:-1])

    def _parse_for(self, token):
        body = list(self._parse_body('end'))
        return ir.ForNode(token.body, *body[:-1])

    def _parse_switch(self, token):
        body = list(self._parse_body('end'))
        return ir.SwitchNode(token.body, *body[:-1])

    def _parse_case(self, token):
        body = list(self._parse_body('case', 'else', 'end'))
        stoptok = body[-1]
        self.push_tok(stoptok)
        return ir.CaseNode(token.body, *body[:-1])

    def _parse_else(self, token):
        body = list(self._parse_body('end'))
        return ir.ElseNode(*body[:-1])

    def _parse_extends(self, token):
        parts = shlex.split(token.body)
        fn = parts[0]
        assert len(parts) == 1
        self._is_child = True
        return ir.ExtendNode(fn)

    def _parse_import(self, token):
        parts = shlex.split(token.body)
        fn = parts[0]
        if len(parts) > 1:
            assert parts[1] == 'as'
            return ir.ImportNode(fn, parts[2])
        else:
            return ir.ImportNode(fn)

    def _parse_include(self, token):
        parts = shlex.split(token.body)
        fn = parts[0]
        assert len(parts) == 1
        return ir.IncludeNode(fn)

    def _parse_py(self, token):
        body = token.body.strip()
        if body:
            body = [ ir.TextNode(body), None ]
        else:
            body = list(self._parse_body('end'))
        node = ir.PythonNode(*body[:-1])
        if node.module_level:
            self.mod_py.append(node)
            return None
        else:
            return node

    def _parse_block(self, token):
        fname = '_kj_block_' + token.body.strip()
        decl = fname + '()'
        body = list(self._parse_body('end'))[:-1]
        self.functions[decl] = body
        if self._is_child:
            parent_block = 'parent.' + fname
            body.insert(0, ir.PythonNode(ir.TextNode('parent_block=%s' % parent_block)))
            return None
        else:
            return ir.ExprNode(decl)

class _Token(object):
    def __init__(self, filename, lineno, text):
        self.filename = filename
        self.lineno = lineno
        self.text = text

    def __repr__(self): # pragma no cover
        return '<%s %r>' % (
            self.__class__.__name__,
            self.text)

class _Expr(_Token): pass
class _Text(_Token): pass
class _Tag(_Token):
    def __init__(self, filename, lineno, tagname, body):
        self.tagname = tagname
        self.body = body
        text = tagname + ' ' + body
        super(_Tag, self).__init__(filename, lineno, text)

def _unescape_newlines(text):
    i = 0
    while i < len(text):
        if text[i] == '\\':
            if text[i+1] != '\n':
                yield text[i+1]
            i += 2
        else:
            yield text[i]
            i += 1
            
            
    
