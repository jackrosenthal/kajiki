import re
from fastpt import v2 as fpt

# Expressions: $foo.bar or ${foo.bar[baz]}
_expr_pattern = r'''
    %(delim)s(?:
      (?P<escaped>%(delim)s) |   # Escape sequence of two delimiters
      (?P<named>%(id)s)      |   # delimiter and a Python identifier
      {(?P<braced>%(id)s)}   |   # delimiter and a braced identifier
      (?P<invalid>)              # Other ill-formed delimiter exprs
)''' % dict(
    delim=re.escape('$'),
    id=r'[_a-z][_a-z0-9.]*')
_re_expr_pattern = re.compile(_expr_pattern, re.VERBOSE | re.IGNORECASE)

_tag_pattern = r'''
    %(delim)s(?:
      (?P<escaped>%(delim)s) |   # Escape sequence of two delimiters
      (?P<named>%(id)s)      |   # delimiter and a Python identifier
      {(?P<braced>%(id)s)}   |   # delimiter and a braced identifier
      (?P<invalid>)              # Other ill-formed delimiter exprs
)''' % dict(
    delim=re.escape('{%'),
    id=r'[_a-z][_a-z0-9.]*')
_re_expr_pattern = re.compile(_expr_pattern, re.VERBOSE | re.IGNORECASE)

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
