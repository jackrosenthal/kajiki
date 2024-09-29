import functools
import importlib.resources
import os
from pathlib import Path

from .util import default_alias_for


class Loader:
    def __init__(self):
        self.modules = {}

    def import_(self, name, *args, **kwargs):
        """Returns the template if it is already in the cache,
        else loads the template, caches it and returns it.
        """
        mod = self.modules.get(name)
        if mod:
            return mod
        mod = self._load(name, *args, **kwargs)
        mod.loader = self
        self.modules[name] = mod
        return mod

    def default_alias_for(self, name):
        return default_alias_for(name)

    @property
    def load(self):
        return self.import_


class MockLoader(Loader):
    def __init__(self, modules):
        super().__init__()
        self.modules.update(modules)
        for v in self.modules.values():
            v.loader = self


class FileLoader(Loader):
    def __init__(
        self,
        path,
        force_mode=None,
        autoescape_text=False,
        xml_autoblocks=None,
        **template_options,
    ):
        super().__init__()
        from kajiki import TextTemplate, XMLTemplate

        if isinstance(path, str):
            self.path = path.split(";")
        elif isinstance(path, Path):
            self.path = [path]
        else:
            self.path = path

        self._force_mode = force_mode
        self._autoescape_text = autoescape_text
        self._xml_autoblocks = xml_autoblocks
        self._template_options = template_options
        self.extension_map = dict(
            txt=lambda *a, **kw: TextTemplate(
                autoescape=self._autoescape_text, *a, **kw
            ),
            xml=XMLTemplate,
            html=lambda *a, **kw: XMLTemplate(mode="html", *a, **kw),
            html5=lambda *a, **kw: XMLTemplate(mode="html5", *a, **kw),
        )

    def _find_resource(self, name):
        for base in self.path:
            path = Path(base) / name
            if path.is_file():
                return path

        raise FileNotFoundError(f"{name} not found in any of {self.path}")

    def _load(self, name, encoding="utf-8", *args, **kwargs):
        """Load a template from file."""
        from kajiki import TextTemplate, XMLTemplate

        options = self._template_options.copy()
        options.update(kwargs)

        resource = self._find_resource(name)
        source = resource.read_text(encoding=encoding)
        if self._force_mode == "text":
            return TextTemplate(
                source=source,
                filename=str(resource),
                autoescape=self._autoescape_text,
                *args,
                **options,
            )
        elif self._force_mode:
            return XMLTemplate(
                source=source,
                filename=str(resource),
                mode=self._force_mode,
                autoblocks=self._xml_autoblocks,
                *args,
                **options,
            )
        else:
            ext = Path(resource.name).suffix.lstrip(".")
            return self.extension_map[ext](
                source=source, filename=str(resource), *args, **options
            )


class PackageLoader(FileLoader):
    def __init__(self, force_mode=None):
        super().__init__(None, force_mode=force_mode)

    def _find_resource(self, name):
        package, module = name.rsplit(".", 1)
        package_resource = importlib.resources.files(package)

        if package_resource.is_file():
            raise OSError(f"{package} refers to a module, not a package.")

        for resource in package_resource.iterdir():
            if not resource.is_file():
                continue

            root, ext = os.path.splitext(resource.name)
            if root != module:
                continue

            for match_ext in (".xml", ".html", ".html5", ".txt"):
                if match_ext == ext:
                    return resource

        raise FileNotFoundError("Unknown template %r" % name)
