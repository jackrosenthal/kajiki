from io import BytesIO
from tokenize import TokenError

from kajiki.ir import ExprNode, TranslatableTextNode


def gettext(s):
    return s


def extract(fileobj, keywords, comment_tags, options):
    """Babel entry point that extracts translation strings from XML templates."""
    from kajiki.template import KajikiSyntaxError
    from kajiki.xml_template import _Compiler, _DomTransformer, _Parser

    try:
        from babel.messages.extract import extract_python

        extract_expr = options.get("extract_python", False)
    except ImportError:
        extract_python = None
        extract_expr = False

    source = fileobj.read()
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    doc = _Parser(filename="<string>", source=source).parse()
    doc = _DomTransformer(doc, strip_text=options.get("strip_text", False)).transform()
    compiler = _Compiler(
        filename="<string>",
        doc=doc,
        mode=options.get("mode", "xml"),
        is_fragment=options.get("is_fragment", False),
    )
    ir = compiler.compile()
    for node in ir:
        if isinstance(node, TranslatableTextNode):
            if node.text.strip():
                yield (node.lineno, "_", node.text, [])
        elif extract_expr and isinstance(node, ExprNode):
            try:
                for e in extract_python(BytesIO(node.text.encode("utf-8")), keywords, comment_tags, options):
                    yield (node.lineno, e[1], e[2], e[3])
            except (TokenError, SyntaxError) as e:
                raise KajikiSyntaxError(e, source, "<string>", node.lineno, 0) from e
