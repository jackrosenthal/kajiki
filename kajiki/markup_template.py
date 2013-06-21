# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

DIRECTIVES = [
    ('def', 'function'),
    ('call', 'function'),
    ('case', 'value'),
    ('else', ''),
    ('for', 'each'),
    ('if', 'test'),
    ('switch', 'test'),
    ('with', 'vars'),
    ('replace', 'value'),
    ('block', 'name'),
    ('extends', 'href'),
]
QDIRECTIVES = [
    ('py:%s' % (k,), v) for k, v in DIRECTIVES
]
QDIRECTIVES_DICT = dict(QDIRECTIVES)
