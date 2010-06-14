NS='http://g.4dz8.com/'
NS_DECL='xmlns:py="%s"' % NS
DIRECTIVES=[
    ('def','function'),
    ('when', 'test'),
    ('otherwise',''),
    ('for','each'),
    ('if','test'),
    ('choose', 'test'),
    ('with', 'vars'),
    ('replace', 'value') ]
QDIRECTIVES = [
    ('{%s}%s' % (NS, k), v)
    for k,v in DIRECTIVES ]
