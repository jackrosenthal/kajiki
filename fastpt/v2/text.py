'''Text template syntax

Expressions:

${<python expr>}
$foo, $foo.bar

Tags:

\w*%<tagname> .* \n
{%<tagname> %}

Escaping via backslash
\$ => $
\% => %
\{ => {
\\ => \

'''
import re
from collections import defaultdict

from fastpt import v2 as fpt
from fastpt.v2 import ir

_pattern = r'''
\$(?:
    (?P<expr_escaped>\$) |      # Escape $$
    (?P<expr_named>[_a-z][_a-z0-9.]*) | # $foo.bar
    {(?P<expr_braced>) | # ${....
    (?P<expr_invalid>)
) |
%(?:
    (?P<tag_bare>[a-z]+\w) | # %for, %end, etc.
    (?P<tag_bare_invalid>)
)|
{%(?:
    (?P<tag_begin>[a-z]+\w) | # {%for, {%end, etc.
    (?P<tag_begin_ljust>-[a-z]+\w) | # {%-for, {%-end, etc.
    (?P<tag_begin_invalid>)
)|
(?P<tag_end>%}) # %}
'''
_re_pattern = re.compile(_pattern, re.VERBOSE | re.IGNORECASE)

def TextTemplate(
    source=None,
    filename=None):
    if source is None:
        source = open(filename).read()
    if filename is None:
        filename = '<string>'
    tokenizer = _Tokenizer(filename, source)
    ast = _Parser(tokenizer).parse()
    return fpt.template.from_ir(ast)

class _Parser(object):

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.functions = defaultdict(list)
        self.functions['__call__()'] = []

    def parse(self):
        body = self.functions['__call__()']
        for token in self.tokenizer:
            if isinstance(token, _Text):
                body.append(self.text(token))
            elif isinstance(token, _Expr):
                body.append(self.expr(token))
            else:
                assert False
        return ir.TemplateNode(
            *[ ir.DefNode(k, *v) for k,v in self.functions.iteritems() ])

    def text(self, token):
        node = ir.TextNode(token.text)
        node.filename = token.filename
        node.lineno = token.lineno
        return node

    def expr(self, token):
        node = ir.ExprNode(token.text)
        node.filename = token.filename
        node.lineno = token.lineno
        return node

class _Tokenizer(object):

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
            else:
                assert False
        if self.pos != len(source):
            yield self.text(source[self.pos:])

    def text(self, text):
        self.lineno += text.count('\n')
        return _Text(self.filename, self.lineno, text)

    def expr(self, text):
        self.lineno += text.count('\n')
        return _Expr(self.filename, self.lineno, text)

    def _get_braced_expr(self):
        try:
            compile(self.source[self.pos:], '', 'eval')
        except SyntaxError, se:
            end = se.offset+self.pos
            text = self.source[self.pos:end-1]
            self.pos = end
            return self.expr(text)
    
class _Token(object):
    def __init__(self, filename, lineno, text):
        self.filename = filename
        self.lineno = lineno
        self.text = text

    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            self.text)

class _Expr(_Token): pass
class _Tag(_Token): pass
class _Text(_Token): pass
