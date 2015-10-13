# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from .ir import TranslatableTextNode


def gettext(s):
    return s


def extract(fileobj, keywords, comment_tags, options):
    '''Babel entry point that extracts translation strings from XML templates.
    '''
    from .xml_template import _Parser, _Compiler, expand
    source = fileobj.read()
    if isinstance(source, bytes):
        source = source.decode('utf-8')
    doc = _Parser(filename='<string>', source=source).parse()
    expand(doc)
    compiler = _Compiler(filename='<string>', doc=doc,
                         mode=options.get('mode', 'xml'),
                         is_fragment=options.get('is_fragment', False))
    ir = compiler.compile()
    for node in ir:
        if isinstance(node, TranslatableTextNode):
            if node.text.strip():
                for line in node.text.split('\n'):
                    yield (node.lineno, '_', line, [])
