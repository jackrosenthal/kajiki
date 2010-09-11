from cStringIO import StringIO
from xml import sax
from htmllib import HTMLParser
from xml.dom import minidom as dom

from .markup_template import QDIRECTIVES, QDIRECTIVES_DICT

def XMLTemplate(
    source=None,
    filename=None):
    if source is None:
        source = open(filename).read()
    if filename is None:
        filename = '<string>'
    dom_tree = _Parser(filename, source).parse()
    print dom_tree.toxml()
    expanded_dom_tree = _expand(dom_tree)
    ir = _Compiler(expanded_dom_tree).compile()
    return fpt.template.from_ir(tree)

class _Parser(sax.ContentHandler):

    def __init__(self, filename, source):
        self._filename = filename
        self._source = source
        self._doc = None
        self._els = []

    def parse(self):
        self._parser = parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_external_pes, False)
        parser.setFeature(sax.handler.feature_external_ges, False)
        parser.setFeature(sax.handler.feature_namespaces, False)
        parser.setProperty(sax.handler.property_lexical_handler, self)
        parser.setContentHandler(self)
        parser.parse(StringIO(self._source))
        return self._doc

    ## ContentHandler implementation
    def startDocument(self):
        self._doc = dom.Document()
        self._els.append(self._doc)

    def startElement(self, name, attrs):
        el = self._doc.createElement(name)
        el.lineno = self._parser.getLineNumber()
        for k,v in attrs.items():
            el.setAttribute(k,v)
        self._els[-1].appendChild(el)
        self._els.append(el)

    def endElement(self, name):
        popped = self._els.pop()
        assert name == popped.tagName

    def characters(self, content):
        node = self._doc.createTextNode(content)
        self._els[-1].appendChild(node)

    def processingInstruction(self, target, data):
        node = self._doc.createProcessingInstruction(target, data)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def skippedEntity(self, name):
        content = unicode(HTMLParser.entitydefs[name], 'latin-1')
        return self.characters(content)

    def startElementNS(self, name, qname, attrs): # pragma no cover
        raise NotImplementedError, 'startElementNS'

    def endElementNS(self, name, qname):# pragma no cover
        raise NotImplementedError, 'startElementNS'

    def startPrefixMapping(self, prefix, uri):# pragma no cover
        raise NotImplemented, 'startPrefixMapping'

    def endPrefixMapping(self, prefix):# pragma no cover
        raise NotImplemented, 'endPrefixMapping'

    # LexicalHandler implementation
    def comment(self, text):
        node = self._doc.createComment(text)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def startCDATA(self): pass
    def endCDATA(self): pass
    def startDTD(self, name, pubid, sysid): pass
    def endDTD(self): pass

def expand(tree, parent=None):
    if not isinstance(tree.tagName, basestring): return tree
    if tree.tagName in QDIRECTIVES_DICT:
        tree.setAttribute(
            tree.tag,
            tree.getAttribute(QDIRECTIVES_DICT[tree.tag]))
        tree.tagName = 'py:nop'
    for directive, attr in QDIRECTIVES:
        if not tree.hasAttribute(directive): continue
        value = tree.getAttribute(directive)
        tree.removeAttribute(directive)
        # nsmap = (parent is not None) and parent.nsmap or tree.nsmap
        el = tree.ownerDocument.createElement(directive)
        el.lineno = tree.lineno
        if attr:
            el.setAttribute(attr, value)
        # el.setsourceline = tree.sourceline
        if parent is None:
            tree.parentNode.replaceChild(newChild=el, oldChild=tree)
        else:
            parent.replaceChild(newChild=el, oldChild=tree)
        el.appendChild(tree)
        expand(tree, el)
        return el
    for child in tree.childNodes:
        expand(child, tree)
    return tree

