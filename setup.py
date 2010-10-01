import sys, os

from setuptools import setup, find_packages

from kajiki import version

setup(name='Kajiki',
      version=version.__release__,
      description="Really fast well-formed xml templates",
      long_description="""Are you tired of the slow performance of Genshi? But
      you still long for the assurance that your output is well-formed that you
      miss from all those other templating engines? Do you wish you had Jinja's
      blocks with Genshi's syntax? Then look  no further, Kajiki is for you!
      Kajiki quickly compiles Genshi-like syntax to *real python bytecode*
      that renders with blazing-fast speed! Don't delay! Pick up your
      copy of Kajiki today!""",  
      classifiers=[
        'Development Status :: 4 - Beta',
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
      url='http://sourceforge.net/p/kajiki/home/',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
