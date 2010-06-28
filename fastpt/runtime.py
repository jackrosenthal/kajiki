import types
from . import core

class Runtime(object):

    def __init__(self, template, namespace, encoding='utf-8'):
        self.template = template
        self.namespace = namespace
        self.encoding = encoding
        self.stack = []
        self.slots = {}
        self.defining_slot_stack = []
        self.stack.append([])

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

    def push_slot(self, name):
        if name in self.slots:
            self.stack.append(self.slots[name])
            return False # Do not modify slot
        else:
            s = self.slots[name] = []
            self.stack.append(s)
            return True # ok to modify slot

    def pop_attr(self, name):
        top = [ s for s in self.stack.pop() if s is not None ]
        if not top: return
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

    def render(self):
        return ''.join(self.stack[0])

    def include(self, href, emit_included=False):
        pt = self.template.load(href)
        func = types.FunctionType(pt._func_code, self.namespace)
        self.push()
        saved, self.template = self.template, pt
        func(self)
        self.pop(emit_included)
        self.template = saved
        
        
