from cStringIO import StringIO

class Runtime(object):

    def __init__(self, stream=None, encoding='utf-8'):
        if stream is None:
            stream = StringIO()
        self.stream = stream
        self.encoding = encoding

    def push(self, s):
        if not isinstance(s, unicode):
            s = unicode(s)
        self.stream.write(s.encode(self.encoding))

    def escape(self, s):
        return unicode(s).replace('<', '&lt;')

    def render(self):
        return self.stream.getvalue()

                        
