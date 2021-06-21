HTML_EMPTY_ATTRS = set([
    'checked',
    'disabled',
    'readonly',
    'multiple',
    'selected',
    'nohref',
    'ismap',
    'declare',
    'defer',
])
HTML_OPTIONAL_END_TAGS = set([
    'area',
    'base',
    'br',
    'col',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param'
])
HTML_REQUIRED_END_TAGS = set(['script'])
HTML_CDATA_TAGS = set(('script', 'style'))
