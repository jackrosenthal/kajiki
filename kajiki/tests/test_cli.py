#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import io
import unittest
import os
import site
import sys
import tempfile
import unittest.mock as mock

import kajiki.loader
from kajiki.__main__ import main


XHTML1 = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" ' \
         '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'


class TestCLI(unittest.TestCase):
    def setattr_reset(self, obj, attr, value):
        # Like setattr, but reset to the original value during
        # tearDown.
        orig = getattr(obj, attr)
        setattr(obj, attr, value)
        self.reset_list.append((obj, attr, orig))

    def tearDown(self):
        while self.reset_list:
            obj, attr, orig = self.reset_list.pop()
            setattr(obj, attr, orig)

    def setUp(self):
        # Create the reset list if not already existing.
        self.reset_list = getattr(self, 'reset_list', [])

        self.mocked_addsitedir = mock.Mock()
        self.setattr_reset(site, 'addsitedir', self.mocked_addsitedir)

        mocked_render = mock.Mock(return_value='render result')
        self.mocked_render = mocked_render

        class MockedTemplate(object):
            def render(self, *args, **kwargs):
                return mocked_render(*args, **kwargs)

        self.mocked_template_type = mock.Mock(return_value=MockedTemplate())

        mocked_import = mock.Mock(return_value=self.mocked_template_type)
        self.mocked_import = mocked_import

        class MockedLoader(object):
            def import_(self, *args, **kwargs):
                return mocked_import(*args, **kwargs)

        self.mocked_file_loader_type = mock.Mock(return_value=MockedLoader())
        self.setattr_reset(kajiki.loader, 'FileLoader',
                           self.mocked_file_loader_type)

        self.mocked_package_loader_type = mock.Mock(
            return_value=MockedLoader())
        self.setattr_reset(kajiki.loader, 'PackageLoader',
                           self.mocked_package_loader_type)

        self.mocked_stdout = io.StringIO()
        self.setattr_reset(sys, 'stdout', self.mocked_stdout)

    def test_simple_file_load(self):
        for filename, load_path in [
                ('filename.txt', '.'),
                ('/path/to/filename.xml', '/path/to'),
                ('some/subdir/myfile.html', 'some/subdir'),
        ]:
            main([filename])

            self.mocked_file_loader_type.assert_called_once_with(
                path=[load_path], force_mode=None)
            self.mocked_import.assert_called_once_with(filename)
            self.mocked_template_type.assert_called_once_with({})
            self.mocked_render.assert_called_once_with()
            assert self.mocked_stdout.getvalue() == 'render result'

            # Reset mocks for next set of params.
            self.setUp()

    def test_simple_package_load(self):
        main(['-p', 'my.cool.package'])

        self.mocked_package_loader_type.assert_called_once_with(
            force_mode=None)
        self.mocked_import.assert_called_once_with('my.cool.package')
        self.mocked_template_type.assert_called_once_with({})
        self.mocked_render.assert_called_once_with()
        assert self.mocked_stdout.getvalue() == 'render result'

    def test_package_loader_site_dirs(self):
        main(['-i', '/usr/share/my-python-site',
              '-i', 'relative/site/path',
              '-i', 'another',
              '-p', 'my.cool.package'])

        self.mocked_addsitedir.assert_has_calls(
            [
                mock.call('/usr/share/my-python-site'),
                mock.call('relative/site/path'),
                mock.call('another'),
            ])

        self.mocked_package_loader_type.assert_called_once_with(
            force_mode=None)
        self.mocked_import.assert_called_once_with('my.cool.package')
        self.mocked_template_type.assert_called_once_with({})
        self.mocked_render.assert_called_once_with()
        assert self.mocked_stdout.getvalue() == 'render result'

    def test_output_to_file(self):
        with tempfile.TemporaryDirectory() as d:
            outfile = os.path.join(d, 'output_file.txt')
            main(['infile.txt', outfile])

            self.mocked_file_loader_type.assert_called_once_with(
                path=['.'], force_mode=None)
            self.mocked_import.assert_called_once_with('infile.txt')
            self.mocked_template_type.assert_called_once_with({})
            self.mocked_render.assert_called_once_with()

            with open(outfile, 'r') as f:
                assert f.read() == 'render result'

    def test_template_variables(self):
        main(['-v', 'foo=bar',
              '-v', 'baz=bip',
              'infile.txt'])

        self.mocked_file_loader_type.assert_called_once_with(
            path=['.'], force_mode=None)
        self.mocked_import.assert_called_once_with('infile.txt')
        self.mocked_template_type.assert_called_once_with({
            'foo': 'bar',
            'baz': 'bip',
        })
        self.mocked_render.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
