import os
class Loader(object):

    def __init__(self):
        self.modules = {}

    def import_(self, name):
        mod = self.modules.get(name)
        if mod: return mod
        mod = self._load(mod)
        self.modules[name] = mod
        return mod

    def default_alias_for(self, name):
        return name.replace('/', '_').replace('.', '_')

class MockLoader(Loader):

    def __init__(self, modules):
        super(MockLoader, self).__init__()
        self.modules.update(modules)
        for v in self.modules.itervalues():
            v.loader = self
            
    def default_alias_for(self, name):
        return os.path.splitext(os.path.basename(name))[0]

