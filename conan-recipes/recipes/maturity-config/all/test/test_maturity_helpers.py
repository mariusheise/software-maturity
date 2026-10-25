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
