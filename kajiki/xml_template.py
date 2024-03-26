import html
import io
from codecs import open
from xml import sax
from xml.dom import minidom as dom
from xml.sax import SAXParseException

from . import ir, template
from .compiler import Compiler
from .doctype import extract_dtd
from .markup_template import QDIRECTIVES, QDIRECTIVES_DICT

impl = dom.getDOMImplementation(" ")


def XMLTemplate(
    source=None,
    filename=None,
    mode=None,
    is_fragment=False,
    encoding="utf-8",
    autoblocks=None,
    cdata_scripts=True,
    strip_text=False,
    base_globals=None,
    compiler=Compiler,
):
    """Given XML source code of a Kajiki Templates parses and returns
    a template class.

    The source code is parsed to its DOM representation by
    :class:`._Parser`, which is then expanded to separate directives
    from tags by :class:`._DomTransformer` and then compiled to the
    *Intermediate Representation* tree by :class:`._Compiler`.

    The *Intermediate Representation* generates the Python code
    which creates a new :class:`kajiki.template._Template` subclass
    through :meth:`kajiki.template.Template`.

    The generated code is then executed to return the newly created
    class.

    Calling ``.render()`` on an instance of the generate class will
    then render the template.
    """
    if source is None:
        with open(filename, encoding=encoding) as f:
            source = f.read()  # source is a unicode string
    if filename is None:
        filename = "<string>"
    doc = _Parser(filename, source).parse()
    doc = _DomTransformer(doc, strip_text=strip_text).transform()
    ir_ = compiler(
        filename,
        doc,
        mode=mode,
        is_fragment=is_fragment,
        autoblocks=autoblocks,
        cdata_scripts=cdata_scripts,
    ).compile()
    t = template.from_ir(ir_, base_globals=base_globals)
    return t



class _Parser(sax.ContentHandler):
    """Parse an XML template into a Tree of DOM Nodes.

    Nodes should then be passed to a `_Compiler` to be
    converted into the intermediate representation and
    then to Python Code.
    """

    DTD = '<!DOCTYPE kajiki SYSTEM "kajiki.dtd">'

    def __init__(self, filename, source):
        """XML defines only a few entities; HTML defines many more.
        The XML parser errors out when it finds HTML entities, unless the
        template contains a reference to an external DTD (in which case
        skippedEntity() gets called, this is what we want). In other words,
        we want to trick expat into parsing XML + HTML entities for us.
        We wouldn't force our users to declare everyday HTML entities!

        So, for the parsing stage, we detect the doctype in the template and
        replace it with our own; then in the compiling stage we put the
        user's doctype back in. The XML parser is thus tricked and nobody
        needs to know this implementation detail of Kajiki.
        """
        sax.ContentHandler.__init__(self)
        if not isinstance(source, str):
            raise TypeError("The template source must be a unicode string.")
        self._els = []
        self._doc = dom.Document()
        self._filename = filename
        # Store the original DTD in the document for the compiler to use later
        self._doc._dtd, position, source = extract_dtd(source)
        # Use our own DTD just for XML parsing
        self._source = source[:position] + self.DTD + source[position:]
        self._cdata_stack = []

    def parse(self):
        """Parse an XML/HTML document to its DOM representation."""
        self._parser = parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_external_pes, False)
        parser.setFeature(sax.handler.feature_external_ges, False)
        parser.setFeature(sax.handler.feature_namespaces, False)
        parser.setProperty(sax.handler.property_lexical_handler, self)
        parser.setContentHandler(self)
        source = sax.xmlreader.InputSource()
        # Sweet XMLReader.parse() documentation says:
        # "As a limitation, the current implementation only accepts byte
        # streams; processing of character streams is for further study."
        # So if source is unicode, we pre-encode it:
        # TODO Is this dance really necessary? Can't I just call a function?
        byts = self._source.encode("utf-8")
        source.setEncoding("utf-8")
        source.setByteStream(io.BytesIO(byts))
        source.setSystemId(self._filename)

        try:
            parser.parse(source)
        except SAXParseException as e:
            exc = XMLTemplateParseError(
                e.getMessage(),
                self._source,
                self._filename,
                e.getLineNumber(),
                e.getColumnNumber(),
            )
            exc.__cause__ = None
            raise exc

        self._doc._source = self._source
        return self._doc

    # ContentHandler implementation
    def startDocument(self):
        self._els.append(self._doc)

    def startElement(self, name, attrs):
        el = self._doc.createElement(name)
        el.lineno = self._parser.getLineNumber()
        for k, v in attrs.items():
            el.setAttribute(k, v)
        self._els[-1].appendChild(el)
        self._els.append(el)

    def endElement(self, name):
        popped = self._els.pop()
        assert name == popped.tagName

    def characters(self, content):
        should_escape = not self._cdata_stack
        if should_escape:
            content = sax.saxutils.escape(content)
        node = self._doc.createTextNode(content)
        node.lineno = self._parser.getLineNumber()
        node.escaped = should_escape
        self._els[-1].appendChild(node)

    def processingInstruction(self, target, data):
        node = self._doc.createProcessingInstruction(target, data)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def skippedEntity(self, name):
        # Deals with an HTML entity such as &nbsp; (XML itself defines
        # very few entities.)

        # The presence of a SYSTEM doctype makes expat say "hey, that
        # MIGHT be a valid entity, better pass it along to sax and
        # find out!" (Since expat is nonvalidating, it never reads the
        # external doctypes.)
        if name and name[-1] != ";":
            # In entities.html5 sometimes the entities are recorded
            # with/without semicolon. That list is copied from cPython
            # itself, and we don't want to maintain a separate diff.
            # So just ensure we ask for entities always recorded with
            # trailing semicolon.
            name += ";"
        return self.characters(html.entities.html5[name])

    def startElementNS(self, name, qname, attrs):  # pragma no cover
        raise NotImplementedError("startElementNS")

    def endElementNS(self, name, qname):  # pragma no cover
        raise NotImplementedError("startElementNS")

    def startPrefixMapping(self, prefix, uri):  # pragma no cover
        raise NotImplementedError("startPrefixMapping")

    def endPrefixMapping(self, prefix):  # pragma no cover
        raise NotImplementedError("endPrefixMapping")

    # LexicalHandler implementation
    def comment(self, text):
        node = self._doc.createComment(text)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def startCDATA(self):
        node = self._doc.createTextNode("<![CDATA[")
        node._cdata = True
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)
        self._cdata_stack.append(self._els[-1])

    def endCDATA(self):
        node = self._doc.createTextNode("]]>")
        node._cdata = True
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)
        self._cdata_stack.pop()

    def startDTD(self, name, pubid, sysid):
        self._doc.doctype = impl.createDocumentType(name, pubid, sysid)

    def endDTD(self):
        pass


class _DomTransformer(object):
    """Applies standard Kajiki transformations to a parsed document.

    Given a document generated by :class:`.Parser` it applies some
    node transformations that are necessary before applying the
    compilation steps to achieve result we usually expect.

    This includes things like squashing consecutive text nodes
    and expanding ``py:`` directives.

    The Transformer mutates the original document.
    """

    def __init__(self, doc, strip_text=True):
        self._transformed = False
        self.doc = doc
        self._strip_text = strip_text

    def transform(self):
        """Applies all the DOM transformations to the document.

        Calling this twice will do nothing as the result is persisted.
        """
        if self._transformed:
            return self.doc

        self.doc = self._expand_directives(self.doc)
        self.doc = self._merge_text_nodes(self.doc)
        self.doc = self._extract_nodes_leading_and_trailing_spaces(self.doc)
        if self._strip_text:
            self.doc = self._strip_text_nodes(self.doc)
        return self.doc

    @classmethod
    def _merge_text_nodes(cls, tree):
        """Merges consecutive TextNodes into a single TextNode.

        Nodes are replaced with a new node whose data contains the
        concatenation of all replaced nodes data.
        Any other node (including CDATA TextNodes) splits runs of TextNodes.
        """
        if isinstance(tree, dom.Document):
            cls._merge_text_nodes(tree.firstChild)
            return tree
        if not isinstance(getattr(tree, "tagName", None), str):
            return tree

        # Squash all successive text nodes into a single one.
        merge_node = None
        for child in list(tree.childNodes):
            if isinstance(child, dom.Text) and not getattr(child, "_cdata", False):
                if merge_node is None:
                    merge_node = child.ownerDocument.createTextNode(child.data)
                    merge_node.lineno = child.lineno
                    merge_node.escaped = child.escaped
                    tree.replaceChild(newChild=merge_node, oldChild=child)
                else:
                    merge_node.data = merge_node.data + child.data
                    tree.removeChild(child)
            else:
                merge_node = None

        # Apply squashing to all children of current node.
        for child in tree.childNodes:
            if not isinstance(child, dom.Text):
                cls._merge_text_nodes(child)

        return tree

    @classmethod
    def _extract_nodes_leading_and_trailing_spaces(cls, tree):
        """Extract the leading and trailing spaces of TextNodes to
        separate nodes.

        This is explicitly intended to make i18n easier, as we don't
        want people having to pay attention to spaces at being and end
        of text when translating it. So those are always extracted and
        only the meaningful part is preserved for translation.
        """
        for child in tree.childNodes:
            if isinstance(child, dom.Text):
                if not getattr(child, "_cdata", False):
                    if not child.data.strip():
                        # Already a totally empty node, do nothing...
                        continue

                    lstripped_data = child.data.lstrip()
                    if len(lstripped_data) != len(child.data):
                        # There is text to strip at begin, create a
                        # new text node with empty space
                        empty_text_len = len(child.data) - len(lstripped_data)
                        empty_text = child.data[:empty_text_len]
                        begin_node = child.ownerDocument.createTextNode(empty_text)
                        begin_node.lineno = child.lineno
                        begin_node.escaped = child.escaped
                        tree.insertBefore(newChild=begin_node, refChild=child)
                        child.lineno += child.data[:empty_text_len].count("\n")
                        child.data = lstripped_data

                    rstripped_data = child.data.rstrip()
                    if len(rstripped_data) != len(child.data):
                        # There is text to strip at end, create a new
                        # text node with empty space
                        empty_text_len = len(child.data) - len(rstripped_data)
                        empty_text = child.data[-empty_text_len:]
                        end_node = child.ownerDocument.createTextNode(empty_text)
                        end_node.lineno = child.lineno + child.data[
                            :-empty_text_len
                        ].count("\n")
                        end_node.escaped = child.escaped
                        tree.replaceChild(newChild=end_node, oldChild=child)
                        tree.insertBefore(newChild=child, refChild=end_node)
                        child.data = rstripped_data
            else:
                cls._extract_nodes_leading_and_trailing_spaces(child)
        return tree

    @classmethod
    def _strip_text_nodes(cls, tree):
        """Strips empty characters in all text nodes."""
        for child in tree.childNodes:
            if isinstance(child, dom.Text):
                if not getattr(child, "_cdata", False):
                    # Move lineno forward the amount of lines we are
                    # going to strip.
                    lstripped_data = child.data.lstrip()
                    child.lineno += child.data[
                        : len(child.data) - len(lstripped_data)
                    ].count("\n")
                    child.data = child.data.strip()
            else:
                cls._strip_text_nodes(child)
        return tree

    @classmethod
    def _expand_directives(cls, tree, parent=None):
        """Expands directives attached to nodes into separate nodes.

        This will convert all instances of::

            <div py:if="check">
            </div>

        into::

            <py:if test="check">
                <div>
                </div>
            </py:if>

        This ensures that whenever a template is processed there is no
        different between the two formats as the Compiler will always
        receive the latter.
        """
        if isinstance(tree, dom.Document):
            cls._expand_directives(tree.firstChild, tree)
            return tree
        if not isinstance(getattr(tree, "tagName", None), str):
            return tree
        if tree.tagName in QDIRECTIVES_DICT:
            tree.setAttribute(
                tree.tagName, tree.getAttribute(QDIRECTIVES_DICT[tree.tagName])
            )
            tree.tagName = "py:nop"
        if tree.tagName != "py:nop" and tree.hasAttribute("py:extends"):
            value = tree.getAttribute("py:extends")
            el = tree.ownerDocument.createElement("py:extends")
            el.setAttribute("href", value)
            el.lineno = tree.lineno
            tree.removeAttribute("py:extends")
            tree.childNodes.insert(0, el)
        for directive, attr in QDIRECTIVES:
            if not tree.hasAttribute(directive):
                continue
            value = tree.getAttribute(directive)
            tree.removeAttribute(directive)
            # nsmap = (parent is not None) and parent.nsmap or tree.nsmap
            el = tree.ownerDocument.createElement(directive)
            el.lineno = tree.lineno
            if attr:
                el.setAttribute(attr, value)
            # el.setsourceline = tree.sourceline
            parent.replaceChild(newChild=el, oldChild=tree)
            el.appendChild(tree)
            cls._expand_directives(tree, el)
            return el
        for child in tree.childNodes:
            cls._expand_directives(child, tree)
        return tree


class XMLTemplateError(template.KajikiTemplateError):
    """Base class for all Parse/Compile errors."""


class XMLTemplateCompileError(XMLTemplateError):
    """Error for failed template constraints.

    This is used to signal directives in contexts where
    they are invalid or any kajiki template constraint
    that fails in the provided template code.
    """

    def __init__(self, msg, doc, filename, linen):
        super().__init__(msg, getattr(doc, "_source", ""), filename, linen, 0)


class XMLTemplateParseError(XMLTemplateError):
    """Error while parsing template XML.

    Signals an invalid XML error in the provided template code.
    """
