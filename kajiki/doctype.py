import re


class DocumentTypeDeclaration:
    """Represents a http://en.wikipedia.org/wiki/Document_Type_Declaration

    This is used to lookup DTDs details by its string, DTDs can
    be registered in :attr:`.by_uri` and can then be looked up
    using :meth:`.matching` method:

    >>> from kajiki.doctype import DocumentTypeDeclaration
    >>> dtd = DocumentTypeDeclaration(
    ...     "html4transitional",
    ...     "-//W3C//DTD HTML 4.01 Transitional//EN",
    ...     "http://www.w3.org/TR/html4/loose.dtd",
    ...     rendering_mode="html",
    ... )
    >>> dtd.uri
    'http://www.w3.org/TR/html4/loose.dtd'
    >>> DocumentTypeDeclaration.by_uri["http://www.w3.org/TR/html4/loose.dtd"] = dtd
    >>> match = DocumentTypeDeclaration.matching(
    ...     '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" '
    ...     '"http://www.w3.org/TR/html4/loose.dtd">'
    ... )
    >>> match.name
    'html4transitional'

    DocumentTypeDeclaration is used by :class:`kajiki.xml_template._Compiler`
    to detect the document doctype and tune generated template (for example
    by deciding if tags closed inline are allowed or not).
    """

    def __init__(
        self,
        name,
        fpi="",
        uri="",
        rendering_mode="xml",
        root_element="html",
        kind="PUBLIC",
    ):
        """*fpi* is the Formal Public Identifier."""
        self.name = name
        self.fpi = fpi
        self.uri = uri
        self.rendering_mode = rendering_mode
        self.root_element = root_element
        assert kind in (  # noqa: S101
            "PUBLIC",
            "SYSTEM",
            "",
        ), '*kind* can be either "PUBLIC", "SYSTEM", or empty.'
        self.kind = kind
        self._cached_str = None

        self.regex = re.compile(
            str(self).replace(" ", r"\s+").replace(".", r"\.").replace("[", r"\[").replace("]", r"\]"),
            flags=re.IGNORECASE,
        )

    def __str__(self):
        if not self._cached_str:
            alist = ["<!DOCTYPE"]
            alist.append(self.root_element)
            if self.kind:
                alist.append(self.kind)
            if self.fpi:
                alist.append('"' + self.fpi + '"')
            if self.uri:
                alist.append('"' + self.uri + '"')
            self._cached_str = " ".join(alist) + ">"
        return self._cached_str

    by_uri = {}  # We store the public DTDs here.  # noqa: RUF012

    @classmethod
    def matching(cls, dtd_string):
        """Looks up the known DTDs and returns the instance that matches the
        provided dtd_string.
        """
        for dtd in cls.by_uri.values():
            if dtd.regex.match(dtd_string):
                return dtd
        return None

    REGEX = re.compile(r"<!DOCTYPE[^>]+>")  # This matches any DTD.


# Build the public DTDs dictionary
for dtd in (
    DocumentTypeDeclaration("html5", kind="", rendering_mode="html5"),
    DocumentTypeDeclaration("xhtml5", kind="", uri=None),
    DocumentTypeDeclaration(
        "xhtml1transitional",
        "-//W3C//DTD XHTML 1.0 Transitional//EN",
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd",
    ),
    DocumentTypeDeclaration(
        "xhtml1strict",
        "-//W3C//DTD XHTML 1.0 Strict//EN",
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd",
    ),
    DocumentTypeDeclaration(
        "xhtml1rdfa",
        "-//W3C//DTD XHTML+RDFa 1.0//EN",
        "http://www.w3.org/MarkUp/DTD/xhtml-rdfa-1.dtd",
    ),
    DocumentTypeDeclaration(
        "xhtml11",
        "-//W3C//DTD XHTML 1.1//EN",
        "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd",
    ),
    DocumentTypeDeclaration(
        "xhtml1frameset",
        "-//W3C//DTD XHTML 1.0 Frameset//EN",
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd",
    ),
    DocumentTypeDeclaration(
        "xhtmlbasic11",
        "-//W3C//DTD XHTML Basic 1.1//EN",
        "http://www.w3.org/TR/xhtml-basic/xhtml-basic11.dtd",
    ),
    DocumentTypeDeclaration(
        "xhtmlmobile12",
        "-//WAPFORUM//DTD XHTML Mobile 1.2//EN",
        "http://www.openmobilealliance.org/tech/DTD/xhtml-mobile12.dtd",
    ),
    DocumentTypeDeclaration(
        "html4transitional",
        "-//W3C//DTD HTML 4.01 Transitional//EN",
        "http://www.w3.org/TR/html4/loose.dtd",
        rendering_mode="html",
    ),
    DocumentTypeDeclaration(
        "html4strict",
        "-//W3C//DTD HTML 4.01//EN",
        "http://www.w3.org/TR/html4/strict.dtd",
        rendering_mode="html",
    ),
    DocumentTypeDeclaration(
        "html4frameset",
        "-//W3C//DTD HTML 4.01 Frameset//EN",
        "http://www.w3.org/TR/html4/frameset.dtd",
        rendering_mode="html",
    ),
    # html3='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">',
    # html2='<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">',
):
    DocumentTypeDeclaration.by_uri[dtd.uri] = dtd

XML_DECLARATION = re.compile(r"<\?xml .*?\?>")


def extract_dtd(markup):
    """Lookup the DTD in the provided markup code.

    Tries to find any DTD in the string *markup* and returns a tuple
    (dtd_string, position, markup_without_the_DTD). Note the first of
    these values might be an empty string:

    >>> markup = (
    ...     "<!DOCTYPE HTML PUBLIC "
    ...     '"-//W3C//DTD HTML 4.01 Transitional//EN" '
    ...     '"http://www.w3.org/TR/html4/loose.dtd">'
    ...     '''<html>
    ...     <head>
    ...     ...
    ...     </head>
    ...     <body>
    ...     ...
    ...     </body>
    ...     </html>'''
    ... )
    >>> import kajiki.doctype
    >>> dtd, dtd_pos, markup_without_dtd = kajiki.doctype.extract_dtd(markup)
    >>> print(dtd)  # doctest: +NORMALIZE_WHITESPACE
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
    >>> print(dtd_pos)
    0
    >>> print(markup_without_dtd)  # doctest: +NORMALIZE_WHITESPACE
    <html>
    <head>
    ...
    </head>
    <body>
    ...
    </body>
    </html>

    >>> markup = '<?xml version="1.0"?><!DOCTYPE html><html><body></body></html>'
    >>> dtd, dtd_pos, markup_without_dtd = kajiki.doctype.extract_dtd(markup)
    >>> print(dtd)
    <!DOCTYPE html>
    >>> print(dtd_pos)
    21
    >>> print(markup_without_dtd)
    <?xml version="1.0"?><html><body></body></html>

    >>> markup = '<?xml version="1.0"?><html><head></head><body></body></html>'
    >>> dtd, dtd_pos, markup_without_dtd = kajiki.doctype.extract_dtd(markup)
    >>> print(dtd)
    <BLANKLINE>
    >>> print(dtd_pos)
    21
    >>> print(markup_without_dtd == markup)
    True

    >>> markup = '<?xml version="1.0" encoding="UTF-8"?><html><body></body></html>'
    >>> dtd, dtd_pos, markup_without_dtd = kajiki.doctype.extract_dtd(markup)
    >>> print(dtd)
    <BLANKLINE>
    >>> print(dtd_pos)
    38
    >>> print(markup_without_dtd == markup)
    True
    """
    match = DocumentTypeDeclaration.REGEX.search(markup)
    if not match:
        decl_match = XML_DECLARATION.match(markup)
        if decl_match:
            # The position for a prospective DTD is *after* the <?xml ...?> declaration,
            # because it's not allowed for there to be anything before it.
            return "", decl_match.end(), markup
        return "", 0, markup
    found = match.group()
    return found, match.start(), markup.replace(found, "", 1)
