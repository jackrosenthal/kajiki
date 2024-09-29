import re
from itertools import chain

from kajiki.util import default_alias_for, flattener, gen_name, window


def generate_python(ir):
    cur_indent = 0
    for node in flattener(ir):
        if isinstance(node, IndentNode):
            cur_indent += 4
        elif isinstance(node, DedentNode):
            cur_indent -= 4
        for line in node.py():
            yield line.indent(cur_indent)


class Node:
    def __init__(self):
        self.filename = "<string>"
        self.lineno = 0

    def py(self):  # pragma no cover
        return []

    def __iter__(self):
        yield self

    def line(self, text):
        return PyLine(self.filename, self.lineno, text)


class PassNode(Node):
    def py(self):
        # 'pass' would result in: TypeError: 'NoneType' object is not iterable
        yield self.line('yield ""')


class HierNode(Node):
    """Base for nodes that contain an indented Python block (def, for, if etc.)"""

    def __init__(self, body):
        super().__init__()
        self.body = tuple(x for x in body if x is not None)

    def body_iter(self):
        yield from optimize(flattener(map(flattener, self.body)))

    def __iter__(self):
        yield self
        yield IndentNode()
        yield from self.body_iter()
        yield DedentNode()


class IndentNode(Node):
    pass


class DedentNode(Node):
    pass


class TemplateNode(HierNode):
    """Represents the root Intermediate Representation node of a template.

    Iterating over this will generate the Python code for the class
    that provides all the functions that are part of the template including
    the ``__main__`` function that represents the template code itself.

    The generated class will then be passed to :meth:`kajiki.template.Template` to
    create a :class:`kajiki.template._Template` subclass that has the
    ``render`` method to render the template.
    """

    class TemplateTail(Node):
        def py(self):
            yield self.line("template = kajiki.Template(template)")

    def __init__(self, mod_py=None, defs=None):
        super().__init__(defs)
        if mod_py is None:
            mod_py = []
        if defs is None:
            defs = []
        self.mod_py = [x for x in mod_py if x is not None]

    def py(self):
        yield self.line("class template:")

    def __iter__(self):
        for x in flattener(self.mod_py):
            yield x
        for x in super().__iter__():
            yield x
        yield self.TemplateTail()


class ImportNode(Node):
    def __init__(self, tpl_name, alias=None):
        super().__init__()
        self.tpl_name = tpl_name
        if alias is None:
            alias = default_alias_for(tpl_name)
        self.alias = alias

    def py(self):
        yield self.line(
            f"{self.alias} = local.__kj__.import_({self.tpl_name!r}, {self.alias!r}, self.__globals__)"
        )


class IncludeNode(Node):
    def __init__(self, tpl_name):
        super().__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            f"yield local.__kj__.import_({self.tpl_name!r}, None, self.__globals__).__main__()"
        )


class ExtendNode(Node):
    def __init__(self, tpl_name):
        super().__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(f"yield local.__kj__.extend({self.tpl_name!r}).__main__()")


class DefNode(HierNode):
    prefix = "@kajiki.expose"

    def __init__(self, decl, *body):
        super().__init__(body)
        self.decl = decl

    def py(self):
        yield self.line(self.prefix)
        yield self.line(f"def {self.decl}:")

    def __iter__(self):
        yield self
        yield IndentNode()
        is_empty = True
        for x in self.body_iter():
            yield x
            is_empty = False
        if is_empty:  # In Python, a function without a body is a SyntaxError.
            yield PassNode()  # Prevent creation of a function without a body
        yield DedentNode()


class InnerDefNode(DefNode):
    prefix = "@__kj__.flattener.decorate"


class CallNode(HierNode):
    class CallTail(Node):
        def __init__(self, call):
            super().__init__()
            self.call = call

        def py(self):
            yield self.line("yield " + self.call)

    def __init__(self, caller, callee, *body):
        super().__init__(body)
        fname = gen_name()
        self.decl = caller.replace("$caller", fname)
        self.call = callee.replace("$caller", fname)

    def py(self):
        yield self.line("@__kj__.flattener.decorate")
        yield self.line(f"def {self.decl}:")

    def __iter__(self):
        yield self
        yield IndentNode()
        yield from self.body_iter()
        yield DedentNode()
        yield self.CallTail(self.call)


class ForNode(HierNode):
    def __init__(self, decl, *body):
        super().__init__(body)
        self.decl = decl

    def py(self):
        yield self.line(f"for {self.decl}:")


class WithNode(HierNode):

    assignment_pattern = re.compile(r"(?:^|;)\s*([^;=]+)=(?!=)", re.M)

    class WithTail(Node):
        def __init__(self, var_names):
            super().__init__()
            self.var_names = var_names

        def py(self):
            yield self.line(
                "({},) = local.__kj__.pop_with()".format(",".join(self.var_names))
            )
            # yield self.line('if %s == (): del %s' % (v, v))

    def __init__(self, vars, *body):
        super().__init__(body)
        assignments = []
        matches = self.assignment_pattern.finditer(vars)
        for m1, m2 in window(chain(matches, [None]), 2):
            lhs = m1.group(1).strip()
            rhs = vars[m1.end() : (m2.start() if m2 else len(vars))]
            assignments.append((lhs, rhs))

        self.vars = assignments
        self.var_names = [lhs for lhs, _ in assignments]

    def py(self):
        yield self.line(
            "local.__kj__.push_with(locals(), [{}])".format(",".join(f'"{k}"' for k in self.var_names))
        )
        for k, v in self.vars:
            yield self.line(f"{k} = {v}")

    def __iter__(self):
        yield self
        yield from self.body_iter()
        yield self.WithTail(self.var_names)


class SwitchNode(HierNode):
    class SwitchTail(Node):
        def py(self):
            yield self.line("local.__kj__.pop_switch()")

    def __init__(self, decl, *body):
        super().__init__(body)
        self.decl = decl

    def py(self):
        yield self.line(f"local.__kj__.push_switch({self.decl})")
        yield self.line("if False: pass")

    def __iter__(self):
        yield self
        yield from self.body_iter()
        yield self.SwitchTail()


class CaseNode(HierNode):
    def __init__(self, decl, *body):
        super().__init__(body)
        self.decl = decl

    def py(self):
        yield self.line(f"elif local.__kj__.case({self.decl}):")


class IfNode(HierNode):
    def __init__(self, decl, *body):
        super().__init__(body)
        self.decl = decl

    def py(self):
        yield self.line(f"if {self.decl}:")


class ElseNode(HierNode):
    def __init__(self, *body):
        super().__init__(body)

    def py(self):
        yield self.line("else:")


class TextNode(Node):
    """Node that outputs Python literals."""

    def __init__(self, text, guard=None):
        super().__init__()
        self.text = text
        self.guard = guard

    def py(self):
        s = f"yield {self.text!r}"
        if self.guard:
            yield self.line(f"if {self.guard}: {s}")
        else:
            yield self.line(s)


class TranslatableTextNode(TextNode):
    def py(self):
        text = self.text.strip()
        s = f"yield local.__kj__.gettext({self.text!r})" if text else f"yield {self.text!r}"
        if self.guard:
            yield self.line(f"if {self.guard}: {s}")
        else:
            yield self.line(s)


class ExprNode(Node):
    """Node that contains a Python expression to be evaluated when the template
    is executed.
    """

    def __init__(self, text, safe=False):
        super().__init__()
        self.text = text
        self.safe = safe

    def py(self):
        if self.safe:
            yield self.line(f"yield {self.text}")
        else:
            yield self.line(f"yield self.__kj__.escape({self.text})")


class AttrNode(HierNode):
    """Node that renders HTML/XML attributes."""

    class AttrTail(Node):
        def __init__(self, parent):
            super().__init__()
            self.p = parent

        def py(self):
            gen = self.p.genname
            x = gen_name()
            yield self.line(f"{gen} = self.__kj__.collect({gen}())")
            yield self.line(
                f"for {x} in self.__kj__.render_attrs({{{self.p.attr!r}:{gen}}}, {self.p.mode!r}):"
            )
            yield self.line(f"    yield {x}")

    def __init__(self, attr, value, guard=None, mode="xml"):
        super().__init__(value)
        self.attr = attr
        self.guard = guard
        self.mode = mode
        self.genname = gen_name()

    def py(self):
        yield self.line(f"def {self.genname}():")

    def __iter__(self):
        if self.guard:
            new_body = IfNode(
                self.guard, AttrNode(self.attr, value=self.body, mode=self.mode)
            )
            yield from new_body
        else:
            yield self
            yield IndentNode()
            if self.body:
                yield from self.body_iter()
            else:
                yield TextNode("")
            yield DedentNode()
            yield self.AttrTail(self)


class AttrsNode(Node):
    def __init__(self, attrs, guard=None, mode="xml"):
        super().__init__()
        self.attrs = attrs
        self.guard = guard
        self.mode = mode

    def py(self):
        x = gen_name()

        def _body():
            yield self.line(
                f"for {x} in self.__kj__.render_attrs({self.attrs}, {self.mode!r}):"
            )
            yield self.line(f"    yield {x}")

        if self.guard:
            yield self.line(f"if {self.guard}:")
            for line in _body():
                yield line.indent()
        else:
            for line in _body():
                yield line


class PythonNode(Node):
    def __init__(self, *body):
        super().__init__()
        self.module_level = False
        blocks = []
        for b in body:
            assert isinstance(b, TextNode)
            blocks.append(b.text)
        text = "".join(blocks)
        if text[0] == "%":
            self.module_level = True
            text = text[1:]
        self.lines = list(self._normalize(text))

    def py(self):
        for line in self.lines:
            yield self.line(line)

    def _normalize(self, text):
        if text.startswith("#\n"):
            text = text[2:]
        prefix = None
        for line in text.splitlines():
            if prefix is None:
                rest = line.lstrip()
                prefix = line[: len(line) - len(rest)]
            assert line.startswith(prefix)
            yield line[len(prefix) :]


def optimize(iter_node):
    last_node = None
    for node in iter_node:
        if (
            type(node) == TextNode
            and type(last_node) == TextNode
            and last_node.guard == node.guard
        ):
            last_node.text += node.text
            # Erase this node by not yielding it.
            continue
        if last_node is not None:
            yield last_node
        last_node = node
    if last_node is not None:
        yield last_node


class PyLine:
    def __init__(self, filename, lineno, text, indent=0):
        self._filename = filename
        self._lineno = lineno
        self._text = text
        self._indent = indent

    def indent(self, sz=4):
        return PyLine(self._filename, self._lineno, self._text, self._indent + sz)

    def __str__(self):
        return (" " * self._indent) + self._text
        if self._lineno:
            return (
                (" " * self._indent)
                + self._text
                + "\t# %s:%d" % (self._filename, self._lineno)
            )
        else:
            return (" " * self._indent) + self._text

    def __repr__(self):
        return f"{self._filename}:{self._lineno} {self}"
