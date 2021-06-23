"""Kajiki public API."""

from .util import expose, flattener
from .template import Template
from .loader import MockLoader, FileLoader, PackageLoader
from .text import TextTemplate
from .xml_template import XMLTemplate
from .version import __version__, __release__

__all__ = [
    "expose",
    "flattener",
    "Template",
    "MockLoader",
    "FileLoader",
    "PackageLoader",
    "TextTemplate",
    "XMLTemplate",
    "__version__",
    "__release__",
]
