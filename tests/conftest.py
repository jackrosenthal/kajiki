import importlib
import pathlib
import sys

import pytest


@pytest.fixture(scope="session", autouse=True)
def add_test_data_module():
    here = pathlib.Path(__file__).parent
    data_package = here / "data" / "__init__.py"
    spec = importlib.util.spec_from_file_location("kajiki_test_data", str(data_package))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
