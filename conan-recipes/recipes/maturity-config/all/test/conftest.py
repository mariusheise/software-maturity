"""Shared fixtures for the maturity-config tests (run with pytest from any folder)."""

import os
import sys
import textwrap

import pytest

# The command modules are imported from the recipe folder, whose files are exported; keep
# __pycache__ out of it.
sys.dont_write_bytecode = True

RECIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS = os.path.join(RECIPE, "extensions", "commands")
sys.path.insert(0, os.path.join(COMMANDS, "maturity"))

from conan.test.utils.tools import TestClient  # noqa: E402  (after the sys.path setup)

# A dependency-free stand-in for the maturity project: same option, real settings.
FIXTURE_CONANFILE = textwrap.dedent("""\
    from conan import ConanFile

    class Fixture(ConanFile):
        name = "fixture"
        version = "1.0"
        settings = "os", "arch", "compiler", "build_type"
        options = {"product": ["ANY"]}
        default_options = {"product": "productA"}
    """)

FIXTURE_PRODUCTS = {
    "products/productA.yml": "description: A\noptions:\n  product: productA\n",
    "products/productB.yml": "description: B\noptions:\n  product: productB\n",
}

# A config revision that is never installed, for pin mismatch tests.
OTHER_CONFIG_REF = "maturity-config/0.1.0#" + "0" * 32


def recipe_profiles():
    """The profiles shipped by the recipe, as {home-relative path: content}."""
    files = {}
    for folder, _, names in os.walk(os.path.join(RECIPE, "profiles")):
        for name in names:
            path = os.path.join(folder, name)
            with open(path, encoding="utf-8") as f:
                files[os.path.relpath(path, RECIPE)] = f.read()
    return files


def save_project(client, conanconfig=None):
    files = {"conanfile.py": FIXTURE_CONANFILE, **FIXTURE_PRODUCTS}
    if conanconfig:
        files["conanconfig.yml"] = conanconfig
    client.save(files)


@pytest.fixture
def client():
    """Conan home with the recipe's profiles and its commands loaded from the source folder."""
    c = TestClient(custom_commands_folder=COMMANDS)
    c.save_home(recipe_profiles())
    save_project(c)
    return c
