"""Command-line interface to Kajiki to render a single template."""

import argparse
import os
import site
import sys

import kajiki.loader


def _kv_pair(pair):
    """Convert a KEY=VALUE string to a 2-tuple of (KEY, VALUE).

    This is intended for usage with the type= argument to argparse.
    """
    key, sep, value = pair.partition("=")
    if not sep:
        msg = f"Expected a KEY=VALUE pair, got {pair}"
        raise argparse.ArgumentTypeError(
            msg
        )
    return key, value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-m",
        "--mode",
        dest="force_mode",
        choices=["text", "xml", "html", "html5"],
        help=(
            "Force a specific templating mode instead of auto-detecting "
            "based on extension."
        ),
    )
    parser.add_argument(
        "-i",
        "--path",
        action="append",
        dest="paths",
        default=[],
        metavar="path",
        help=(
            "Add to the file loader's include paths.  For the package "
            "loader, this will add the path to Python's site directories."
        ),
    )
    parser.add_argument(
        "-v",
        "--var",
        action="append",
        dest="template_variables",
        default=[],
        type=_kv_pair,
        metavar="KEY=VALUE",
        help="Template variables, passed as KEY=VALUE pairs.",
    )
    parser.add_argument(
        "-p",
        "--package",
        dest="loader_type",
        action="store_const",
        const=kajiki.loader.PackageLoader,
        default=kajiki.loader.FileLoader,
        help="Load based on package name instead of file path.",
    )
    parser.add_argument(
        "file_or_package",
        help="Filename or package to load.",
    )
    parser.add_argument(
        "output_file",
        type=argparse.FileType("w"),
        default=sys.stdout,
        nargs="?",
        help="Output file.  If unspecified, use stdout.",
    )

    opts = parser.parse_args(argv)

    loader_kwargs = {}
    if opts.loader_type is kajiki.loader.PackageLoader:
        for path in opts.paths:
            site.addsitedir(path)
    else:
        opts.paths.append(os.path.dirname(opts.file_or_package) or ".")
        loader_kwargs["path"] = opts.paths

    loader = opts.loader_type(force_mode=opts.force_mode, **loader_kwargs)
    template = loader.import_(opts.file_or_package)
    result = template(dict(opts.template_variables)).render()
    opts.output_file.write(result)

    # Close the output file to avoid a ResourceWarning during unit
    # tests on Python 3.4+.  But don't close stdout, just flush it
    # instead.
    if opts.output_file is sys.stdout:
        opts.output_file.flush()
    else:
        opts.output_file.close()


if __name__ == "__main__":
    main(sys.argv[1:])  # pragma: no cover
