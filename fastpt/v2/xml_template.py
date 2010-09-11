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
        self._dom = None
        self._els = []

    def parse(self):
        parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_external_pes, False)
        parser.setFeature(sax.handler.feature_external_ges, False)
        parser.setFeature(sax.handler.feature_namespaces, False)
        parser.setContentHandler(self)
        parser.parse(StringIO(self._source))
        return self._doc

    def startDocument(self):
        self._doc = dom.Document()
        self._els.append(self._doc)

    def startElement(self, name, attrs):
        el = self._doc.createElement(name)
        for k,v in attrs.items():
            el.setAttribute(k,v)
        self._els[-1].appendChild(el)
        self._els.append(el)

    def endElement(self, name):
        popped = self._els.pop()
        assert name == popped.tagName

    def startElementNS(self, name, qname, attrs):
        raise NotImplementedError, 'startElementNS'

    def endElementNS(self, name, qname):
        raise NotImplementedError, 'startElementNS'

    def characters(self, content):
        node = self._doc.createTextNode(content)
        self._els[-1].appendChild(node)

    def processingInstruction(self, target, data):
        node = self._doc.createProcessingInstruction(target, data)
        self._els[-1].appendChild(node)

    def skippedEntity(self, name):
        content = unicode(HTMLParser.entitydefs[name], 'latin-1')
        return self.characters(content)

    def startPrefixMapping(self, prefix, uri):
        raise NotImplemented, 'startPrefixMapping'

    def endPrefixMapping(self, prefix):
        raise NotImplemented, 'endPrefixMapping'

def expand(tree, parent=None):
    if not isinstance(tree.tagName, basestring): return tree
    if tree.tagName in QDIRECTIVES_DICT:
        tree.attributes[tree.tag] = tree.attributes.pop(QDIRECTIVES_DICT[tree.tag])
        tree.tag = 'py:nop'
    for directive, attr in QDIRECTIVES:
        if not tree.hasAttribute(directive): continue
        value = tree.getAttribute(directive)
        tree.removeAttribute(directive)
        # nsmap = (parent is not None) and parent.nsmap or tree.nsmap
        el = tree.ownerDocument.createElement(directive)
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
    new_children = []
    for child in tree.childNodes:
        new_children.append(expand(child, tree))
    for ch in tree.childNodes:
        tree.removeChild(ch)
    for ch in new_children:
        tree.appendChild(ch)
    return tree

