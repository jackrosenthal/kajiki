"""End-to-end tests of Kajiki."""

import pathlib
import pytest

from kajiki.__main__ import main


DATA = pathlib.Path(__file__).parent / "data"
GOLDEN = DATA / "golden"


@pytest.mark.parametrize(
    ["args", "golden_file"],
    [
        (["-p", "kajiki.tests.data.kitchensink"], "kitchensink1.html"),
        ([str(DATA / "kitchensink.html")], "kitchensink1.html"),
    ],
)
def test_golden_file(args, golden_file, capsys):
    with open(str(GOLDEN / golden_file)) as f:
        golden_data = f.read()

    main(args)

    captured = capsys.readouterr()
    assert captured.out == golden_data
    assert captured.err == ""
