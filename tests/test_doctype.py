import pytest

from kajiki.doctype import DocumentTypeDeclaration, extract_dtd

XHTML1 = (
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
    '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
)


@pytest.mark.parametrize(
    ["uri", "name", "rendering_mode", "stringified"],
    [
        ["", "html5", "html5", "<!DOCTYPE html>"],
        [None, "xhtml5", "xml", "<!DOCTYPE html>"],
        [
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd",
            "xhtml1transitional",
            "xml",
            XHTML1,
        ],
    ],
)
def test_dtd_by_uri(uri, name, rendering_mode, stringified):
    dtd = DocumentTypeDeclaration.by_uri[uri]
    assert dtd.name == name
    assert dtd.rendering_mode == rendering_mode
    assert str(dtd) == stringified


def test_extract_dtd():
    html = "<div>Test template</div>"
    markup = XHTML1 + html
    extracted, pos, rest = extract_dtd(markup)  # The function being tested
    assert extracted == XHTML1
    assert pos == 0
    assert rest == html
    dtd = DocumentTypeDeclaration.matching(extracted)  # Another function
    assert (
        dtd
        is DocumentTypeDeclaration.by_uri[
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
        ]
    )
