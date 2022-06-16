DIRECTIVES = [
    ("def", "function"),
    ("call", "function"),
    ("case", ("value", "matching")),
    ("else", ""),
    ("for", "each"),
    ("if", "test"),
    ("switch", "test"),
    ("with", "vars"),
    ("replace", "value"),
    ("block", "name"),
    ("extends", "href"),
]
QDIRECTIVES = [("py:%s" % (k,), v) for k, v in DIRECTIVES]
QDIRECTIVES_DICT = dict(QDIRECTIVES)
