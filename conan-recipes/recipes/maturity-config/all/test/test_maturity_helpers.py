"""Layer 1: the helpers in _maturity.py, without a Conan home."""

import json
from types import SimpleNamespace

import pytest
from conan.errors import ConanException

import _maturity


def write(root, files):
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_discover_products_pairs_yml_and_lock(tmp_path):
    write(tmp_path, {"products/a.yml": "options:\n  product: a\n", "products/a.lock": "{}",
                     "products/b.yml": "description: no options\n"})
    products = _maturity.discover_products(str(tmp_path))
    assert list(products) == ["a", "b"]
    assert products["a"]["options"] == {"product": "a"}
    assert products["a"]["lock"] == str(tmp_path / "products" / "a.lock")
    assert products["b"]["options"] == {}


def test_discover_products_warns_about_orphan_lock(tmp_path, capfd):
    write(tmp_path, {"products/a.yml": "", "products/orphan.lock": "{}"})
    assert list(_maturity.discover_products(str(tmp_path))) == ["a"]
    assert "orphan.lock has no matching orphan.yml" in capfd.readouterr().err


@pytest.mark.parametrize("files, message", [
    ({}, "No 'products' folder"),
    ({"products/a.lock": "{}"}, "No product variants"),
])
def test_discover_products_errors(tmp_path, files, message):
    write(tmp_path, files)
    with pytest.raises(ConanException, match=message):
        _maturity.discover_products(str(tmp_path))


def test_check_choice_lists_available_values():
    _maturity.check_choice("target", "linux-x86_64", ["linux-x86_64"])
    with pytest.raises(ConanException, match="Unknown target 'win'. Available: a, b"):
        _maturity.check_choice("target", "win", ["a", "b"])
    with pytest.raises(ConanException, match="Available: none"):
        _maturity.check_choice("target", "win", [])


def test_profile_values_reads_one_axis():
    api = SimpleNamespace(profiles=SimpleNamespace(list=lambda: [
        "default", "maturity/target/linux-x86_64", "maturity/target/linux-armv8",
        "maturity/build_type/debug", "other/target/x"]))
    assert _maturity.profile_values(api, "target") == ["linux-armv8", "linux-x86_64"]
    assert _maturity.profile_values(api, "build_type") == ["debug"]


def test_option_and_profile_args():
    assert _maturity.option_args({"options": {"product": "productB", "shared": True}}) == [
        "-o=&:product=productB", "-o=&:shared=True"]
    assert _maturity.profile_args("linux-armv8", "debug") == [
        "-pr:h=maturity/target/linux-armv8", "-pr:h=maturity/build_type/debug",
        "-pr:b=maturity/target/linux-x86_64", "-pr:b=maturity/build_type/release"]


def test_installed_config_refs(tmp_path):
    api = SimpleNamespace(home_folder=str(tmp_path))
    assert _maturity.installed_config_refs(api) == []
    (tmp_path / "config_version.json").write_text(
        json.dumps({"config_version": ["maturity-config/0.1.0#abc"]}), encoding="utf-8")
    assert _maturity.installed_config_refs(api) == ["maturity-config/0.1.0#abc"]


def test_config_packages(tmp_path):
    write(tmp_path, {"conanconfig.yml": "packages:\n  - maturity-config/[>=0.1 <1]\n"})
    assert _maturity.config_packages(str(tmp_path)) == ["maturity-config/[>=0.1 <1]"]


def profiles_api():
    return SimpleNamespace(profiles=SimpleNamespace(list=lambda: [
        "maturity/target/linux-x86_64", "maturity/build_type/debug",
        "maturity/build_type/release"]))


def test_graph_args_composes_root_lock_options_and_profiles(tmp_path):
    write(tmp_path, {"products/a.yml": "options:\n  product: a\n", "products/a.lock": "{}"})
    root = str(tmp_path)
    assert _maturity.graph_args(profiles_api(), root, "a", "linux-x86_64", "debug") == [
        root, "--lockfile=" + str(tmp_path / "products" / "a.lock"), "-o=&:product=a",
        *_maturity.profile_args("linux-x86_64", "debug")]


@pytest.mark.parametrize("product, target, build_type, message", [
    ("nope", "linux-x86_64", "debug", "Unknown product 'nope'. Available: a, b"),
    ("a", "win", "debug", "Unknown target 'win'. Available: linux-x86_64"),
    ("a", "linux-x86_64", "relwithdebinfo", "Unknown build type 'relwithdebinfo'"),
    ("b", "linux-x86_64", "debug", "Run 'conan maturity:lock-update --product b'"),
])
def test_graph_args_errors(tmp_path, product, target, build_type, message):
    write(tmp_path, {"products/a.yml": "", "products/a.lock": "{}", "products/b.yml": ""})
    with pytest.raises(ConanException, match=message):
        _maturity.graph_args(profiles_api(), str(tmp_path), product, target, build_type)


def test_discover_products_merges_the_shipped_defaults(tmp_path):
    write(tmp_path, {"products/a.yml": "options:\n  product: a\n",
                     "products/b.yml": "coverage:\n  fail_under: 85\nrelease:\n  latest: false\n"
                                       "targets: [linux-x86_64]\nconf:\n  log_level: debug\n"})
    products = _maturity.discover_products(str(tmp_path))
    a, b = products["a"], products["b"]
    assert a["name"] == "a"
    assert a["coverage"] == {"fail_under": 90} and a["release"] == {"latest": None}
    assert a["audit"] == {"severity_level": 7.0}
    assert a["targets"] is None and a["conf"] == {} and a["description"] == ""
    assert b["coverage"] == {"fail_under": 85} and b["release"] == {"latest": False}
    assert b["targets"] == ["linux-x86_64"] and b["conf"] == {"log_level": "debug"}


@pytest.mark.parametrize("content, message", [
    ("colour: red\n", "products/x.yml: unknown key 'colour'. Allowed: audit, conf, coverage, "
                      "description, options, release, targets"),
    ("coverage:\n  fail_undre: 80\n", "products/x.yml: unknown key 'coverage.fail_undre'. "
                                      "Allowed: fail_under"),
    ("- a\n", "products/x.yml: must be a mapping"),
    ("description: [1]\n", "'description' must be a string"),
    ("options:\n  a: [1]\n", "'options.a' must be a string, number or boolean"),
    ("options: 3\n", "'options' must be a mapping"),
    ("targets: linux-x86_64\n", "'targets' must be a list of strings"),
    ("coverage:\n  fail_under: 101\n", "'coverage.fail_under' must be a number from 0 to 100"),
    ("coverage:\n  fail_under: true\n", "'coverage.fail_under' must be a number from 0 to 100"),
    ("audit:\n  severity_level: 11\n", "'audit.severity_level' must be a CVSS score from 0 to 10"),
    ("release:\n  latest: 'yes'\n", "'release.latest' must be true, false or null"),
])
def test_discover_products_rejects_invalid_manifests(tmp_path, content, message):
    write(tmp_path, {"products/x.yml": content})
    with pytest.raises(ConanException) as error:
        _maturity.discover_products(str(tmp_path))
    assert message in str(error.value)


def test_product_targets_defaults_to_all_and_checks_the_list():
    api = profiles_api()
    assert _maturity.product_targets(api, {"name": "a", "targets": None}) == ["linux-x86_64"]
    assert _maturity.product_targets(api, {"name": "a", "targets": ["linux-x86_64"]}) == [
        "linux-x86_64"]
    with pytest.raises(ConanException, match="products/a.yml lists unknown target 'win'"):
        _maturity.product_targets(api, {"name": "a", "targets": ["win"]})
