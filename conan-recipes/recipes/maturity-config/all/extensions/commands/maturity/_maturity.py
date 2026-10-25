"""Helpers shared by the maturity custom commands (not a command itself)."""

import json
import os

import yaml
from conan.api.output import ConanOutput
from conan.errors import ConanException

PRODUCTS_DIR = "products"
# Target profile of the machine running the build, used for the build context (-pr:b).
BUILD_TARGET = "linux-x86_64"


def add_path_argument(parser):
    parser.add_argument("path", nargs="?", default=".",
                        help="Repository root with conanfile.py and products/ (default: .)")


def discover_products(root):
    """Map each product variant in <root>/products/ to its settings (.yml) and lockfile (.lock)."""
    folder = os.path.join(root, PRODUCTS_DIR)
    if not os.path.isdir(folder):
        raise ConanException(f"No '{PRODUCTS_DIR}' folder in {root}")
    entries = os.listdir(folder)
    products = {}
    for entry in sorted(entries):
        name, ext = os.path.splitext(entry)
        if ext != ".yml":
            continue
        with open(os.path.join(folder, entry), encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        products[name] = {"options": data.get("options") or {},
                          "lock": os.path.join(folder, f"{name}.lock")}
    for entry in sorted(entries):
        name, ext = os.path.splitext(entry)
        if ext == ".lock" and name not in products:
            ConanOutput().warning(f"{PRODUCTS_DIR}/{entry} has no matching {name}.yml, ignored")
    if not products:
        raise ConanException(f"No product variants (*.yml) in {folder}")
    return products


def profile_values(conan_api, axis):
    """Values available for one profile axis, e.g. 'target' -> ['linux-x86_64']."""
    prefix = f"maturity/{axis}/"
    profiles = (p.replace(os.sep, "/") for p in conan_api.profiles.list())
    return sorted(p[len(prefix):] for p in profiles if p.startswith(prefix))


def check_choice(kind, value, choices):
    if value not in choices:
        raise ConanException(f"Unknown {kind} '{value}'. Available: {', '.join(choices) or 'none'}")


def option_args(product):
    return [f"-o=&:{key}={value}" for key, value in product["options"].items()]


def profile_args(target, build_type):
    return [f"-pr:h=maturity/target/{target}", f"-pr:h=maturity/build_type/{build_type}",
            f"-pr:b=maturity/target/{BUILD_TARGET}", "-pr:b=maturity/build_type/release"]


def installed_config_refs(conan_api):
    """Config packages installed in the Conan home, with version and revision."""
    path = os.path.join(conan_api.home_folder, "config_version.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["config_version"]


def config_packages(root):
    """Config package references requested in <root>/conanconfig.yml."""
    path = os.path.join(root, "conanconfig.yml")
    with open(path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("packages") or []


def run(conan_api, cmd):
    ConanOutput().info("Running: conan " + " ".join(cmd))
    conan_api.command.run(cmd)
