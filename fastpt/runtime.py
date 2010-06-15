import types
from cStringIO import StringIO

class Runtime(object):

    def __init__(self, template, namespace, stream=None, encoding='utf-8'):
        self.template = template
        self.namespace = namespace
        if stream is None:
            stream = StringIO()
        self.stream = stream
        self.encoding = encoding
        self.stack = []
        self.slots = {}
        self.defining_slot_stack = []

    def append(self, value):
        if value is None: return
        if not isinstance(value, basestring):
            value = unicode(value)
        if not isinstance(value, str):
            value = value.encode(self.encoding)
        if self.stack:
            self.stack[-1].append(value)
        else:
            self.stream.write(value)

    def push(self):
        self.stack.append([])

    def pop(self, emit=True):
        top = self.stack.pop()
        if not emit: return
        for part in top:
            self.append(part)

    def push_slot(self, name):
        if name in self.slots:
            self.stack.append(self.slots[name])
            return False # Do not modify slot
        else:
            s = self.slots[name] = []
            self.stack.append(s)
            return True # ok to modify slot

    def escape(self, s):
        if s is None: return s
        return unicode(s).replace('<', '&lt;')

    def render(self):
        return self.stream.getvalue()

    def include(self, href):
        pt = self.template.load(href)
        pt.compile()
        func = types.FunctionType(pt._func_code, self.namespace)
        func(self)
        
        
