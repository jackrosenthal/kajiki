import os
class Loader(object):

    def __init__(self):
        self.modules = {}

    def import_(self, name):
        mod = self.modules.get(name)
        if mod: return mod
        mod = self._load(name)
        self.modules[name] = mod
        return mod

    def default_alias_for(self, name):
        return os.path.splitext(os.path.basename(name))[0]

class MockLoader(Loader):

    def __init__(self, modules):
        super(MockLoader, self).__init__()
        self.modules.update(modules)
        for v in self.modules.itervalues():
            v.loader = self
            
class FileLoader(Loader):

    def __init__(self, base):
        super(FileLoader, self).__init__()
        from kajiki import XMLTemplate, TextTemplate
        self.base = base
        self.extension_map = dict(
            txt=TextTemplate,
            xml=XMLTemplate,
            html=lambda *a,**kw:XMLTemplate(*a, mode='html', **kw),
            html5=lambda *a,**kw:XMLTemplate(*a, mode='html5', **kw))

    def _load(self, name):
        filename = os.path.join(self.base, name)
        ext = os.path.splitext(name)[1][1:]
        source = open(filename, 'rb').read()
        return self.extension_map[ext](source=source, filename=filename)
        
