class Loader(object):

    def __init__(self):
        self.modules = {}

    def import_(self, name):
        mod = self.modules.get(name)
        if mod: return mod
        mod = self._load(mod)
        self.modules[name] = mod
        return mod

class MockLoader(Loader):

    def __init__(self, modules):
        super(MockLoader, self).__init__()
        self.modules.update(modules)
        for v in self.modules.itervalues():
            v.loader = self
            

