"""Layer 3: build the real package, publish it to a test server and use it as a consumer would."""

import json
import os

import pytest
from conftest import RECIPE, TestClient, save_project

REF = "maturity-config/0.1.0"
# Configuration packages have no settings, so their package ID is always the empty-info hash.
PACKAGE_ID = "da39a3ee5e6b4b0d3255bfef95601890afd80709"


@pytest.fixture
def consumer():
    """A Conan home whose only source for maturity-config is the (test) remote."""
    c = TestClient(default_server_user=True)
    c.run(f"create {RECIPE} --version 0.1.0")
    c.run(f"upload {REF} -r default -c")
    c.run('remove "*" -c')
    save_project(c, conanconfig="packages:\n  - maturity-config/[>=0.1 <1]\n")
    return c


def test_package_contains_only_profiles_and_commands():
    c = TestClient()
    c.run(f"create {RECIPE} --version 0.1.0")
    c.run(f"cache path {REF}:{PACKAGE_ID}")
    folder = c.out.strip()
    files = sorted(os.path.relpath(os.path.join(d, f), folder).replace(os.sep, "/")
                   for d, _, names in os.walk(folder) for f in names)
    assert files == [
        "conaninfo.txt", "conanmanifest.txt",
        "extensions/commands/maturity/_coverage.py",
        "extensions/commands/maturity/_maturity.py",
        "extensions/commands/maturity/cmd_build.py",
        "extensions/commands/maturity/cmd_config_lock_update.py",
        "extensions/commands/maturity/cmd_coverage.py",
        "extensions/commands/maturity/cmd_install.py",
        "extensions/commands/maturity/cmd_lock_update.py",
        "profiles/maturity/build_type/debug",
        "profiles/maturity/build_type/release",
        "profiles/maturity/coverage",
        "profiles/maturity/target/linux-x86_64",
    ]


def test_install_pkg_from_remote_then_commands_work(consumer):
    consumer.run("config install-pkg .")
    consumer.run("maturity:config-lock-update")
    with open(os.path.join(consumer.current_folder, "conan.lock"), encoding="utf-8") as f:
        pinned = json.load(f)["config_requires"]
    assert len(pinned) == 1 and pinned[0].startswith(REF + "#")
    consumer.run("maturity:lock-update")
    with open(os.path.join(consumer.current_folder, "products", "productA.lock"),
              encoding="utf-8") as f:
        assert json.load(f)["config_requires"] == pinned
    consumer.run("maturity:install --product=productA --target=linux-x86_64 --build-type=debug")
    assert "build_type=Debug" in consumer.out


def test_install_pkg_fails_for_a_revision_the_remote_does_not_have(consumer):
    lock = {"version": "0.5", "requires": [], "build_requires": [], "python_requires": [],
            "config_requires": [REF + "#" + "0" * 32]}
    consumer.save({"conan.lock": json.dumps(lock)})
    consumer.run("config install-pkg .", assert_error=True)
    assert "Unable to find" in consumer.out
