"""Layer 2: the maturity:* commands, loaded from the source folder into a throwaway Conan home."""

import json
import os
import textwrap

from conftest import (COMMANDS, FIXTURE_CONANFILE, OTHER_CONFIG_REF, TestClient, recipe_profiles,
                      save_project)

# The fixture with the folder layout maturity:coverage expects; build() runs no tests, so
# gcovr finds no data and reports 100%.
COVERAGE_CONANFILE = FIXTURE_CONANFILE.replace(
    "from conan import ConanFile\n",
    "from conan import ConanFile\nfrom conan.tools.cmake import cmake_layout\n") + (
    "\n    def layout(self):\n        cmake_layout(self)\n")


def lock(client, product):
    with open(os.path.join(client.current_folder, "products", f"{product}.lock"),
              encoding="utf-8") as f:
        return json.load(f)


def test_commands_are_listed(client):
    client.run("-h")
    for command in ("maturity:install", "maturity:lock-update", "maturity:config-lock-update",
                    "maturity:coverage"):
        assert command in client.out


def test_lock_update_creates_a_lock_per_product(client):
    client.run("maturity:lock-update")
    assert lock(client, "productA")["requires"] == []
    assert lock(client, "productB")["config_requires"] == []


def test_lock_update_limits_to_one_product(client):
    client.run("maturity:lock-update --product productB")
    assert not os.path.exists(os.path.join(client.current_folder, "products", "productA.lock"))
    assert os.path.exists(os.path.join(client.current_folder, "products", "productB.lock"))


def test_lock_update_covers_every_build_type(client):
    client.run("maturity:lock-update --product productA")
    assert "-pr:h=maturity/build_type/debug" in client.out
    assert "-pr:h=maturity/build_type/release" in client.out


def test_install_composes_lock_options_and_profiles(client):
    client.run("maturity:lock-update")
    client.run("maturity:install --product=productB --target=linux-x86_64 --build-type=debug")
    assert "--lockfile=" + os.path.join(client.current_folder, "products", "productB.lock") in client.out
    assert "-o=&:product=productB" in client.out
    assert "-pr:h=maturity/target/linux-x86_64 -pr:h=maturity/build_type/debug" in client.out
    assert "build_type=Debug" in client.out
    assert "compiler.cppstd=20" in client.out


def test_install_defaults_to_release(client):
    client.run("maturity:lock-update --product productA")
    client.run("maturity:install --product=productA --target=linux-x86_64")
    assert "build_type=Release" in client.out


def test_install_rejects_unknown_values(client):
    client.run("maturity:lock-update")
    for args, message in [
        ("--product=nope --target=linux-x86_64", "Unknown product 'nope'. Available: productA, productB"),
        ("--product=productA --target=win", "Unknown target 'win'. Available: linux-x86_64"),
        ("--product=productA --target=linux-x86_64 --build-type=relwithdebinfo",
         "Unknown build type 'relwithdebinfo'. Available: debug, release"),
    ]:
        client.run(f"maturity:install {args}", assert_error=True)
        assert message in client.out


def test_install_needs_the_product_lock(client):
    client.run("maturity:install --product=productA --target=linux-x86_64", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out


def test_lock_update_pins_the_installed_config(client):
    client.save_home({"config_version.json": json.dumps({"config_version": [OTHER_CONFIG_REF]})})
    client.run("maturity:lock-update --product productA")
    assert lock(client, "productA")["config_requires"] == [OTHER_CONFIG_REF]


def test_install_fails_when_the_installed_config_differs_from_the_lock(client):
    client.save_home({"config_version.json": json.dumps({"config_version": [OTHER_CONFIG_REF]})})
    client.run("maturity:lock-update --product productA")
    installed = "maturity-config/0.1.0#" + "1" * 32
    client.save_home({"config_version.json": json.dumps({"config_version": [installed]})})
    client.run("maturity:install --product=productA --target=linux-x86_64", assert_error=True)
    assert "not in the lockfile" in client.out


def test_coverage_builds_with_the_coverage_profile_and_writes_reports(client):
    client.save({"conanfile.py": COVERAGE_CONANFILE})
    client.run("maturity:lock-update --product productB")
    client.run("maturity:coverage --product=productB --target=linux-x86_64")
    assert "Running: conan build " in client.out
    assert "--lockfile=" + os.path.join(client.current_folder, "products", "productB.lock") in client.out
    assert "-o=&:product=productB" in client.out
    assert "-pr:h=maturity/build_type/debug" in client.out
    assert "-pr:h=maturity/coverage" in client.out
    assert "build_type=Debug" in client.out
    assert "&:tools.build:cxxflags" in client.out
    reports = os.path.join(client.current_folder, "build", "coverage-report")
    for name in ("coverage.json", "coverage.xml", "coverage-report.html", "coverage-summary.md"):
        assert os.path.isfile(os.path.join(reports, name))
    assert "Line coverage 100.0% meets the gate of 90%" in client.out
    assert os.path.isdir(os.path.join(client.current_folder, "build", "coverage", "Debug"))
    client.run("maturity:coverage --product=productB --target=linux-x86_64 --fail-under=101",
               assert_error=True)
    assert "Line coverage 100.0% is below the gate of 101%" in client.out


def test_coverage_needs_the_coverage_build_folder(client):
    client.run("maturity:lock-update --product productA")
    client.run("maturity:coverage --product=productA --target=linux-x86_64", assert_error=True)
    assert "No build folder build/coverage" in client.out


def test_coverage_rejects_unknown_values_and_needs_the_lock(client):
    client.run("maturity:coverage --product=nope --target=linux-x86_64", assert_error=True)
    assert "Unknown product 'nope'" in client.out
    client.run("maturity:coverage --product=productA --target=win", assert_error=True)
    assert "Unknown target 'win'" in client.out
    client.run("maturity:coverage --product=productA --target=linux-x86_64", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out


def test_coverage_needs_gcovr(client, monkeypatch):
    client.run("maturity:lock-update --product productA")
    monkeypatch.setenv("PATH", "")
    client.run("maturity:coverage --product=productA --target=linux-x86_64", assert_error=True)
    assert "gcovr not found" in client.out


def test_config_lock_update_builds_the_revision_install_pkg_will_pick(tmp_path):
    """The remote has a newer config revision without a binary, the cache an older one with a
    binary. The build step must resolve the remote's revision, as install-pkg does."""
    c = TestClient(custom_commands_folder=COMMANDS, default_server_user=True)
    c.save_home(recipe_profiles())
    save_project(c, conanconfig="packages:\n  - cfg/[>=0.1 <1]\n")
    recipe = textwrap.dedent("""\
        from conan import ConanFile
        from conan.tools.files import save

        class Cfg(ConanFile):
            name = "cfg"
            package_type = "configuration"

            def package(self):
                save(self, self.package_folder + "/cfg.txt", "{content}")
        """)
    c.save({"cfg/conanfile.py": recipe.format(content="old")})
    c.run("create cfg --version 0.1.0")
    c.run("upload cfg/0.1.0 -r default -c")
    c.save({"cfg/conanfile.py": recipe.format(content="new")})
    c.run("export cfg --version 0.1.0")
    new_rev = c.exported_recipe_revision()
    c.run("upload cfg/0.1.0 -r default -c --only-recipe")
    c.run(f"remove cfg/0.1.0#{new_rev} -c")

    c.run("maturity:config-lock-update")
    assert "--update=cfg" in c.out
    with open(os.path.join(c.current_folder, "conan.lock"), encoding="utf-8") as f:
        assert json.load(f)["config_requires"] == [f"cfg/0.1.0#{new_rev}"]
