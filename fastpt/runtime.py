import types
from contextlib import contextmanager
from collections import defaultdict
from . import core

class Runtime(object):

    def __init__(self, template, namespace, encoding='utf-8'):
        self.template = template
        self.namespace = namespace
        self.encoding = encoding
        self.stack = []
        self.slots = defaultdict(list)
        self.defining_slot_stack = []
        self.stack.append([])
        self._slot_definition_enabled = True

    @contextmanager
    def slot_definition_disabled(self):
        self._slot_definition_enabled = False
        yield
        self._slot_definition_enabled = True
        

    def doctype(self):
        for decl in self.template._tree.declarations:
            self.stack[-1].append('<!%s>' % decl)
        return
        docinfo = self.template._tree.docinfo
        if docinfo.public_id:
            self.stack[-1].append('<!DOCTYPE %s PUBLIC "%s" "%s">' % (
                    docinfo.root_name, docinfo.public_id, docinfo.system_url))

    def append(self, value):
        if value is None: return
        vtype = type(value)
        if vtype == core.Markup:
            self.stack[-1].append(value.encode(self.encoding))
            return
        elif hasattr(value, '__html__'):
            self.stack[-1].append(value.__html__().encode(self.encoding))
            return
        if vtype == unicode:
            value = value.encode(self.encoding)
        elif vtype != str:
            try:
                value = str(value)
            except:
                value = unicode(value).encode(self.encoding)
        value = value.replace('&', '&amp;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        self.stack[-1].append(value)

    def push(self):
        self.stack.append([])

    def pop(self, emit=True):
        top = self.stack.pop()
        if not emit: return
        for part in top:
            self.stack[-1].append(part)

    def def_slot(self, name, func):
        def _call_slot():
            tpl, func = self.slots[name][-1]
            with self.slot_definition_disabled():
                return func(self)
        if self._slot_definition_enabled or not self.slots[name]:
            self.slots[name].append((self.template, func))
        self.stack[-1].append(_call_slot)

    def super_slot(self, name, depth):
        self.stack[-1].append(lambda: self.slots[name][depth](self, depth))

    def pop_attr(self, name):
        top = [ s for s in self.stack.pop() if s is not None ]
        if not top: return
        if name == 'xmlns': return
        self.stack[-1].append(' ' + name + '="')
        for part in top:
            self.append(part)
        self.stack[-1].append('"')

    def escape(self, s):
        if s is None: return s
        return unicode(s).replace('<', '&lt;')

    def attrs(self, d):
        if d is None: return
        if isinstance(d, dict):
            d = d.iteritems()
        for k,v in d:
            if v is None: continue
            self.append(' %s="%s"' % (k, unicode(v)))

    def generate(self):
        def gen(it):
            for x in it:
                if callable(x):
                    for xx in gen(x()):
                        yield xx
                else:
                    yield x
        return gen(self.stack.pop())

    def render(self):
        return ''.join(self.generate())

    def include(self, href, emit_included=False):
        pt = self.template.load(href)
        func = types.FunctionType(pt._func_code, self.namespace)
        self.push()
        saved, self.template = self.template, pt
        func(self)
        self.pop(emit_included)
        self.template = saved
        
    def call_slot(self, href, name):
        pt = self.template.load(href)
        func = types.FunctionType(pt._func_code, self.namespace)
        runtime = Runtime(pt, dict(self.namespace))
        runtime.push()
        func(runtime)
        def _call_slot():
            tpl, func = runtime.slots[name][-1]
            with self.slot_definition_disabled():
                return func(self)
        self.stack[-1].append(_call_slot)
        
        
