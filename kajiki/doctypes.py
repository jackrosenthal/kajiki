# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

doctypes = dict(
    xml='<?xml version="1.0" encoding="utf-8" ?>',
    html5='<!DOCTYPE HTML>', xhtml5='<!DOCTYPE HTML>',
    xhtml1transitional='<!DOCTYPE html PUBLIC '
        '"-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
    xhtml1strict='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
    xhtml1rdfa='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML+RDFa 1.0//EN" '
        '"http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd">',
    xhtml11='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
        '"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">',
    xhtml1frameset='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">',
    xhtmlbasic11='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML Basic 1.1//EN" '
        '"http://www.w3.org/TR/xhtml-basic/xhtml-basic11.dtd">',
    xhtmlmobile12='<!DOCTYPE html PUBLIC '
        '"-//WAPFORUM//DTD XHTML Mobile 1.2//EN" '
        '"http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd">',
    html4transitional='<!DOCTYPE html PUBLIC '
        '"-//W3C//DTD HTML 4.01 Transitional//EN" '
        '"http://www.w3.org/TR/html4/loose.dtd">',
    html4strict='<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" '
        '"http://www.w3.org/TR/html4/strict.dtd">',
    html4frameset='<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" '
        '"http://www.w3.org/TR/html4/frameset.dtd">',
    html3='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">',
    html2='<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">',
    none='', silent='',
)
doctypes[None] = doctypes['None'] = doctypes[''] = ''


def rendering_mode(doctype_name):
    if doctype_name.begins_with('x'):
        return 'xml'
    elif doctype_name == 'html5':
        return 'html5'
    else:
        return 'html'
