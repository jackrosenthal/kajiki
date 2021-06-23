"""Kajiki public API."""

from .loader import FileLoader, MockLoader, PackageLoader
from .template import Template
from .text import TextTemplate
from .util import expose, flattener
from .version import __release__, __version__
from .xml_template import XMLTemplate

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
