from HTMLParser import HTMLParser

def log(func):
    def inner(self, *args, **kwargs):
        print 'Calling %s(*(%r), **(%r))' % (
            func.__name__, args, kwargs)
        return func(self, *args, **kwargs)
    return inner

def parse(fp, parser):
    parser.reset()
    while True:
        block = fp.read(4096)
        if block: parser.feed(block)
        else: break
    parser.close()
    return parser.tree

class Tree(object):
    __slots__ = ('children','declarations', 'text', 'nsmap')

    def __init__(self):
        self.children = []
        self.declarations = []
        self.text = ''
        self.nsmap = {}

    def append(self, node):
        node.parent = self
        self.children.append(node)
        node.fixup_nsmap()

    def getroot(self):
        for ch in self.children:
            if isinstance(ch, Element): return ch
        return None

class Node(object):
    __slots__ = ('tag', 'sourceline','parent', 'tail', 'children')

    def __init__(self):
        self.sourceline = None
        self.parent = None
        self.tail = ''
        self.children = []

    def __iter__(self):
        return iter(self.children)

class Element(Node):
    __slots__ = ('tag', 'attrib', 'text', 'children', 'nsmap')

    def __init__(self, tag, attrib=None):
        super(Element, self).__init__()
        if isinstance(attrib, list):
            attrib = dict(attrib)
        self.tag = tag
        self.attrib = attrib or {}
        self.text = ''
        self.nsmap = {}

    def replace(self, old, new):
        new.parent = self
        old_children = self.children
        self.children = [
            new if ch == old else ch
            for ch in self.children ]
        assert len(old_children) == len(self.children)

    def append(self, node):
        node.parent = self
        self.children.append(node)
        node.fixup_nsmap()

    def __iter__(self):
        return iter(self.children)

    def __setitem__(self, k, v):
        self.children[k] = v

    def __getitem__(self, k):
        return self.children[k]

    def __unicode__(self):
        attrib = [''] + [ '%s="%s"' % (k,v) for k,v in self.attrib.iteritems() ]
        l = [ u'<%s%s>\n  %s' % (self.tag, ' '.join(attrib), self.text.strip()) ]
        for ch in self.children:
            l.append('  ' + unicode(ch).replace('\n', '\n  '))
        l.append(u'</%s>%s' % (self.tag, self.tail.strip()))
        return u'\n'.join(l)

    def fixup_nsmap(self):
        old_nsmap = self.nsmap
        self.nsmap = dict(self.parent.nsmap)
        self.nsmap.update(old_nsmap)
        nsmap = self.nsmap
        new_attrib = []
        # Look for new declarations
        for k,v in self.attrib.iteritems():
            if k.startswith('xmlns:'):
                nsmap[k.split(':', 1)[-1]] = v
            elif k == 'xmlns':
                nsmap[None] = v
            else:
                new_attrib.append((k,v))
        # Perform mapping
        self.tag = self._map_ns(self.tag)
        self.attrib = dict(
            (self._map_ns(k), v) for k,v in new_attrib)

    def _map_ns(self, old):
        if '{' in old: return old
        if ':' not in old: return old
        prefix, suffix = old.split(':', 1)
        return '{%s}%s' % (self.nsmap[prefix], suffix)

class ProcessingInstruction(Node):
    __slots__ = ('target','text')

    def __init__(self, data):
        super(ProcessingInstruction, self).__init__()
        self.tag = ProcessingInstruction
        self.target, self.text = data.split(' ', 1)
        if self.text.endswith('?'):
            self.text = self.text[:-1]

    def __unicode__(self):
        return '<?%s %s?>' % (self.target, self.text)

class Comment(Node):
    __slots__ = ('data','tail')

    def __init__(self, data):
        super(Comment, self).__init__()
        self.tag = Comment
        self.data = data

    def __unicode__(self):
        return '<!--%s -->' % (self.data,)

class HtmlParser(HTMLParser):

    def reset(self):
        self.tree = Tree()
        self.tag_stack = [self.tree]
        HTMLParser.reset(self)

    @property
    def cur(self):
        return self.tag_stack[-1]
    
    def handle_starttag(self, tag, attrs):
        el = Element(tag, attrs)
        el.sourceline = self.getpos()[0]
        self.cur.append(el)
        self.tag_stack.append(el)

    def handle_endtag(self, tag):
        self.tag_stack.pop()

    def handle_charref(self, name):
        self._handle_text(name)

    def handle_entityref(self, name):
        self._handle_text(name)

    def handle_data(self, data):
        self._handle_text(data)

    def _handle_text(self, text):
        if self.cur.children:
            self.cur.children[-1].tail += text
        else:
            self.cur.text += text

    def handle_comment(self, data):
        c = Comment(data)
        c.sourceline = self.getpos()[0]
        self.cur.append(c)

    def handle_decl(self, decl):
        self.tree.declarations.append(decl)

    def handle_pi(self, data):
        pi = ProcessingInstruction(data)
        pi.sourceline = self.getpos()[0]
        pi.parent = self.cur
        self.cur.append(pi)

    def unknown_decl(self, data):
        self.error("unknown declaration: %r" % (data,))
