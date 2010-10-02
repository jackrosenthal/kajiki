from babel.messages.extract import extract_python

from .ir import TranslatableTextNode

def gettext(s):
    return s

def extract(fileobj, keywords, comment_tags, options):
    from .xml_template import _Parser, _Compiler, expand
    text = fileobj.read()
    doc = _Parser('<string>', text).parse()
    expand(doc)
    compiler = _Compiler(
        '<string>', doc,
        options.get('mode', 'xml'),
        is_fragment=options.get('is_fragment', False),
        force_mode=options.get('force_mode', False))
    ir_ = compiler.compile()
    for node in ir_:
        if isinstance(node, TranslatableTextNode):
            if node.text.strip():
                for line in node.text.split('\n'):
                    x = node.lineno, '_',  line, []
                    yield x
