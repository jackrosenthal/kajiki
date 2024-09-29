from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

from kajiki.util import default_alias_for


class Loader:
    def __init__(self, reload=False):  # noqa: FBT002
        self._reload = reload
        self.modules = {}

    def import_(self, name, **kwargs):
        """Returns the template if it is already in the cache,
        else loads the template, caches it and returns it.
        """
        mod = self.modules.get(name)
        if not self._reload and mod:
            return mod
        mod = self._load(name, **kwargs)
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
        reload=False,  # noqa: FBT002
        force_mode=None,
        autoescape_text=False,  # noqa: FBT002
        xml_autoblocks=None,
        **template_options,
    ):
        super().__init__(reload=reload)
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
        self.extension_map = {
            "txt": lambda **kw: TextTemplate(autoescape=self._autoescape_text, **kw),
            "xml": XMLTemplate,
            "html": lambda **kw: XMLTemplate(mode="html", **kw),
            "html5": lambda **kw: XMLTemplate(mode="html5", **kw),
        }

    def _filename(self, name: str) -> str | Path | None:
        """Get the filename of the requested resource."""
        for base in self.path:
            path = Path(base) / name
            if path.is_file():
                return path

        msg = f"{name} not found in any of {self.path}"
        raise FileNotFoundError(msg)

    def _find_resource(self, name: str) -> Path:
        """Locate the loadable resource and return a Path to it."""
        filename = self._filename(name)
        if not filename:
            msg = f"{self!r}._filename returned {filename!r}"
            raise FileNotFoundError(msg)
        path = Path(filename)
        if not path.is_file():
            msg = f"{filename} doesn't exist or isn't a file."
            raise FileNotFoundError(msg)
        return path

    def _load(self, name, encoding="utf-8", **kwargs):
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
                **options,
            )

        if self._force_mode:
            return XMLTemplate(
                source=source,
                filename=str(resource),
                mode=self._force_mode,
                autoblocks=self._xml_autoblocks,
                **options,
            )

        ext = Path(resource.name).suffix.lstrip(".")
        return self.extension_map[ext](source=source, filename=str(resource), **options)


class PackageLoader(FileLoader):
    def __init__(self, reload=False, force_mode=None):  # noqa: FBT002
        super().__init__(None, reload=reload, force_mode=force_mode)

    def _find_resource(self, name):
        package, module = name.rsplit(".", 1)
        package_resource = importlib_resources.files(package)

        if package_resource.is_file():
            msg = f"{package} refers to a module, not a package."
            raise OSError(msg)

        for resource in package_resource.iterdir():
            if not resource.is_file():
                continue

            root, ext = os.path.splitext(resource.name)
            if root != module:
                continue

            for match_ext in (".xml", ".html", ".html5", ".txt"):
                if match_ext == ext:
                    return resource

        msg = f"Unknown template {name!r}"
        raise FileNotFoundError(msg)
