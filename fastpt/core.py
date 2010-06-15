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
