# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import re
from codecs import open
from xml import sax
from xml.dom import minidom as dom
from xml.sax import SAXParseException

from nine import IS_PYTHON2, basestring, str, iteritems, native_str

if IS_PYTHON2:
    from cStringIO import StringIO as BytesIO
else:
    from io import BytesIO

from . import ir
from . import template
from .ddict import defaultdict
from .doctype import DocumentTypeDeclaration, extract_dtd
from .entities import html5, unescape
from .html_utils import (HTML_OPTIONAL_END_TAGS, HTML_REQUIRED_END_TAGS,
                         HTML_CDATA_TAGS)
from .markup_template import QDIRECTIVES, QDIRECTIVES_DICT

impl = dom.getDOMImplementation(' ')


def XMLTemplate(source=None, filename=None, mode=None, is_fragment=False,
                encoding='utf-8', autoblocks=None, cdata_scripts=True):
    if source is None:
        with open(filename, encoding=encoding) as f:
            source = f.read()  # source is a unicode string
    if filename is None:
        filename = '<string>'
    doc = _Parser(filename, source).parse()
    expand(doc)
    compiler = _Compiler(filename, doc, mode=mode, is_fragment=is_fragment,
                         autoblocks=autoblocks, cdata_scripts=cdata_scripts)
    ir_ = compiler.compile()
    return template.from_ir(ir_)


def annotate(gen):
    def inner(self, node, *args, **kwargs):
        for x in gen(self, node, *args, **kwargs):
            self._anno(node, x)
            yield x
    return inner


class _Compiler(object):
    def __init__(self, filename, doc, mode=None, is_fragment=False,
                 autoblocks=None, cdata_scripts=True):
        self.filename = filename
        self.doc = doc
        self.is_fragment = is_fragment
        self.functions = defaultdict(list)
        self.functions['__main__()'] = []
        self.function_lnos = {}
        self.mod_py = []
        self.autoblocks = autoblocks or []
        self.cdata_scripts = cdata_scripts
        self.in_def = False
        self.is_child = False
        # The rendering mode is either specified in the *mode* argument,
        # or inferred from the DTD:
        self._dtd = DocumentTypeDeclaration.matching(self.doc._dtd)
        if mode:
            self.mode = mode
        elif self._dtd:
            self.mode = self._dtd.rendering_mode
        else:  # The template might contain an unknown DTD
            self.mode = 'xml'  # by default

    def compile(self):
        body = list(self._compile_node(self.doc.firstChild))
        # Never emit doctypes on fragments
        if not self.is_fragment and not self.is_child:
            if self.doc._dtd:
                dtd = self.doc._dtd
            elif self.mode == 'html5':
                dtd = '<!DOCTYPE html>'
            else:
                dtd = None
            if dtd:
                dtd = ir.TextNode(dtd)
                dtd.filename = self.filename
                dtd.lineno = 1
                body.insert(0, dtd)
        self.functions['__main__()'] = body
        defs = []
        for k, v in iteritems(self.functions):
            node = ir.DefNode(k, *v)
            node.lineno = self.function_lnos.get(k)
            defs.append(node)
        node = ir.TemplateNode(self.mod_py, defs)
        node.filename = self.filename
        node.lineno = 0
        return node

    def _anno(self, dom_node, ir_node):
        if ir_node.lineno:
            return
        ir_node.filename = self.filename
        ir_node.lineno = dom_node.lineno

    def _is_autoblock(self, node):
        if node.tagName not in self.autoblocks:
            return False

        if node.hasAttribute('py:autoblock'):
            guard = node.getAttribute('py:autoblock').lower()
            if guard not in ('false', 'true'):
                raise ValueError('py:autoblock is evaluated at compile time '
                                 'and only accepts True/False constants')
            if guard == 'false':
                # We throw away the attribute so it doesn't remain in rendered nodes.
                node.removeAttribute('py:autoblock')
                return False

        return True

    def _compile_node(self, node):
        if isinstance(node, dom.Comment):
            return self._compile_comment(node)
        elif isinstance(node, dom.Text):
            return self._compile_text(node)
        elif isinstance(node, dom.ProcessingInstruction):
            return self._compile_pi(node)
        elif self._is_autoblock(node):
            # Set the name of the block equal to the tag itself.
            node.setAttribute('name', node.tagName)
            return self._compile_block(node)
        elif node.tagName.startswith('py:'):
            # Handle directives
            compiler = getattr(
                self, '_compile_%s' % node.tagName.split(':')[-1],
                self._compile_xml)
            return compiler(node)
        else:
            return self._compile_xml(node)

    @annotate
    def _compile_xml(self, node):
        content = attrs = guard = None
        if node.hasAttribute('py:strip'):
            guard = node.getAttribute('py:strip')
            if guard == '':  # py:strip="" means yes, do strip the tag
                guard = 'False'
            else:
                guard = 'not (%s)' % guard
            node.removeAttribute('py:strip')
        yield ir.TextNode('<%s' % node.tagName, guard)
        for k, v in sorted(node.attributes.items()):
            tc = _TextCompiler(self.filename, v, node.lineno,
                               ir.TextNode, in_html_attr=True)
            v = list(tc)
            if k == 'py:content':
                content = node.getAttribute('py:content')
                continue
            elif k == 'py:attrs':
                attrs = node.getAttribute('py:attrs')
                continue
            yield ir.AttrNode(k, v, guard, self.mode)
        if attrs:
            yield ir.AttrsNode(attrs, guard, self.mode)
        if content:
            yield ir.TextNode('>', guard)
            yield ir.ExprNode(content)
            yield ir.TextNode('</%s>' % node.tagName, guard)
        else:
            if node.childNodes:
                yield ir.TextNode('>', guard)
                if self.cdata_scripts and node.tagName in HTML_CDATA_TAGS:
                    # Special behaviour for <script>, <style> tags:
                    if self.mode == 'xml':  # Start escaping
                        yield ir.TextNode('/*<![CDATA[*/')
                    # Need to unescape the contents of these tags
                    for child in node.childNodes:
                        # CDATA for scripts and styles are automatically managed.
                        if getattr(child, '_cdata', False):
                            continue
                        assert isinstance(child, dom.Text)
                        for x in self._compile_text(child):
                            if child.escaped:  # If user declared CDATA no escaping happened.
                                x.text = unescape(x.text)
                            yield x
                    if self.mode == 'xml':  # Finish escaping
                        yield ir.TextNode('/*]]>*/')
                else:
                    for cn in node.childNodes:
                        # Keep CDATA sections around if declared by user
                        if getattr(cn, '_cdata', False):
                            yield ir.TextNode(cn.data)
                            continue
                        for x in self._compile_node(cn):
                            yield x
                if not (self.mode.startswith('html')
                        and node.tagName in HTML_OPTIONAL_END_TAGS):
                    yield ir.TextNode('</%s>' % node.tagName, guard)
            elif node.tagName in HTML_REQUIRED_END_TAGS:
                yield ir.TextNode('></%s>' % node.tagName, guard)
            else:
                if self.mode.startswith('html'):
                    if node.tagName in HTML_OPTIONAL_END_TAGS:
                        yield ir.TextNode('>', guard)
                    else:
                        yield ir.TextNode('></%s>' % node.tagName, guard)
                else:
                    yield ir.TextNode('/>', guard)

    @annotate
    def _compile_replace(self, node):
        yield ir.ExprNode(node.getAttribute('value'))

    @annotate
    def _compile_pi(self, node):
        body = ir.TextNode(node.data.strip())
        node = ir.PythonNode(body)
        if node.module_level:
            self.mod_py.append(node)
        else:
            yield node

    @annotate
    def _compile_import(self, node):
        href = node.getAttribute('href')
        if node.hasAttribute('alias'):
            yield ir.ImportNode(href, node.getAttribute('alias'))
        else:
            yield ir.ImportNode(href)

    @annotate
    def _compile_extends(self, node):
        self.is_child = True
        href = node.getAttribute('href')
        yield ir.ExtendNode(href)
        for x in self._compile_nop(node):
            yield x

    @annotate
    def _compile_include(self, node):
        href = node.getAttribute('href')
        yield ir.IncludeNode(href)

    @annotate
    def _compile_block(self, node):
        fname = '_kj_block_' + node.getAttribute('name')
        decl = fname + '()'
        body = list(self._compile_nop(node))
        if not body:
            body = [ir.PassNode()]
        self.functions[decl] = body
        if self.is_child:
            parent_block = 'parent.' + fname
            body.insert(0,
                ir.PythonNode(ir.TextNode('parent_block=%s' % parent_block)))
        else:
            yield ir.ExprNode(decl)

    @annotate
    def _compile_def(self, node):
        old_in_def, self.in_def = self.in_def, True
        body = list(self._compile_nop(node))
        self.in_def = old_in_def
        if self.in_def:
            yield ir.InnerDefNode(node.getAttribute('function'), *body)
        else:
            self.functions[node.getAttribute('function')] = body

    @annotate
    def _compile_call(self, node):
        if node.childNodes[0].hasAttribute('args'):
            defn = '$caller(' + node.childNodes[0].getAttribute('args') + ')'
        else:
            defn = '$caller()'
        yield ir.CallNode(
            defn,
            node.getAttribute('function').replace('%caller', '$caller'),
            *self._compile_nop(node))

    @annotate
    def _compile_text(self, node):
        kwargs = {}
        if node.parentNode and node.parentNode.tagName in HTML_CDATA_TAGS:
            # script and style should always be untranslatable.
            kwargs['node_type'] = ir.TextNode

        tc = _TextCompiler(self.filename, node.data, node.lineno, **kwargs)
        for x in tc:
            yield x

    @annotate
    def _compile_comment(self, node):
        if not node.data.startswith('!'):
            yield ir.TextNode('<!-- %s -->' % node.data)

    @annotate
    def _compile_for(self, node):
        yield ir.ForNode(node.getAttribute('each'),
                         *list(self._compile_nop(node)))

    @annotate
    def _compile_with(self, node):
        yield ir.WithNode(node.getAttribute('vars'),
                          *list(self._compile_nop(node)))

    @annotate
    def _compile_switch(self, node):
        body = []

        # Filter out empty text nodes and report unsupported nodes
        for n in self._compile_nop(node):
            if isinstance(n, ir.TextNode) and not n.text.strip():
                continue
            elif not isinstance(n, (ir.CaseNode, ir.ElseNode)):
                raise XMLTemplateCompileError(
                    'py:with directive can only contain py:case and py:else nodes '
                    'and cannot be placed on a tag.',
                    doc=self.doc, filename=self.filename, linen=node.lineno
                )
            body.append(n)

        yield ir.SwitchNode(node.getAttribute('test'), *body)

    @annotate
    def _compile_case(self, node):
        yield ir.CaseNode(node.getAttribute('value'),
                          *list(self._compile_nop(node)))

    @annotate
    def _compile_if(self, node):
        yield ir.IfNode(node.getAttribute('test'),
                        *list(self._compile_nop(node)))

    @annotate
    def _compile_else(self, node):
        yield ir.ElseNode(
            *list(self._compile_nop(node)))

    @annotate
    def _compile_nop(self, node):
        for c in node.childNodes:
            for x in self._compile_node(c):
                yield x


def make_text_node(text, guard=None):
    '''Return a TranslatableTextNode if the text is not empty,
    otherwise a regular TextNode.
    '''
    if text.strip():
        return ir.TranslatableTextNode(text, guard)
    return ir.TextNode(text, guard)


class _TextCompiler(object):
    '''Separates expressions such as ${some_var} from the ordinary text
    around them in the template source and generates ExprNode instances and
    TextNode instances accordingly.
    '''
    def __init__(self, filename, source, lineno,
                 node_type=make_text_node, in_html_attr=False):
        self.filename = filename
        self.source = source
        self.orig_lineno = lineno
        self.lineno = 0
        self.pos = 0
        self.node_type = node_type
        self.in_html_attr = in_html_attr

    def text(self, text):
        node = self.node_type(text)
        node.lineno = self.real_lineno
        self.lineno += text.count('\n')
        return node

    def expr(self, text):
        # *safe* being True here avoids escaping twice, since
        # HTML attributes are always escaped in the end.
        node = ir.ExprNode(text, safe=self.in_html_attr)
        node.lineno = self.real_lineno
        self.lineno += text.count('\n')
        return node

    @property
    def real_lineno(self):
        return self.orig_lineno + self.lineno

    _pattern = r'''
    \$(?:
        (?P<expr_named>[_a-z][_a-z0-9.]*) | # $foo.bar
        {(?P<expr_braced>) | # ${....
        \$ # $$ -> $
    )'''
    _re_pattern = re.compile(
        _pattern, re.VERBOSE | re.IGNORECASE | re.MULTILINE)

    def __iter__(self):
        source = self.source
        for mo in self._re_pattern.finditer(source):
            start = mo.start()
            if start > self.pos:
                yield self.text(source[self.pos:start])
            self.pos = start
            groups = mo.groupdict()
            if groups['expr_braced'] is not None:
                self.pos = mo.end()
                yield self._get_braced_expr()
            elif groups['expr_named'] is not None:
                self.pos = mo.end()
                yield self.expr(groups['expr_named'])
            else:
                # handle $$ and $ followed by anything that is neither a valid
                # variable name or braced expression
                self.pos = mo.end()
                yield self.text('$')
        if self.pos != len(source):
            yield self.text(source[self.pos:])

    def _get_braced_expr(self):
        try:
            compile(self.source[self.pos:], '', 'eval')
        except SyntaxError as se:
            end = se.offset + self.pos
            text = self.source[self.pos:end - 1]
            self.pos = end
            return self.expr(text)


class _Parser(sax.ContentHandler):
    DTD = '<!DOCTYPE kajiki SYSTEM "kajiki.dtd">'

    def __init__(self, filename, source):
        '''XML defines only a few entities; HTML defines many more.
        The XML parser errors out when it finds HTML entities, unless the
        template contains a reference to an external DTD (in which case
        skippedEntity() gets called, this is what we want). In other words,
        we want to trick expat into parsing XML + HTML entities for us.
        We wouldn't force our users to declare everyday HTML entities!

        So, for the parsing stage, we detect the doctype in the template and
        replace it with our own; then in the compiling stage we put the
        user's doctype back in. The XML parser is thus tricked and nobody
        needs to know this implementation detail of Kajiki.
        '''
        if not isinstance(source, str):
            raise TypeError('The template source must be a unicode string.')
        self._els = []
        self._doc = dom.Document()
        self._filename = filename
        # Store the original DTD in the document for the compiler to use later
        self._doc._dtd, position, source = extract_dtd(source)
        # Use our own DTD just for XML parsing
        self._source = source[:position] + self.DTD + source[position:]
        self._cdata_stack = []

    def parse(self):
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
        byts = self._source.encode('utf-8')
        source.setEncoding(native_str('utf-8'))
        source.setByteStream(BytesIO(byts))
        source.setSystemId(self._filename)

        try:
            parser.parse(source)
        except SAXParseException as e:
            exc = XMLTemplateParseError(e.getMessage(), self._source, self._filename,
                                        e.getLineNumber(), e.getColumnNumber())
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
        '''Deals with an HTML entity such as &nbsp;
        (XML itself defines very few entities.)

        The presence of a SYSTEM doctype makes expat say "hey, that MIGHT be
        a valid entity, better pass it along to sax and find out!"
        (Since expat is nonvalidating, it never reads the external doctypes.)
        '''
        return self.characters(html5[name])

    def startElementNS(self, name, qname, attrs):  # pragma no cover
        raise NotImplementedError('startElementNS')

    def endElementNS(self, name, qname):  # pragma no cover
        raise NotImplementedError('startElementNS')

    def startPrefixMapping(self, prefix, uri):  # pragma no cover
        raise NotImplementedError('startPrefixMapping')

    def endPrefixMapping(self, prefix):  # pragma no cover
        raise NotImplementedError('endPrefixMapping')

    # LexicalHandler implementation
    def comment(self, text):
        node = self._doc.createComment(text)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def startCDATA(self):
        node = self._doc.createTextNode('<![CDATA[')
        node._cdata = True
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)
        self._cdata_stack.append(self._els[-1])

    def endCDATA(self):
        node = self._doc.createTextNode(']]>')
        node._cdata = True
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)
        self._cdata_stack.pop()

    def startDTD(self, name, pubid, sysid):
        self._doc.doctype = impl.createDocumentType(name, pubid, sysid)

    def endDTD(self):
        pass


def expand(tree, parent=None):
    if isinstance(tree, dom.Document):
        expand(tree.firstChild, tree)
        return tree
    if not isinstance(getattr(tree, 'tagName', None), basestring):
        return tree
    if tree.tagName in QDIRECTIVES_DICT:
        tree.setAttribute(
            tree.tagName,
            tree.getAttribute(QDIRECTIVES_DICT[tree.tagName]))
        tree.tagName = 'py:nop'
    if tree.tagName != 'py:nop' and tree.hasAttribute('py:extends'):
        value = tree.getAttribute('py:extends')
        el = tree.ownerDocument.createElement('py:extends')
        el.setAttribute('href', value)
        el.lineno = tree.lineno
        tree.removeAttribute('py:extends')
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
        expand(tree, el)
        return el
    for child in tree.childNodes:
        expand(child, tree)
    return tree


class XMLTemplateError(Exception):
    def __init__(self, msg, source, filename, linen, coln):
        super(XMLTemplateError, self).__init__(
            '[%s:%s] %s\n%s' % (filename, linen, msg, self._get_source_snippet(source, linen))
        )
        self.filename = filename
        self.linenum = linen
        self.colnum = coln

    def _get_source_snippet(self, source, linen):
        SURROUNDING = 2
        linen -= 1

        parts = []
        for i in range(SURROUNDING, 0, -1):
            parts.append('\t     %s\n' % self._get_source_line(source, linen - i))
        parts.append('\t --> %s\n' % self._get_source_line(source, linen))
        for i in range(1, SURROUNDING + 1):
            parts.append('\t     %s\n' % self._get_source_line(source, linen + i))
        return ''.join(parts)

    def _get_source_line(self, source, linen):
        if linen < 0:
            return ''

        try:
            return source.splitlines()[linen]
        except:
            return ''


class XMLTemplateCompileError(XMLTemplateError):
    def __init__(self, msg, doc, filename, linen):
        super(XMLTemplateCompileError, self).__init__(
            msg, getattr(doc, '_source', ''), filename, linen, 0
        )


class XMLTemplateParseError(XMLTemplateError):
    pass
