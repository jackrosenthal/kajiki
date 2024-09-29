"""Kajiki public API."""

from kajiki.loader import FileLoader, MockLoader, PackageLoader
from kajiki.template import Template
from kajiki.text import TextTemplate
from kajiki.util import expose, flattener
from kajiki.xml_template import XMLTemplate

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
