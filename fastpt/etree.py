from HTMLParser import HTMLParser

def log(func):
    def inner(self, *args, **kwargs):
        print 'Calling %s(*(%r), **(%r))' % (
            func.__name__, args, kwargs)
        return func(self, *args, **kwargs)
    return inner

class HtmlParser(HTMLParser):

    def reset(self):
        self.cur_tag = None
        self.cur_data = []
        HTMLParser.reset(self)
    
    @log
    def handle_starttag(self, tag, attrs):
        pass

    # Overridable -- handle end tag
    @log
    def handle_endtag(self, tag):
        pass

    # Overridable -- handle character reference
    @log
    def handle_charref(self, name):
        pass

    # Overridable -- handle entity reference
    @log
    def handle_entityref(self, name):
        pass

    # Overridable -- handle data
    @log
    def handle_data(self, data):
        pass

    # Overridable -- handle comment
    @log
    def handle_comment(self, data):
        pass

    # Overridable -- handle declaration
    @log
    def handle_decl(self, decl):
        pass

    # Overridable -- handle processing instruction
    @log
    def handle_pi(self, data):
        pass

    @log
    def unknown_decl(self, data):
        self.error("unknown declaration: %r" % (data,))
