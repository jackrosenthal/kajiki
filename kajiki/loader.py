import os
import pkg_resources

class Loader(object):

    def __init__(self):
        self.modules = {}

    def import_(self, name):
        mod = self.modules.get(name)
        if mod: return mod
        mod = self._load(name)
        mod.loader = self
        self.modules[name] = mod
        return mod

    def default_alias_for(self, name):
        return os.path.splitext(os.path.basename(name))[0]

    load=import_

class MockLoader(Loader):

    def __init__(self, modules):
        super(MockLoader, self).__init__()
        self.modules.update(modules)
        for v in self.modules.itervalues():
            v.loader = self
            
class FileLoader(Loader):

    def __init__(self, base, reload=True):
        super(FileLoader, self).__init__()
        from kajiki import XMLTemplate, TextTemplate
        self.base = base
        self.extension_map = dict(
            txt=TextTemplate,
            xml=XMLTemplate,
            html=lambda *a,**kw:XMLTemplate(mode='html', *a, **kw),
            html5=lambda *a,**kw:XMLTemplate(mode='html5', *a, **kw))
        self._timestamps = {}
        self._reload = reload

    def _filename(self, name):
        return os.path.join(self.base, name)

    def import_(self, name):
        filename = self._filename(name)
        if self._reload and name in self.modules and os.stat(filename).st_mtime > self._timestamps.get(name, 0):
            del self.modules[name]
        return super(FileLoader, self).import_(name)

    def _load(self, name):
        filename = self._filename(name)
        ext = os.path.splitext(filename)[1][1:]
        self._timestamps[name] = os.stat(filename).st_mtime
        source = open(filename, 'rb').read()
        return self.extension_map[ext](source=source, filename=filename)
        
class PackageLoader(FileLoader):

    def __init__(self, reload=True):
        super(PackageLoader, self).__init__(None, reload)

    def _filename(self, name):
        package, module = name.rsplit('.', 1)
        found = dict()
        for fn in pkg_resources.resource_listdir(package, '.'):
            if fn == name: return pkg_resources.resource_filename(package, fn)
            root, ext = os.path.splitext(fn)
            if root == module:
                found[ext] = fn
        for ext in ('.xml', '.html', '.html5', '.txt'):
            if ext in found:
                return pkg_resources.resource_filename(package, found[ext])
        else:
            raise IOError, 'Unknown template %r' % name

