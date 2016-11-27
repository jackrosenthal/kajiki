# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from nine import basestring, itervalues
import os
import pkg_resources


class Loader(object):
    def __init__(self):
        self.modules = {}

    def import_(self, name, *args, **kwargs):
        '''Returns the template if it is already in the cache,
        else loads the template, caches it and returns it.
        '''
        mod = self.modules.get(name)
        if mod:
            return mod
        mod = self._load(name, *args, **kwargs)
        mod.loader = self
        self.modules[name] = mod
        return mod

    def default_alias_for(self, name):
        return os.path.splitext(os.path.basename(name))[0]

    @property
    def load(self):
        return self.import_


class MockLoader(Loader):
    def __init__(self, modules):
        super(MockLoader, self).__init__()
        self.modules.update(modules)
        for v in itervalues(self.modules):
            v.loader = self


class FileLoader(Loader):
    def __init__(self, path, reload=True, force_mode=None,
                 autoescape_text=False, xml_autoblocks=None,
                 **template_options):
        super(FileLoader, self).__init__()
        from kajiki import XMLTemplate, TextTemplate
        if isinstance(path, basestring):
            self.path = path.split(';')
        else:
            self.path = path
        self._timestamps = {}
        self._reload = reload
        self._force_mode = force_mode
        self._autoescape_text = autoescape_text
        self._xml_autoblocks = xml_autoblocks
        self._template_options = template_options
        self.extension_map = dict(
            txt=lambda *a, **kw: TextTemplate(
                autoescape=self._autoescape_text, *a, **kw),
            xml=XMLTemplate,
            html=lambda *a, **kw: XMLTemplate(mode='html', *a, **kw),
            html5=lambda *a, **kw: XMLTemplate(mode='html5', *a, **kw))

    def _filename(self, name):
        for base in self.path:
            fn = os.path.join(base, name)
            if os.path.exists(fn):
                return fn
        return None

    def import_(self, name, *args, **kwargs):
        filename = self._filename(name)
        if self._reload and name in self.modules:
            mtime = os.stat(filename).st_mtime
            if mtime > self._timestamps.get(name, 0):
                del self.modules[name]
        return super(FileLoader, self).import_(name, *args, **kwargs)

    def _load(self, name, encoding='utf-8', *args, **kwargs):
        '''Text templates are read in text mode and XML templates are read in
        binary mode. Thus, the ``encoding`` argument is only used for reading
        text template files.
        '''
        from kajiki import XMLTemplate, TextTemplate
        options = self._template_options.copy()
        options.update(kwargs)

        filename = self._filename(name)
        self._timestamps[name] = os.stat(filename).st_mtime
        if self._force_mode == 'text':
            return TextTemplate(filename=filename,
                autoescape=self._autoescape_text, *args, **options)
        elif self._force_mode:
            return XMLTemplate(filename=filename,
                               mode=self._force_mode,
                               autoblocks=self._xml_autoblocks,
                               *args, **options)
        else:
            ext = os.path.splitext(filename)[1][1:]
            return self.extension_map[ext](
                source=None, filename=filename, *args, **options)


class PackageLoader(FileLoader):
    def __init__(self, reload=True, force_mode=None):
        super(PackageLoader, self).__init__(None, reload, force_mode)

    def _filename(self, name):
        package, module = name.rsplit('.', 1)
        found = dict()
        for fn in pkg_resources.resource_listdir(package, '.'):
            if fn == name:
                return pkg_resources.resource_filename(package, fn)
            root, ext = os.path.splitext(fn)
            if root == module:
                found[ext] = fn
        for ext in ('.xml', '.html', '.html5', '.txt'):
            if ext in found:
                return pkg_resources.resource_filename(package, found[ext])
        else:
            raise IOError('Unknown template %r' % name)
