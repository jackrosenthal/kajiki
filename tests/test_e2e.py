"""End-to-end tests of Kajiki."""

import pathlib

import pytest

from kajiki.__main__ import main

DATA = pathlib.Path(__file__).parent / "data"
GOLDEN = DATA / "golden"


@pytest.mark.parametrize(
    ["args", "golden_file"],
    [
        (["-p", "kajiki_test_data.kitchensink"], "kitchensink1.html"),
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


def test_file_not_found():
    with pytest.raises(IOError):
        main(["/does/not/exist.txt"])


# We should be able to force a non-txt file into text mode.
def test_force_text_mode(tmpdir, capsys):
    tmpfile = str(tmpdir / "myfile.png")
    with open(tmpfile, "w") as f:
        f.write("<!DOCTYPE html>\n")
        f.write("%for i in range(10)\n")
        f.write("${i}\n")
        f.write("%end")

    main(["-m", "text", tmpfile])

    captured = capsys.readouterr()
    assert (
        captured.out
        == """<!DOCTYPE html>
0
1
2
3
4
5
6
7
8
9
"""
    )
    assert captured.err == ""
