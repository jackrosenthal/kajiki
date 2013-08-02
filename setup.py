#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
import os
from setuptools import setup, find_packages
# http://peak.telecommunity.com/DevCenter/setuptools#developer-s-guide
import codecs
open = lambda path: codecs.open(path, encoding='utf-8')

# Get version info
__version__ = None
__release__ = None
exec(open('kajiki/version.py').read())


def content_of(*files):
    here = os.path.abspath(os.path.dirname(__file__))
    content = []
    for f in files:
        with open(os.path.join(here, f)) as stream:
            content.append(stream.read())
    return '\n'.join(content)


setup(name='Kajiki',
      version=__release__,
      description='Fast XML-based template engine with Genshi syntax and '
                  'Jinja blocks',
      long_description=content_of('README.rst', 'CHANGES.rst'),
      classifiers=[  # http://pypi.python.org/pypi?:action=list_classifiers
          'Development Status :: 5 - Production/Stable',
          'Environment :: Web Environment',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.2',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: Implementation :: CPython',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Text Processing :: Markup :: HTML',
          'Topic :: Text Processing :: Markup :: XML',
      ],
      keywords='templating engine template genshi jinja jinja2 mako '
               'chameleon xml html xhtml',
      author='Rick Copeland',
      author_email='rick446@usa.net',
      maintainer='Nando Florestan',
      maintainer_email='nandoflorestan@gmail.com',
      url='https://github.com/nandoflorestan/kajiki',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=['nine', 'babel'],
      test_suite='kajiki.tests',
      entry_points="""
          [babel.extractors]
          kajiki = kajiki.i18n:extract
      """,
)
