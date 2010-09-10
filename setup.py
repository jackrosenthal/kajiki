from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='FastPt',
      version=version,
      description="Really fast well-formed xml templates",
      long_description="""Are you tired of the slow performance of Genshi? But
      you still long for the assurance that your output is well-formed that you
      miss from all those other templating engines? Do you wish you had Jinja's
      blocks with Genshi's syntax? Then look  no further, FastPt is for you!
      FastPt uses the stdlib's HTMLParser to *quickly* compile Genshi-like syntax to *real python
      bytecode* that renders with blazing-fast speed! Don't delay! Pick up your
      copy of FastPt today!""",  
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML',
        'Topic :: Text Processing :: Markup :: XML'
        ], 
      keywords='template xml',
      author='Rick Copeland',
      author_email='rick446@usa.net',
      url='http://bitbucket.org/rick446/fastpt',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'webhelpers',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
