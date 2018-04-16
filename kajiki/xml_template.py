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
from .template import KajikiSyntaxError
from .ddict import defaultdict
from .doctype import DocumentTypeDeclaration, extract_dtd
from .entities import html5, unescape
from .html_utils import (HTML_OPTIONAL_END_TAGS, HTML_REQUIRED_END_TAGS,
                         HTML_CDATA_TAGS)
from .markup_template import QDIRECTIVES, QDIRECTIVES_DICT

impl = dom.getDOMImplementation(' ')


def XMLTemplate(source=None, filename=None, mode=None, is_fragment=False,
                encoding='utf-8', autoblocks=None, cdata_scripts=True,
                strip_text=False, base_globals=None):
    """Given XML source code of a Kajiki Templates parses and returns a template class.

    The source code is parsed to its DOM representation by :class:`._Parser`,
    which is then expanded to separate directives from tags by :class:`._DomTransformer`
    and then compiled to the *Intermediate Representation* tree by :class:`._Compiler`.

    The *Intermediate Representation* generates the Python code
    which creates a new :class:`kajiki.template._Template` subclass through
    :meth:`kajiki.template.Template`.

    The generated code is then executed to return the newly created class.

    Calling ``.render()`` on an instance of the generate class will then render the template.
    """
    if source is None:
        with open(filename, encoding=encoding) as f:
            source = f.read()  # source is a unicode string
    if filename is None:
        filename = '<string>'
    doc = _Parser(filename, source).parse()
    doc = _DomTransformer(doc, strip_text=strip_text).transform()
    ir_ = _Compiler(filename, doc, mode=mode, is_fragment=is_fragment,
                    autoblocks=autoblocks, cdata_scripts=cdata_scripts).compile()
    t = template.from_ir(ir_, base_globals=base_globals)
    return t


def annotate(gen):
    def inner(self, node, *args, **kwargs):
        for x in gen(self, node, *args, **kwargs):
            self._anno(node, x)
            yield x
    return inner


class _Compiler(object):
    """Compiles a DOM tree into Intermediate Representation :class:`kajiki.ir.TemplateNode`.

    Intermediate Representation is a tree of nodes that represent
    Python Code that should be generated to execute the template.
    """
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
        """Compile the document provided by :class:`._Parser`.

        Returns as :class:`kajiki.ir.TemplateNode` instance representing
        the whole tree of nodes as their intermediate representation.

        The returned template will include at least a ``__main__``
        function which is the document itself including a DOCTYPE and
        any function declared through ``py:def`` or as a ``py:block``.

        The ``TemplateNode`` will also include the module level
        code specified through ``<?py %``.

        If the compiled document didn't specify a DOCTYPE provides
        one at least for HTML5.

        .. note::
            As this alters the functions and mode wide code
            registries of the compiler ``compile`` should
            never be called twice or might lead to unexpected results.
        """
        if len(self.doc.childNodes) != 1:
            raise XMLTemplateCompileError('more than one children in document',
                                          self.doc, self.filename, 0)
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
                dtd = ir.TextNode(dtd.strip()+'\n')
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
        """Convert a DOM node to its intermediate representation.

        Calls specific compile functions for special nodes and any
        directive that was expanded by :meth:`._DomTransformer._expand_directives`.
        For any plain XML node forward it to :meth:`._compile_xml`.

        Automatically converts any ``autoblock`` node to a ``py:block`` directive.
        """
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
        """Compile plain XML nodes.

        When compiling a node also take care of directives that
        only modify the node itself (``py:strip``, ``py:attrs``
        and ``py:content``) as all directives wrapping the node
        and its children have already been handled by :meth:`._compile_node`.

        The provided intermediate representations include
        the node itself, its attributes and its content.

        Attributes of the node are handled through :class:`._TextCompiler`
        to ensure ${expr} expressions are handled in attributes too.

        In case the node has children (and no py:content)
        compile the children too.
        """
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
                               ir.TextNode, in_html_attr=True, compiler_instance=self)
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
        """Convert py:replace nodes to their intermediate representation."""
        yield ir.ExprNode(node.getAttribute('value'))

    @annotate
    def _compile_pi(self, node):
        """Convert <?py and <?python nodes to their intermediate representation.

        Any code identified by :class:`.ir.PythonNode` as ``module_level``
        (it starts with % character) will be registered in compiler registry
        of module wide code to be provided to be template.
        """
        body = ir.TextNode(node.data.strip())
        node = ir.PythonNode(body)
        if node.module_level:
            self.mod_py.append(node)
        else:
            yield node

    @annotate
    def _compile_import(self, node):
        """Convert py:import nodes to their intermediate representation."""
        href = node.getAttribute('href')
        if node.hasAttribute('alias'):
            yield ir.ImportNode(href, node.getAttribute('alias'))
        else:
            yield ir.ImportNode(href)

    @annotate
    def _compile_extends(self, node):
        """Convert py:extends nodes to their intermediate representation."""
        self.is_child = True
        href = node.getAttribute('href')
        yield ir.ExtendNode(href)
        for x in self._compile_nop(node):
            yield x

    @annotate
    def _compile_include(self, node):
        """Convert py:include nodes to their intermediate representation."""
        href = node.getAttribute('href')
        yield ir.IncludeNode(href)

    @annotate
    def _compile_block(self, node):
        """Convert py:block nodes to their intermediate representation.

        Any compiled block will be registered in the compiler functions
        registry to be provided to the template.
        """
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
        """Convert py:def nodes to their intermediate representation.

        Any compiled definition will be registered in the compiler functions
        registry to be provided to the template.
        """
        old_in_def, self.in_def = self.in_def, True
        body = list(self._compile_nop(node))
        self.in_def = old_in_def
        if self.in_def:
            yield ir.InnerDefNode(node.getAttribute('function'), *body)
        else:
            self.functions[node.getAttribute('function')] = body

    @annotate
    def _compile_call(self, node):
        """Convert py:call nodes to their intermediate representation."""
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
        """Compile text nodes to their intermediate representation"""
        kwargs = {}
        if node.parentNode and node.parentNode.tagName in HTML_CDATA_TAGS:
            # script and style should always be untranslatable.
            kwargs['node_type'] = ir.TextNode

        tc = _TextCompiler(self.filename, node.data, node.lineno, compiler_instance=self, **kwargs)
        for x in tc:
            yield x

    @annotate
    def _compile_comment(self, node):
        """Convert comments to their intermediate representation."""
        if not node.data.startswith('!'):
            yield ir.TextNode('<!-- %s -->' % node.data)

    @annotate
    def _compile_for(self, node):
        """Convert py:for nodes to their intermediate representation."""
        yield ir.ForNode(node.getAttribute('each'),
                         *list(self._compile_nop(node)))

    @annotate
    def _compile_with(self, node):
        """Convert py:with nodes to their intermediate representation."""
        yield ir.WithNode(node.getAttribute('vars'),
                          *list(self._compile_nop(node)))

    @annotate
    def _compile_switch(self, node):
        """Convert py:switch nodes to their intermediate representation."""
        body = []

        # Filter out empty text nodes and report unsupported nodes
        for n in self._compile_nop(node):
            if isinstance(n, ir.TextNode) and not n.text.strip():
                continue
            elif not isinstance(n, (ir.CaseNode, ir.ElseNode)):
                raise XMLTemplateCompileError(
                    'py:switch directive can only contain py:case and py:else nodes '
                    'and cannot be placed on a tag.',
                    doc=self.doc, filename=self.filename, linen=node.lineno
                )
            body.append(n)

        yield ir.SwitchNode(node.getAttribute('test'), *body)

    @annotate
    def _compile_case(self, node):
        """Convert py:case nodes to their intermediate representation."""
        yield ir.CaseNode(node.getAttribute('value'),
                          *list(self._compile_nop(node)))

    @annotate
    def _compile_if(self, node):
        """Convert py:if nodes to their intermediate representation."""
        yield ir.IfNode(node.getAttribute('test'),
                        *list(self._compile_nop(node)))

    @annotate
    def _compile_else(self, node):
        """Convert py:else nodes to their intermediate representation."""
        if (getattr(node.parentNode, 'tagName', '') != 'py:nop' and
                not node.parentNode.hasAttribute('py:switch') and
                getattr(node.previousSibling, 'tagName', '') != 'py:if'):
            raise XMLTemplateCompileError(
                'py:else directive must be inside a py:switch or directly after py:if '
                'without text or spaces in between',
                doc=self.doc, filename=self.filename, linen=node.lineno
            )

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

    This avoid spending the cost of translating empty nodes.
    '''
    if text.strip():
        return ir.TranslatableTextNode(text, guard)
    return ir.TextNode(text, guard)


class _TextCompiler(object):
    """Separates expressions such as ${some_var} from the ordinary text
    around them in the template source and generates :class:`.ir.ExprNode`
    instances and :class:`.ir.TextNode` instances accordingly.
    """
    def __init__(self, filename, source, lineno,
                 node_type=make_text_node, in_html_attr=False, compiler_instance=None):
        self.filename = filename
        self.source = source
        self.orig_lineno = lineno
        self.lineno = 0
        self.pos = 0
        self.node_type = node_type
        self.in_html_attr = in_html_attr
        self.compiler_instance = compiler_instance
        self.doc = self.compiler_instance.doc

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
        # see https://github.com/nandoflorestan/kajiki/pull/38
        # Trying to get the position of a closing } in braced expressions
        # So, self.source can be something like `1+1=${1+1} ahah`
        # in this case this function gets called only once with self.pos equal to 6
        # this function must return the result of self.expr('1+1') and must set self.pos to 9
        def py_expr(end=None):
            return self.source[self.pos:end]
        try:
            self.pos += len(py_expr()) - len(py_expr().lstrip())
            compile(py_expr(), 'find_}', 'eval')
        except SyntaxError as se:
            end = sum(
                [self.pos, se.offset] +
                [len(line) + 1
                 for idx, line in enumerate(py_expr().splitlines())
                 if idx < se.lineno - 1]
            )
            if py_expr(end)[-1] != '}':
                # for example unclosed strings
                raise XMLTemplateCompileError(
                    "Kajiki can't compile the python expression `%s`" % py_expr()[:-1],
                    doc=self.doc, filename=self.filename, linen=self.lineno)
            else:
                # if the expression ends in a } then it may be valid
                try:
                    compile(py_expr(end-1), 'check_validity', 'eval')
                except SyntaxError as se:
                    # for example + operators with a single operand
                    raise XMLTemplateCompileError(
                        "Kajiki detected an invalid python expression `%s`" % py_expr()[:-1],
                        doc=self.doc, filename=self.filename, linen=self.lineno)

            py_text = py_expr(end - 1)
            self.pos = end
            return self.expr(py_text)
        else:
            raise XMLTemplateCompileError("Braced expression not terminated",
                                          doc=self.doc, filename=self.filename, linen=self.lineno)


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
        # Deals with an HTML entity such as &nbsp; (XML itself defines very few entities.)

        # The presence of a SYSTEM doctype makes expat say "hey, that MIGHT be
        # a valid entity, better pass it along to sax and find out!"
        # (Since expat is nonvalidating, it never reads the external doctypes.)
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
        if not isinstance(getattr(tree, 'tagName', None), basestring):
            return tree

        # Squash all successive text nodes into a single one.
        merge_node = None
        for child in list(tree.childNodes):
            if isinstance(child, dom.Text) and not getattr(child, '_cdata', False):
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
        """Extract the leading and traling spaces of TextNodes to separate nodes.

        This is explicitly intended to make i18n easier, as we don't want people having
        to pay attention to spaces at being and end of text when translating it. So those
        are always extracted and only the meaningful part is preserved for translation.
        """
        for child in tree.childNodes:
            if isinstance(child, dom.Text):
                if not getattr(child, '_cdata', False):
                    if not child.data.strip():
                        # Already a totally empty node, do nothing...
                        continue

                    lstripped_data = child.data.lstrip()
                    if len(lstripped_data) != len(child.data):
                        # There is text to strip at begin, create a new text node with empty space
                        empty_text_len = len(child.data) - len(lstripped_data)
                        empty_text = child.data[:empty_text_len]
                        begin_node = child.ownerDocument.createTextNode(empty_text)
                        begin_node.lineno = child.lineno
                        begin_node.escaped = child.escaped
                        tree.insertBefore(newChild=begin_node, refChild=child)
                        child.lineno += child.data[:empty_text_len].count('\n')
                        child.data = lstripped_data

                    rstripped_data = child.data.rstrip()
                    if len(rstripped_data) != len(child.data):
                        # There is text to strip at end, create a new text node with empty space
                        empty_text_len = len(child.data) - len(rstripped_data)
                        empty_text = child.data[-empty_text_len:]
                        end_node = child.ownerDocument.createTextNode(empty_text)
                        end_node.lineno = child.lineno + child.data[:-empty_text_len].count('\n')
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
                if not getattr(child, '_cdata', False):
                    # Move lineno forward the amount of lines we are going to strip.
                    lstripped_data = child.data.lstrip()
                    child.lineno += child.data[:len(child.data)-len(lstripped_data)].count('\n')
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
            cls._expand_directives(tree, el)
            return el
        for child in tree.childNodes:
            cls._expand_directives(child, tree)
        return tree


class XMLTemplateError(Exception):
    """Base class for all Parse/Compile errors."""
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
    """Error for failed template constraints.

    This is used to signal directives in contexts where
    they are invalid or any kajiki template constraint
    that fails in the provided template code.
    """
    def __init__(self, msg, doc, filename, linen):
        super(XMLTemplateCompileError, self).__init__(
            msg, getattr(doc, '_source', ''), filename, linen, 0
        )


class XMLTemplateParseError(XMLTemplateError):
    """Error while parsing template XML.

    Signals an invalid XML error in the provided template code.
    """
