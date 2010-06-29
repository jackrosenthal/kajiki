import sys

XI_NS="http://www.w3.org/2001/XInclude"
NS="http://genshi.edgewall.org/"
NS_DECL='xmlns:py="%s"' % NS
DIRECTIVES=[
    ('def','function'),
    ('when', 'test'),
    ('otherwise',''),
    ('for','each'),
    ('if','test'),
    ('choose', 'test'),
    ('with', 'vars'),
    ('replace', 'value'),
    ('slot', 'name'),
    ('extends', 'href'),]
QDIRECTIVES = [
    ('{%s}%s' % (NS, k), v)
    for k,v in DIRECTIVES ]
QDIRECTIVES_DICT = dict(QDIRECTIVES)

class Markup(unicode): pass

def value_of(name, default=None):
    f = sys._getframe(1)
    try:
        return f.f_locals[name]
    except KeyError:
        return f.f_globals.get(name, default)

def defined(name):
    f = sys._getframe(1)
    return name in f.f_locals or name in f.f_globals
