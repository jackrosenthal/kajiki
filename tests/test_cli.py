from unittest import mock

import pytest

import kajiki.loader
from kajiki.__main__ import main


class MainMocks:
    def __init__(self, monkeypatch):
        mocked_render = mock.Mock(return_value="render result")
        self.render = mocked_render

        class MockedTemplate:
            def render(self, *args, **kwargs):
                return mocked_render(*args, **kwargs)

        self.template_type = mock.Mock(return_value=MockedTemplate())

        mocked_import = mock.Mock(return_value=self.template_type)
        self.import_ = mocked_import

        class MockedLoader:
            def import_(self, *args, **kwargs):
                return mocked_import(*args, **kwargs)

        self.file_loader_type = mock.Mock(return_value=MockedLoader())
        monkeypatch.setattr(kajiki.loader, "FileLoader", self.file_loader_type)

        self.package_loader_type = mock.Mock(return_value=MockedLoader())
        monkeypatch.setattr(kajiki.loader, "PackageLoader", self.package_loader_type)


@pytest.fixture
def main_mocks(monkeypatch):
    return MainMocks(monkeypatch)


@pytest.mark.parametrize(
    ("filename", "load_path"),
    [
        ("filename.txt", "."),
        ("/path/to/filename.xml", "/path/to"),
        ("some/subdir/myfile.html", "some/subdir"),
    ],
)
def test_simple_file_load(filename, load_path, capsys, main_mocks):
    main([filename])

    main_mocks.file_loader_type.assert_called_once_with(path=[load_path], force_mode=None)
    main_mocks.import_.assert_called_once_with(filename)
    main_mocks.template_type.assert_called_once_with({})
    main_mocks.render.assert_called_once_with()

    assert capsys.readouterr().out == "render result"


def test_simple_package_load(capsys, main_mocks):
    main(["-p", "my.cool.package"])

    main_mocks.package_loader_type.assert_called_once_with(force_mode=None)
    main_mocks.import_.assert_called_once_with("my.cool.package")
    main_mocks.template_type.assert_called_once_with({})
    main_mocks.render.assert_called_once_with()

    assert capsys.readouterr().out == "render result"


@mock.patch("site.addsitedir", autospec=True)
def test_package_loader_site_dirs(addsitedir, capsys, main_mocks):
    main(
        [
            "-i",
            "/usr/share/my-python-site",
            "-i",
            "relative/site/path",
            "-i",
            "another",
            "-p",
            "my.cool.package",
        ]
    )

    addsitedir.assert_has_calls(
        [
            mock.call("/usr/share/my-python-site"),
            mock.call("relative/site/path"),
            mock.call("another"),
        ]
    )

    main_mocks.package_loader_type.assert_called_once_with(force_mode=None)
    main_mocks.import_.assert_called_once_with("my.cool.package")
    main_mocks.template_type.assert_called_once_with({})
    main_mocks.render.assert_called_once_with()

    assert capsys.readouterr().out == "render result"


def test_output_to_file(tmpdir, main_mocks):
    outfile = str(tmpdir / "output_file.txt")
    main(["infile.txt", outfile])

    main_mocks.file_loader_type.assert_called_once_with(path=["."], force_mode=None)
    main_mocks.import_.assert_called_once_with("infile.txt")
    main_mocks.template_type.assert_called_once_with({})
    main_mocks.render.assert_called_once_with()

    with open(outfile) as f:
        assert f.read() == "render result"


def test_template_variables(main_mocks):
    main(["-v", "foo=bar", "-v", "baz=bip", "infile.txt"])

    main_mocks.file_loader_type.assert_called_once_with(path=["."], force_mode=None)
    main_mocks.import_.assert_called_once_with("infile.txt")
    main_mocks.template_type.assert_called_once_with(
        {
            "foo": "bar",
            "baz": "bip",
        }
    )
    main_mocks.render.assert_called_once_with()


def test_template_variables_bad(capsys):
    with pytest.raises(SystemExit) as e:
        main(["-v", "BADBADBAD", "infile.txt"])

    assert e.value.code != 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.endswith("error: argument -v/--var: Expected a KEY=VALUE pair, got BADBADBAD\n")
