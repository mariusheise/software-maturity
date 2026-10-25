"""Layer 2: the maturity:* commands, loaded from the source folder into a throwaway Conan home."""

import json
import os

from conftest import OTHER_CONFIG_REF


def lock(client, product):
    with open(os.path.join(client.current_folder, "products", f"{product}.lock"),
              encoding="utf-8") as f:
        return json.load(f)


def test_commands_are_listed(client):
    client.run("-h")
    for command in ("maturity:install", "maturity:lock-update", "maturity:config-lock-update"):
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
