import os
from . import template
from . import exceptions

class Loader(object):

    def __init__(self, reload=True, directory=None):
        if directory is None: directory = os.getcwd()
        self._reload = reload
        self._directory = directory
        self._cache = {}

    def load(self, href):
        path = os.path.abspath(
            os.path.join(
                self._directory,
                href))
        pt = self._cache.get(path)
        if pt is not None and self._reload:
            if os.stat(pt.filename).st_mtime > pt.timestamp:
                pt = None
        if pt is None:
            pt = self._load(path)
            self._cache[path] = pt
        return pt

    def _load(self, path):
        if not os.path.exists(path):
            raise exceptions.TemplateNotFound(
                '%r not found' % path)
        pt = template.Template(
            filename=path,
            loader=self)
        pt.compile()
        return pt

class PackageLoader(Loader):

    def __init__(self, reload=True, extensions=('html', 'xml')):
        super(PackageLoader, self).__init__(reload)
        self._extensions = extensions
        self._fn_cache = {}

    def load(self, href, package=None):
        try:
            fn, pkg = self._fn_cache[href, package]
        except KeyError:
            try:
                fn, pkg = self._find_filename(href, package)
            except ImportError:
                fn, pkg = self._find_filename(href.rsplit('.', 1)[0], package)
            self._fn_cache[href, package] = fn, pkg
        pt = super(PackageLoader, self).load(fn)
        pt.package = pkg
        return pt

    def _find_filename(self, href, package):
        if '.' not in href:
            href = '.' + href
            # raise exceptions.IllegalTemplateName(
            #     '%r must contain at least one dot' % href)
        pkg_name, pt_name = href.rsplit('.', 1)
        if pkg_name == '':
            pkg = package
        else:
            base_pkg = __import__(pkg_name)
            pkg = base_pkg
            for pkg_part in pkg_name.split('.')[1:]:
                pkg = getattr(pkg, pkg_part)
        dirname = os.path.dirname(pkg.__file__)
        attempts = []
        for ext in self._extensions:
            filename = os.path.abspath(os.path.join(
                    dirname,
                    pt_name + '.' + ext))
            attempts.append(filename)
            if os.path.exists(filename):
                return filename, pkg
        raise exceptions.TemplateNotFound(
            '%r not found, tried %r' % (href, attempts))
        
        
