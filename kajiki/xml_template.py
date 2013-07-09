# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import re
from xml import sax
from xml.dom import minidom as dom

from nine import IS_PYTHON2, basestring, str, iteritems, nimport
HTMLParser = nimport('html.parser:HTMLParser')
entitydefs = nimport('html.entities:entitydefs')

if IS_PYTHON2:
    from cStringIO import StringIO as BytesIO
else:
    from io import BytesIO

from . import ir
from . import template
from .ddict import defaultdict
from .markup_template import QDIRECTIVES, QDIRECTIVES_DICT
from .html_utils import HTML_OPTIONAL_END_TAGS

impl = dom.getDOMImplementation(' ')

_pattern = r'''
\$(?:
    (?P<expr_escaped>\$) |      # Escape $$
    (?P<expr_named>[_a-z][_a-z0-9.]*) | # $foo.bar
    {(?P<expr_braced>) | # ${....
    (?P<expr_invalid>)
)'''
_re_pattern = re.compile(_pattern, re.VERBOSE | re.IGNORECASE | re.MULTILINE)


def XMLTemplate(source=None, filename=None, **kw):
    if 'mode' in kw:
        mode = kw['mode']
        force_mode = True
    else:
        mode = 'xml'
        force_mode = False
    is_fragment = kw.pop('is_fragment', False)
    if source is None:
        with open(filename) as f:
            source = f.read()  # source is a bytes instance
    if filename is None:
        filename = '<string>'
    doc = _Parser(filename, source).parse()
    expand(doc)
    compiler = _Compiler(filename, doc, mode, is_fragment, force_mode)
    ir_ = compiler.compile()
    return template.from_ir(ir_)


def annotate(gen):
    def inner(self, node, *args, **kwargs):
        for x in gen(self, node, *args, **kwargs):
            self._anno(node, x)
            yield x
    return inner


class _Compiler(object):
    mode_lookup = {
        'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd': 'xml',
        'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd': 'xml',
        'http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd': 'xml',
        'http://www.w3.org/TR/html4/strict.dtd': 'html',
        'http://www.w3.org/TR/html4/loose.dtd': 'html',
        'http://www.w3.org/TR/html4/frameset.dtd': 'html',
    }

    def __init__(self, filename, doc, mode='xml', is_fragment=False,
                 force_mode=False):
        self.filename = filename
        self.doc = doc
        self.mode = mode
        self.functions = defaultdict(list)
        self.functions['__main__()'] = []
        self.function_lnos = {}
        self.mod_py = []
        self.in_def = False
        self.is_child = False
        self.is_fragment = is_fragment
        if not force_mode and self.doc.doctype:
            if self.doc.doctype.toxml().lower() == '<!doctype html>':
                self.mode = 'html5'
            elif self.doc.doctype.systemId is None:
                self.mode = 'html'
            else:
                self.mode = self.mode_lookup.get(
                    self.doc.doctype.systemId, 'xml')

    def compile(self):
        body = list(self._compile_node(self.doc.firstChild))
        # Never emit doctypes on fragments
        if not self.is_fragment and not self.is_child:
            if self.mode == 'xml' and self.doc.doctype:
                dt = ir.TextNode(self.doc.doctype.toxml())
                dt.filename = self.filename
                dt.lineno = 1
                body.insert(0, dt)
            elif self.mode == 'html5':
                dt = ir.TextNode('<!DOCTYPE html>')
                dt.filename = self.filename
                dt.lineno = 1
                body.insert(0, dt)
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

    def _compile_node(self, node):
        if isinstance(node, dom.Comment):
            return self._compile_comment(node)
        elif isinstance(node, dom.Text):
            return self._compile_text(node)
        elif isinstance(node, dom.ProcessingInstruction):
            return self._compile_pi(node)
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
            guard = 'not (%s)' % node.getAttribute('py:strip')
            node.removeAttribute('py:strip')
        yield ir.TextNode('<%s' % node.tagName, guard)
        for k, v in sorted(node.attributes.items()):
            tc = _TextCompiler(self.filename, v, node.lineno,
                               ir.TextNode)
            v = list(tc)
            # v = ''.join(n.text for n in tc)
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
                for cn in node.childNodes:
                    for x in self._compile_node(cn):
                        yield x
                if not (self.mode.startswith('html')
                        and node.tagName in HTML_OPTIONAL_END_TAGS):
                    yield ir.TextNode('</%s>' % node.tagName, guard)
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
        tc = _TextCompiler(self.filename, node.data, node.lineno)
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
        # Filter out text nodes
        body = [x for x in self._compile_nop(node)
                if not isinstance(x, ir.TextNode)]
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


class _TextCompiler(object):
    def __init__(self, filename, source, lineno,
                 node_type=ir.TranslatableTextNode):
        self.filename = filename
        self.source = source
        self.orig_lineno = lineno
        self.lineno = 0
        self.pos = 0
        self.node_type = node_type

    def text(self, text):
        node = self.node_type(text)
        node.lineno = self.real_lineno
        self.lineno += text.count('\n')
        return node

    def expr(self, text):
        node = ir.ExprNode(text)
        node.lineno = self.real_lineno
        self.lineno += text.count('\n')
        return node

    @property
    def real_lineno(self):
        return self.orig_lineno + self.lineno

    def __iter__(self):
        source = self.source
        for mo in _re_pattern.finditer(source):
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
            elif groups['expr_escaped'] is not None:
                self.pos = mo.end()
                yield self.text('$')
            else:
                msg = 'Syntax error %s:%s' % (self.filename, self.real_lineno)
                for i, line in enumerate(self.source.splitlines()):
                    print('%3d %s' % (i + 1, line))
                print(msg)
                assert False, groups
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


def doctype_with_html_entities():
    '''Returns a string containing lots of entity declarations
    (such as nbsp, lt, gt etc.)
    to be inserted into the input XML file.
    '''
    alist = ['<!DOCTYPE kajiki [']
    for k, v in sorted(list(iteritems(entitydefs))):
        if isinstance(v, bytes):
            # Python docs specifically say this is in latin-1.
            v = v.decode('latin-1')  # get unicode
        alist.append('<!ENTITY {0} "{1}">'.format(k, v))
    alist.append(']>')
    return '\n'.join(alist)


HTML_ENTITIES = '''<!DOCTYPE IGNORE [
    <!ENTITY AElig "Æ">
    <!ENTITY Aacute "Á">
    <!ENTITY Acirc "Â">
    <!ENTITY Agrave "À">
    <!ENTITY Alpha "Α">
    <!ENTITY Aring "Å">
    <!ENTITY Atilde "Ã">
    <!ENTITY Auml "Ä">
    <!ENTITY Beta "Β">
    <!ENTITY Ccedil "Ç">
    <!ENTITY Chi "Χ">
    <!ENTITY Dagger "‡">
    <!ENTITY Delta "Δ">
    <!ENTITY ETH "Ð">
    <!ENTITY Eacute "É">
    <!ENTITY Ecirc "Ê">
    <!ENTITY Egrave "È">
    <!ENTITY Epsilon "Ε">
    <!ENTITY Eta "Η">
    <!ENTITY Euml "Ë">
    <!ENTITY Gamma "Γ">
    <!ENTITY Iacute "Í">
    <!ENTITY Icirc "Î">
    <!ENTITY Igrave "Ì">
    <!ENTITY Iota "Ι">
    <!ENTITY Iuml "Ï">
    <!ENTITY Kappa "Κ">
    <!ENTITY Lambda "Λ">
    <!ENTITY Mu "Μ">
    <!ENTITY Ntilde "Ñ">
    <!ENTITY Nu "Ν">
    <!ENTITY OElig "Œ">
    <!ENTITY Oacute "Ó">
    <!ENTITY Ocirc "Ô">
    <!ENTITY Ograve "Ò">
    <!ENTITY Omega "Ω">
    <!ENTITY Omicron "Ο">
    <!ENTITY Oslash "Ø">
    <!ENTITY Otilde "Õ">
    <!ENTITY Ouml "Ö">
    <!ENTITY Phi "Φ">
    <!ENTITY Pi "Π">
    <!ENTITY Prime "″">
    <!ENTITY Psi "Ψ">
    <!ENTITY Rho "Ρ">
    <!ENTITY Scaron "Š">
    <!ENTITY Sigma "Σ">
    <!ENTITY THORN "Þ">
    <!ENTITY Tau "Τ">
    <!ENTITY Theta "Θ">
    <!ENTITY Uacute "Ú">
    <!ENTITY Ucirc "Û">
    <!ENTITY Ugrave "Ù">
    <!ENTITY Upsilon "Υ">
    <!ENTITY Uuml "Ü">
    <!ENTITY Xi "Ξ">
    <!ENTITY Yacute "Ý">
    <!ENTITY Yuml "Ÿ">
    <!ENTITY Zeta "Ζ">
    <!ENTITY aacute "á">
    <!ENTITY acirc "â">
    <!ENTITY acute "´">
    <!ENTITY aelig "æ">
    <!ENTITY agrave "à">
    <!ENTITY alefsym "ℵ">
    <!ENTITY alpha "α">
    <!ENTITY and "∧">
    <!ENTITY ang "∠">
    <!ENTITY aring "å">
    <!ENTITY asymp "≈">
    <!ENTITY atilde "ã">
    <!ENTITY auml "ä">
    <!ENTITY bdquo "„">
    <!ENTITY beta "β">
    <!ENTITY brvbar "¦">
    <!ENTITY bull "•">
    <!ENTITY cap "∩">
    <!ENTITY ccedil "ç">
    <!ENTITY cedil "¸">
    <!ENTITY cent "¢">
    <!ENTITY chi "χ">
    <!ENTITY circ "ˆ">
    <!ENTITY clubs "♣">
    <!ENTITY cong "≅">
    <!ENTITY copy "©">
    <!ENTITY crarr "↵">
    <!ENTITY cup "∪">
    <!ENTITY curren "¤">
    <!ENTITY dArr "⇓">
    <!ENTITY dagger "†">
    <!ENTITY darr "↓">
    <!ENTITY deg "°">
    <!ENTITY delta "δ">
    <!ENTITY diams "♦">
    <!ENTITY divide "÷">
    <!ENTITY eacute "é">
    <!ENTITY ecirc "ê">
    <!ENTITY egrave "è">
    <!ENTITY empty "∅">
    <!ENTITY emsp " ">
    <!ENTITY ensp " ">
    <!ENTITY epsilon "ε">
    <!ENTITY equiv "≡">
    <!ENTITY eta "η">
    <!ENTITY eth "ð">
    <!ENTITY euml "ë">
    <!ENTITY euro "€">
    <!ENTITY exist "∃">
    <!ENTITY fnof "ƒ">
    <!ENTITY forall "∀">
    <!ENTITY frac12 "½">
    <!ENTITY frac14 "¼">
    <!ENTITY frac34 "¾">
    <!ENTITY frasl "⁄">
    <!ENTITY gamma "γ">
    <!ENTITY ge "≥">
    <!ENTITY gt ">">
    <!ENTITY hArr "⇔">
    <!ENTITY harr "↔">
    <!ENTITY hearts "♥">
    <!ENTITY hellip "…">
    <!ENTITY iacute "í">
    <!ENTITY icirc "î">
    <!ENTITY iexcl "¡">
    <!ENTITY igrave "ì">
    <!ENTITY image "ℑ">
    <!ENTITY infin "∞">
    <!ENTITY int "∫">
    <!ENTITY iota "ι">
    <!ENTITY iquest "¿">
    <!ENTITY isin "∈">
    <!ENTITY iuml "ï">
    <!ENTITY kappa "κ">
    <!ENTITY lArr "⇐">
    <!ENTITY lambda "λ">
    <!ENTITY lang "〈">
    <!ENTITY laquo "«">
    <!ENTITY larr "←">
    <!ENTITY lceil "⌈">
    <!ENTITY ldquo "“">
    <!ENTITY le "≤">
    <!ENTITY lfloor "⌊">
    <!ENTITY lowast "∗">
    <!ENTITY loz "◊">
    <!ENTITY lrm "‎">
    <!ENTITY lsaquo "‹">
    <!ENTITY lsquo "‘">
    <!ENTITY lt "<">
    <!ENTITY macr "¯">
    <!ENTITY mdash "—">
    <!ENTITY micro "µ">
    <!ENTITY middot "·">
    <!ENTITY minus "−">
    <!ENTITY mu "μ">
    <!ENTITY nabla "∇">
    <!ENTITY nbsp " ">
    <!ENTITY ndash "–">
    <!ENTITY ne "≠">
    <!ENTITY ni "∋">
    <!ENTITY not "¬">
    <!ENTITY notin "∉">
    <!ENTITY nsub "⊄">
    <!ENTITY ntilde "ñ">
    <!ENTITY nu "ν">
    <!ENTITY oacute "ó">
    <!ENTITY ocirc "ô">
    <!ENTITY oelig "œ">
    <!ENTITY ograve "ò">
    <!ENTITY oline "‾">
    <!ENTITY omega "ω">
    <!ENTITY omicron "ο">
    <!ENTITY oplus "⊕">
    <!ENTITY or "∨">
    <!ENTITY ordf "ª">
    <!ENTITY ordm "º">
    <!ENTITY oslash "ø">
    <!ENTITY otilde "õ">
    <!ENTITY otimes "⊗">
    <!ENTITY ouml "ö">
    <!ENTITY para "¶">
    <!ENTITY part "∂">
    <!ENTITY permil "‰">
    <!ENTITY perp "⊥">
    <!ENTITY phi "φ">
    <!ENTITY pi "π">
    <!ENTITY piv "ϖ">
    <!ENTITY plusmn "±">
    <!ENTITY pound "£">
    <!ENTITY prime "′">
    <!ENTITY prod "∏">
    <!ENTITY prop "∝">
    <!ENTITY psi "ψ">
    <!ENTITY rArr "⇒">
    <!ENTITY radic "√">
    <!ENTITY rang "〉">
    <!ENTITY raquo "»">
    <!ENTITY rarr "→">
    <!ENTITY rceil "⌉">
    <!ENTITY rdquo "”">
    <!ENTITY real "ℜ">
    <!ENTITY reg "®">
    <!ENTITY rfloor "⌋">
    <!ENTITY rho "ρ">
    <!ENTITY rlm "‏">
    <!ENTITY rsaquo "›">
    <!ENTITY rsquo "’">
    <!ENTITY sbquo "‚">
    <!ENTITY scaron "š">
    <!ENTITY sdot "⋅">
    <!ENTITY sect "§">
    <!ENTITY shy "­">
    <!ENTITY sigma "σ">
    <!ENTITY sigmaf "ς">
    <!ENTITY sim "∼">
    <!ENTITY spades "♠">
    <!ENTITY sub "⊂">
    <!ENTITY sube "⊆">
    <!ENTITY sum "∑">
    <!ENTITY sup "⊃">
    <!ENTITY sup1 "¹">
    <!ENTITY sup2 "²">
    <!ENTITY sup3 "³">
    <!ENTITY supe "⊇">
    <!ENTITY szlig "ß">
    <!ENTITY tau "τ">
    <!ENTITY there4 "∴">
    <!ENTITY theta "θ">
    <!ENTITY thetasym "ϑ">
    <!ENTITY thinsp " ">
    <!ENTITY thorn "þ">
    <!ENTITY tilde "˜">
    <!ENTITY times "×">
    <!ENTITY trade "™">
    <!ENTITY uArr "⇑">
    <!ENTITY uacute "ú">
    <!ENTITY uarr "↑">
    <!ENTITY ucirc "û">
    <!ENTITY ugrave "ù">
    <!ENTITY uml "¨">
    <!ENTITY upsih "ϒ">
    <!ENTITY upsilon "υ">
    <!ENTITY uuml "ü">
    <!ENTITY weierp "℘">
    <!ENTITY xi "ξ">
    <!ENTITY yacute "ý">
    <!ENTITY yen "¥">
    <!ENTITY yuml "ÿ">
    <!ENTITY zeta "ζ">
    <!ENTITY zwj "‍">
    <!ENTITY zwnj "‌">
]>'''.encode('utf-8')  # <!ENTITY amp "&"> <!ENTITY quot """>


class _Parser(sax.ContentHandler):
    def __init__(self, filename, source, accept_html_entities=True):
        self._filename = filename
        self._source = source
        self._doc = None
        self._els = []
        self._accept_html_entities = accept_html_entities

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
        if isinstance(self._source, bytes):
            byts = self._source
        else:
            byts = self._source.encode('utf-8')
            source.setEncoding('utf-8')
        if self._accept_html_entities:
            byts = HTML_ENTITIES + byts
        source.setByteStream(BytesIO(byts))
        source.setSystemId(self._filename)
        parser.parse(source)
        return self._doc

    # ContentHandler implementation
    def startDocument(self):
        self._doc = dom.Document()
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
        content = sax.saxutils.escape(content)
        node = self._doc.createTextNode(content)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def processingInstruction(self, target, data):
        node = self._doc.createProcessingInstruction(target, data)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def skippedEntity(self, name):
        '''Deals with an HTML entity such as &nbsp;'''
        content = entitydefs[name]
        # The value is bytes in Python 2 and str in Python 3, so:
        if isinstance(content, bytes):
            # Python docs specifically say this is in latin-1.
            content = str(content, 'latin-1')  # get unicode
        return self.characters(content)

    def startElementNS(self, name, qname, attrs):  # pragma no cover
        raise NotImplementedError('startElementNS')

    def endElementNS(self, name, qname):  # pragma no cover
        raise NotImplementedError('startElementNS')

    def startPrefixMapping(self, prefix, uri):  # pragma no cover
        raise NotImplemented('startPrefixMapping')

    def endPrefixMapping(self, prefix):  # pragma no cover
        raise NotImplemented('endPrefixMapping')

    # LexicalHandler implementation
    def comment(self, text):
        node = self._doc.createComment(text)
        node.lineno = self._parser.getLineNumber()
        self._els[-1].appendChild(node)

    def startCDATA(self):
        pass

    def endCDATA(self):
        pass

    def startDTD(self, name, pubid, sysid):
        if name == 'IGNORE':
            return
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
