import importlib
import pathlib
import sys

import pytest


@pytest.fixture(scope="session", autouse=True)
def add_test_data_module():
    here = pathlib.Path(__file__).parent
    data_package = here / "data" / "__init__.py"
    spec = importlib.util.spec_from_file_location("kajiki_test_data", str(data_package))

    # TODO(Python3.4): below dance can change to
    # importlib.util.module_from_spec() when support for Python 3.4 is
    # dropped.
    module = type(sys)(spec.name)
    module.__name__ = spec.name
    module.__loader__ = spec.loader
    module.__package__ = spec.parent
    module.__path__ = spec.submodule_search_locations
    module.__file__ = spec.origin

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
