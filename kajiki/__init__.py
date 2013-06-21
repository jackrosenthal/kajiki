# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from .util import expose, flattener
from .template import Template
from .loader import MockLoader, FileLoader, PackageLoader
from .text import TextTemplate
from .xml_template import XMLTemplate
from .version import __version__, __release__
