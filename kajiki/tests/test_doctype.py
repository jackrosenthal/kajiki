#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from unittest import TestCase, main
from nine import str
from kajiki.doctype import DocumentTypeDeclaration, extract_dtd


XHTML1 = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" ' \
         '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'


class TestDTD(TestCase):
    def test_dtd(self):
        dtd = DocumentTypeDeclaration.by_uri['']
        assert dtd.name == 'html5'
        assert str(dtd) == '<!DOCTYPE html>', str(dtd)
        assert dtd.rendering_mode == 'html5'
        dtd = DocumentTypeDeclaration.by_uri[None]
        assert dtd.name == 'xhtml5'
        assert str(dtd) == '<!DOCTYPE html>', str(dtd)
        assert dtd.rendering_mode == 'xml'
        dtd = DocumentTypeDeclaration.by_uri[
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"]
        assert dtd.name == 'xhtml1transitional'
        assert str(dtd) == XHTML1
        assert dtd.rendering_mode == 'xml'

    def test_extract_dtd(self):
        html = '<div>Test template</div>'
        markup = XHTML1 + html
        extracted, pos, rest = extract_dtd(markup)  # The function being tested
        assert extracted == XHTML1
        assert pos == 0
        assert rest == html
        dtd = DocumentTypeDeclaration.matching(extracted)  # Another function
        assert dtd is DocumentTypeDeclaration.by_uri[
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"]


if __name__ == '__main__':
    main()
