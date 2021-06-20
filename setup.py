#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
import os
from setuptools import setup, find_packages
# http://peak.telecommunity.com/DevCenter/setuptools#developer-s-guide

# Get version info
__version__ = None
__release__ = None
exec(open('kajiki/version.py').read())


def content_of(*files):
    import codecs
    open = lambda path: codecs.open(path, encoding='utf-8')
    here = os.path.abspath(os.path.dirname(__file__))
    content = []
    for f in files:
        with open(os.path.join(here, f)) as stream:
            content.append(stream.read())
    return '\n'.join(content)


setup(name='kajiki',
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
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Text Processing :: Markup :: HTML',
          'Topic :: Text Processing :: Markup :: XML',
      ],
      keywords='templating engine template genshi jinja jinja2 mako '
               'chameleon xml html xhtml',
      author='Rick Copeland',
      author_email='rick446@usa.net',
      maintainer='Jack Rosenthal',
      maintainer_email='jack@rosenth.al',
      url='https://github.com/jackrosenthal/kajiki',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=['nine'],
      python_requires='>=3.4',
      extras_require = {
          'testing': ['babel', 'pytest'],
          'docs': ['sphinx'],
      },
      entry_points="""
          [console_scripts]
          kajiki = kajiki.__main__:main

          [babel.extractors]
          kajiki = kajiki.i18n:extract

          [python.templating.engines]
          kajiki = kajiki.integration.turbogears1:XMLTemplateEnginePlugin
      """,
)
