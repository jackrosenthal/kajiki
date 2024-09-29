"""Test we don't break TurboGears' usage of our Python API."""

from __future__ import annotations

import dataclasses
import wsgiref.util
from pathlib import Path
from typing import Any

import pytest

from kajiki import i18n

DATA = Path(__file__).resolve().parent.parent / "data"
GOLDEN = DATA / "golden"


@pytest.fixture
def tg2():
    """Import tg2 (if available), and cleanup its mess."""
    orig_gettext = i18n.gettext
    try:
        import tg
    except ImportError:
        pytest.skip("TurboGears not installed")
    else:
        yield tg
    finally:
        i18n.gettext = orig_gettext


@pytest.fixture
def tg2_app(tg2):
    """Create a new tg2 app with defaults for testing.

    Returns:
        A WSGI application.
    """

    class RootController(tg2.TGController):
        @tg2.expose("kajiki_test_data.kitchensink")
        def index(self):
            return {}

    config = tg2.MinimalApplicationConfigurator()
    config.update_blueprint(
        {
            "root_controller": RootController(),
            "renderers": ["kajiki"],
            "templating.kajiki.template_extension": ".html",
        }
    )
    return config.make_wsgi_app()


@dataclasses.dataclass
class Response:
    """Encapsulates a response for testing."""

    status: str
    headers: list[tuple[str, str]]
    body: str


def app_request(app: Any, path: str = "/", method: str = "GET") -> Response:
    response_status = ""
    response_headers = []

    def start_response(status, headers):
        nonlocal response_status
        nonlocal response_headers
        response_status = status
        response_headers = headers

    environ = {}
    wsgiref.util.setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path

    response_body = b"".join(app(environ, start_response))

    return Response(
        status=response_status,
        headers=response_headers,
        body=response_body,
    )


def test_smoke_tg2(tg2_app):
    """Do a basic smoke test of using kajiki renderer on tg2."""
    response = app_request(tg2_app, "/")
    assert response.status == "200 OK"
    assert response.body == (GOLDEN / "kitchensink1.html").read_bytes()
