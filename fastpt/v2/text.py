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
from fastpt import v2 as fpt

_pattern = r'''
\$(?:
    (?P<expr_escaped>\$) |      # Escape $$
    (?P<expr_named>[_a-z][_a-z.]*) | # $foo.bar
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
_re_pattern = re.compile(_pattern)

def TextTemplate(
    source=None,
    filename=None):
    if source is None:
        source = open(filename).read()
    if filename is None:
        filename = '<string>'
    tokenstream = _tokenize(filename, source)
    # return fpt.template.from_ir(ir)
    return None
    
def _tokenize(filename, source):
    last_pos = 0
    for mo in _re_pattern.finditer(source):
        start=  mo.start()
        if start > last_pos:
            yield _Text(filename, 0, source[last_pos:start])
            last_pos = start
        groups = mo.groupdict()
        
        print mo.groupdict()
        import pdb; pdb.set_trace()

class _Token(object):
    def __init__(self, filename, lineno, text):
        self.filename = filename
        self.lineno = lineno
        self.text = text

class _Expr(_Token): pass
class _Tag(_Token): pass
class _Text(_Token): pass
