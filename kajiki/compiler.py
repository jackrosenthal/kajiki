import collections
import html
import re
from xml.dom import minidom as dom

from kajiki import ir
from kajiki.doctype import DocumentTypeDeclaration
from kajiki.html_utils import HTML_CDATA_TAGS, HTML_OPTIONAL_END_TAGS, HTML_REQUIRED_END_TAGS


def annotate(gen):
    def inner(self, node, *args, **kwargs):
        for x in gen(self, node, *args, **kwargs):
            self._anno(node, x)
            yield x

    return inner


def make_text_node(text, guard=None):
    """Return a TranslatableTextNode if the text is not empty,
    otherwise a regular TextNode.

    This avoid spending the cost of translating empty nodes.
    """
    if text.strip():
        return ir.TranslatableTextNode(text, guard)
    return ir.TextNode(text, guard)


class Compiler(object):
    """Compiles a DOM tree into IR :class:`kajiki.ir.TemplateNode`.

    Intermediate Representation is a tree of nodes that represent
    Python Code that should be generated to execute the template.
    """

    def __init__(
        self,
        filename,
        doc,
        mode=None,
        is_fragment=False,
        autoblocks=None,
        cdata_scripts=True,
    ):
        self.filename = filename
        self.doc = doc
        self.is_fragment = is_fragment
        self.functions = collections.defaultdict(list)
        self.functions["__main__()"] = []
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
            self.mode = "xml"  # by default

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
        templateNodes = [
            n for n in self.doc.childNodes if not isinstance(n, dom.Comment)
        ]
        if len(templateNodes) != 1:
            raise XMLTemplateCompileError(
                "expected a single root node in document", self.doc, self.filename, 0
            )
        body = list(self._compile_node(templateNodes[0]))
        # Never emit doctypes on fragments
        if not self.is_fragment and not self.is_child:
            if self.doc._dtd:
                dtd = self.doc._dtd
            elif self.mode == "html5":
                dtd = "<!DOCTYPE html>"
            else:
                dtd = None
            if dtd:
                dtd = ir.TextNode(dtd.strip() + "\n")
                dtd.filename = self.filename
                dtd.lineno = 1
                body.insert(0, dtd)
        self.functions["__main__()"] = body
        defs = []
        for k, v in self.functions.items():
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

        if node.hasAttribute("py:autoblock"):
            guard = node.getAttribute("py:autoblock").lower()
            if guard not in ("false", "true"):
                raise ValueError(
                    "py:autoblock is evaluated at compile time "
                    "and only accepts True/False constants"
                )
            if guard == "false":
                # We throw away the attribute so it doesn't remain in rendered nodes.
                node.removeAttribute("py:autoblock")
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
            node.setAttribute("name", node.tagName)
            return self._compile_block(node)
        elif node.tagName.startswith("py:"):
            # Handle directives
            compiler = getattr(
                self, "_compile_%s" % node.tagName.split(":")[-1], self._compile_xml
            )
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

        Attributes of the node are handled through :class:`.TextCompiler`
        to ensure ${expr} expressions are handled in attributes too.

        In case the node has children (and no py:content)
        compile the children too.
        """
        content = attrs = guard = None
        if node.hasAttribute("py:strip"):
            guard = node.getAttribute("py:strip")
            if guard == "":  # py:strip="" means yes, do strip the tag
                guard = "False"
            else:
                guard = "not (%s)" % guard
            node.removeAttribute("py:strip")
        yield ir.TextNode("<%s" % node.tagName, guard)
        for k, v in sorted(node.attributes.items()):
            tc = TextCompiler(
                self.filename,
                v,
                node.lineno,
                ir.TextNode,
                in_html_attr=True,
                compiler_instance=self,
            )
            v = list(tc)
            if k == "py:content":
                content = node.getAttribute("py:content")
                continue
            elif k == "py:attrs":
                attrs = node.getAttribute("py:attrs")
                continue
            yield ir.AttrNode(k, v, guard, self.mode)
        if attrs:
            yield ir.AttrsNode(attrs, guard, self.mode)
        if content:
            yield ir.TextNode(">", guard)
            yield ir.ExprNode(content)
            yield ir.TextNode("</%s>" % node.tagName, guard)
        else:
            if node.childNodes:
                yield ir.TextNode(">", guard)
                if self.cdata_scripts and node.tagName in HTML_CDATA_TAGS:
                    # Special behaviour for <script>, <style> tags:
                    if self.mode == "xml":  # Start escaping
                        yield ir.TextNode("/*<![CDATA[*/")
                    # Need to unescape the contents of these tags
                    for child in node.childNodes:
                        # CDATA for scripts and styles are automatically managed.
                        if getattr(child, "_cdata", False):
                            continue
                        assert isinstance(child, dom.Text)
                        for x in self._compile_text(child):
                            if (
                                child.escaped
                            ):  # If user declared CDATA no escaping happened.
                                x.text = html.unescape(x.text)
                            yield x
                    if self.mode == "xml":  # Finish escaping
                        yield ir.TextNode("/*]]>*/")
                else:
                    for cn in node.childNodes:
                        # Keep CDATA sections around if declared by user
                        if getattr(cn, "_cdata", False):
                            yield ir.TextNode(cn.data)
                            continue
                        for x in self._compile_node(cn):
                            yield x
                if not (
                    self.mode.startswith("html")
                    and node.tagName in HTML_OPTIONAL_END_TAGS
                ):
                    yield ir.TextNode("</%s>" % node.tagName, guard)
            elif node.tagName in HTML_REQUIRED_END_TAGS:
                yield ir.TextNode("></%s>" % node.tagName, guard)
            else:
                if self.mode.startswith("html"):
                    if node.tagName in HTML_OPTIONAL_END_TAGS:
                        yield ir.TextNode(">", guard)
                    else:
                        yield ir.TextNode("></%s>" % node.tagName, guard)
                else:
                    yield ir.TextNode("/>", guard)

    @annotate
    def _compile_replace(self, node):
        """Convert py:replace nodes to their intermediate representation."""
        yield ir.ExprNode(node.getAttribute("value"))

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
        href = node.getAttribute("href")
        if node.hasAttribute("alias"):
            yield ir.ImportNode(href, node.getAttribute("alias"))
        else:
            yield ir.ImportNode(href)

    @annotate
    def _compile_extends(self, node):
        """Convert py:extends nodes to their intermediate representation."""
        self.is_child = True
        href = node.getAttribute("href")
        yield ir.ExtendNode(href)
        for x in self._compile_nop(node):
            yield x

    @annotate
    def _compile_include(self, node):
        """Convert py:include nodes to their intermediate representation."""
        href = node.getAttribute("href")
        yield ir.IncludeNode(href)

    @annotate
    def _compile_block(self, node):
        """Convert py:block nodes to their intermediate representation.

        Any compiled block will be registered in the compiler functions
        registry to be provided to the template.
        """
        fname = "_kj_block_" + node.getAttribute("name")
        decl = fname + "()"
        body = list(self._compile_nop(node))
        if not body:
            body = [ir.PassNode()]
        self.functions[decl] = body
        if self.is_child:
            parent_block = "parent." + fname
            body.insert(0, ir.PythonNode(ir.TextNode("parent_block=%s" % parent_block)))
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
            yield ir.InnerDefNode(node.getAttribute("function"), *body)
        else:
            self.functions[node.getAttribute("function")] = body

    @annotate
    def _compile_call(self, node):
        """Convert py:call nodes to their intermediate representation."""
        if node.childNodes[0].hasAttribute("args"):
            defn = "$caller(" + node.childNodes[0].getAttribute("args") + ")"
        else:
            defn = "$caller()"
        yield ir.CallNode(
            defn,
            node.getAttribute("function").replace("%caller", "$caller"),
            *self._compile_nop(node)
        )

    @annotate
    def _compile_text(self, node):
        """Compile text nodes to their intermediate representation"""
        kwargs = {}
        if node.parentNode and node.parentNode.tagName in HTML_CDATA_TAGS:
            # script and style should always be untranslatable.
            kwargs["node_type"] = ir.TextNode

        tc = TextCompiler(
            self.filename, node.data, node.lineno, compiler_instance=self, **kwargs
        )
        for x in tc:
            yield x

    @annotate
    def _compile_comment(self, node):
        """Convert comments to their intermediate representation."""
        if not node.data.startswith("!"):
            yield ir.TextNode("<!-- %s -->" % node.data)

    @annotate
    def _compile_for(self, node):
        """Convert py:for nodes to their intermediate representation."""
        yield ir.ForNode(node.getAttribute("each"), *list(self._compile_nop(node)))

    @annotate
    def _compile_with(self, node):
        """Convert py:with nodes to their intermediate representation."""
        yield ir.WithNode(node.getAttribute("vars"), *list(self._compile_nop(node)))

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
                    "py:switch directive can only contain py:case and py:else nodes "
                    "and cannot be placed on a tag.",
                    doc=self.doc,
                    filename=self.filename,
                    linen=node.lineno,
                )
            body.append(n)

        yield ir.SwitchNode(node.getAttribute("test"), *body)

    @annotate
    def _compile_case(self, node):
        """Convert py:case nodes to their intermediate representation."""
        yield ir.CaseNode(node.getAttribute("value"), *list(self._compile_nop(node)))

    @annotate
    def _compile_if(self, node):
        """Convert py:if nodes to their intermediate representation."""
        yield ir.IfNode(node.getAttribute("test"), *list(self._compile_nop(node)))

    @annotate
    def _compile_else(self, node):
        """Convert py:else nodes to their intermediate representation."""
        if (
            getattr(node.parentNode, "tagName", "") != "py:nop"
            and not node.parentNode.hasAttribute("py:switch")
            and getattr(node.previousSibling, "tagName", "") != "py:if"
        ):
            raise XMLTemplateCompileError(
                "py:else directive must be inside a py:switch or directly after py:if "
                "without text or spaces in between",
                doc=self.doc,
                filename=self.filename,
                linen=node.lineno,
            )

        yield ir.ElseNode(*list(self._compile_nop(node)))

    @annotate
    def _compile_nop(self, node):
        for c in node.childNodes:
            for x in self._compile_node(c):
                yield x


class TextCompiler(object):
    """Separates expressions such as ${some_var} from the ordinary text
    around them in the template source and generates :class:`.ir.ExprNode`
    instances and :class:`.ir.TextNode` instances accordingly.
    """

    def __init__(
        self,
        filename,
        source,
        lineno,
        node_type=make_text_node,
        in_html_attr=False,
        compiler_instance=None,
    ):
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
        self.lineno += text.count("\n")
        return node

    def expr(self, text):
        # *safe* being True here avoids escaping twice, since
        # HTML attributes are always escaped in the end.
        node = ir.ExprNode(text, safe=self.in_html_attr)
        node.lineno = self.real_lineno
        self.lineno += text.count("\n")
        return node

    @property
    def real_lineno(self):
        return self.orig_lineno + self.lineno

    _pattern = r"""
    \$(?:
        (?P<expr_named>[_a-z][_a-z0-9.]*) | # $foo.bar
        {(?P<expr_braced>) | # ${....
        \$ # $$ -> $
    )"""
    _re_pattern = re.compile(_pattern, re.VERBOSE | re.IGNORECASE | re.MULTILINE)

    def __iter__(self):
        source = self.source
        for mo in self._re_pattern.finditer(source):
            start = mo.start()
            if start > self.pos:
                yield self.text(source[self.pos : start])
            self.pos = start
            groups = mo.groupdict()
            if groups["expr_braced"] is not None:
                self.pos = mo.end()
                yield self._get_braced_expr()
            elif groups["expr_named"] is not None:
                self.pos = mo.end()
                yield self.expr(groups["expr_named"])
            else:
                # handle $$ and $ followed by anything that is neither a valid
                # variable name or braced expression
                self.pos = mo.end()
                yield self.text("$")
        if self.pos != len(source):
            yield self.text(source[self.pos :])

    def _get_braced_expr(self):
        from kajiki.xml_template import XMLTemplateCompileError

        # see https://github.com/nandoflorestan/kajiki/pull/38
        # Trying to get the position of a closing } in braced expressions
        # So, self.source can be something like `1+1=${1+1} ahah`
        # in this case this function gets called only once with
        # self.pos equal to 6 this function must return the result of
        # self.expr('1+1') and must set self.pos to 9
        def py_expr(end=None):
            return self.source[self.pos : end]

        try:
            self.pos += len(py_expr()) - len(py_expr().lstrip())
            compile(py_expr(), "find_}", "eval")
        except SyntaxError as se:
            end = sum(
                [self.pos, se.offset]
                + [
                    len(line) + 1
                    for idx, line in enumerate(py_expr().splitlines())
                    if idx < se.lineno - 1
                ]
            )
            if py_expr(end)[-1] != "}":
                # for example unclosed strings
                raise XMLTemplateCompileError(
                    "Kajiki can't compile the python expression `%s`" % py_expr()[:-1],
                    doc=self.doc,
                    filename=self.filename,
                    linen=self.lineno,
                )
            else:
                # if the expression ends in a } then it may be valid
                try:
                    compile(py_expr(end - 1), "check_validity", "eval")
                except SyntaxError:
                    # for example + operators with a single operand
                    raise XMLTemplateCompileError(
                        "Kajiki detected an invalid python expression `%s`"
                        % py_expr()[:-1],
                        doc=self.doc,
                        filename=self.filename,
                        linen=self.lineno,
                    )

            py_text = py_expr(end - 1)
            self.pos = end
            return self.expr(py_text)
        else:
            raise XMLTemplateCompileError(
                "Braced expression not terminated",
                doc=self.doc,
                filename=self.filename,
                linen=self.lineno,
            )
