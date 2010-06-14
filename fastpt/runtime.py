from cStringIO import StringIO

class Runtime(object):

    def __init__(self, stream=None, encoding='utf-8'):
        if stream is None:
            stream = StringIO()
        self.stream = stream
        self.encoding = encoding
        self.stack = []

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

    def pop(self):
        for part in self.stack.pop():
            self.append(part)

    def escape(self, s):
        if s is None: return s
        return unicode(s).replace('<', '&lt;')

    def render(self):
        return self.stream.getvalue()

                        
