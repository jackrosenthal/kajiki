#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)
from setuptools import setup, find_packages

# Get version info
__version__ = None
__release__ = None
exec(open('kajiki/version.py').read())

setup(name='Kajiki',
      version=__release__,
      description="Really fast well-formed xml templates",
      long_description="""Are you tired of the slow performance of Genshi? But
      you still long for the assurance that your output is well-formed that you
      miss from all those other templating engines? Do you wish you had Jinja's
      blocks with Genshi's syntax? Then look no further, Kajiki is for you!
      Kajiki quickly compiles Genshi-like syntax to *real python bytecode*
      that renders with blazing-fast speed! Don't delay! Pick up your
      copy of Kajiki today!""",
      classifiers=[  # http://pypi.python.org/pypi?:action=list_classifiers
          'Development Status :: 4 - Beta',
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
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Text Processing :: Markup :: HTML',
          'Topic :: Text Processing :: Markup :: XML',
      ],
      keywords='template xml',
      author='Rick Copeland',
      author_email='rick446@usa.net',
      url='http://sourceforge.net/p/kajiki/home/',
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
