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


# The sections a products/<name>.yml may have. Values: a nested schema (dict) or a check that
# returns an error message for a wrong value (None when fine).
def _scalar_map(value):
    if not isinstance(value, dict):
        return "must be a mapping"
    for key, item in value.items():
        if not isinstance(item, (str, int, float, bool)):
            return {key: "must be a string, number or boolean"}
    return None


MANIFEST_SCHEMA = {
    "description": lambda v: None if isinstance(v, str) else "must be a string",
    "options": _scalar_map,
    "conf": _scalar_map,
    "targets": lambda v: (None if v is None or (isinstance(v, list)
                                                and all(isinstance(t, str) for t in v))
                          else "must be a list of strings"),
    "coverage": {
        "fail_under": lambda v: (None if isinstance(v, (int, float)) and not isinstance(v, bool)
                                 and 0 <= v <= 100 else "must be a number from 0 to 100"),
    },
    "audit": {
        "severity_level": lambda v: (None if isinstance(v, (int, float)) and not isinstance(v, bool)
                                     and 0 <= v <= 10 else "must be a CVSS score from 0 to 10"),
    },
    "release": {
        "latest": lambda v: None if v is None or isinstance(v, bool)
        else "must be true, false or null",
    },
}
# Org-wide defaults shipped with the commands; a product manifest overrides them.
DEFAULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defaults.yml")


def _validate(data, schema, source, prefix=""):
    if not isinstance(data, dict):
        raise ConanException(f"{source}: {f'{prefix[:-1]!r} ' if prefix else ''}must be a mapping")
    for key, value in data.items():
        path = f"{prefix}{key}"
        if key not in schema:
            raise ConanException(f"{source}: unknown key {path!r}. "
                                 f"Allowed: {', '.join(sorted(schema))}")
        check = schema[key]
        if isinstance(check, dict):
            _validate(value, check, source, f"{path}.")
            continue
        error = check(value)
        if isinstance(error, dict):  # an error about one entry of a mapping
            (item, message), = error.items()
            raise ConanException(f"{source}: '{path}.{item}' {message}")
        if error:
            raise ConanException(f"{source}: {path!r} {error}")


def _merge(defaults, data):
    merged = dict(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict) and key not in (
                "options", "conf"):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_defaults():
    with open(DEFAULTS_FILE, encoding="utf-8") as f:
        defaults = yaml.safe_load(f) or {}
    _validate(defaults, MANIFEST_SCHEMA, os.path.basename(DEFAULTS_FILE))
    return defaults


def discover_products(root):
    """Map each product variant in <root>/products/ to its validated manifest (<name>.yml,
    merged over the shipped defaults) plus its lockfile path (<name>.lock)."""
    folder = os.path.join(root, PRODUCTS_DIR)
    if not os.path.isdir(folder):
        raise ConanException(f"No '{PRODUCTS_DIR}' folder in {root}")
    entries = os.listdir(folder)
    base = {"description": "", "options": {}, "conf": {}, "targets": None, **load_defaults()}
    products = {}
    for entry in sorted(entries):
        name, ext = os.path.splitext(entry)
        if ext != ".yml":
            continue
        with open(os.path.join(folder, entry), encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data = {} if data is None else data
        _validate(data, MANIFEST_SCHEMA, f"{PRODUCTS_DIR}/{entry}")
        products[name] = {**_merge(base, data), "name": name, "manifest": data,
                          "lock": os.path.join(folder, f"{name}.lock")}
    for entry in sorted(entries):
        name, ext = os.path.splitext(entry)
        if ext == ".lock" and name not in products:
            ConanOutput().warning(f"{PRODUCTS_DIR}/{entry} has no matching {name}.yml, ignored")
    if not products:
        raise ConanException(f"No product variants (*.yml) in {folder}")
    return products


def product_targets(conan_api, product):
    """Target profiles a product supports: its 'targets' list, or every maturity/target/*."""
    available = profile_values(conan_api, "target")
    if product["targets"] is None:
        return available
    for target in product["targets"]:
        if target not in available:
            raise ConanException(f"{PRODUCTS_DIR}/{product['name']}.yml lists unknown target "
                                 f"'{target}'. Available: {', '.join(available) or 'none'}")
    return list(product["targets"])


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


def conf_args(product):
    """The manifest's conf section for the root recipe, as user.maturity.product:<key>."""
    return [arg for key, value in product["conf"].items()
            for arg in ("-c", f"user.maturity.product:{key}={value}")]


def profile_args(target, build_type):
    return [f"-pr:h=maturity/target/{target}", f"-pr:h=maturity/build_type/{build_type}",
            f"-pr:b=maturity/target/{BUILD_TARGET}", "-pr:b=maturity/build_type/release"]


def graph_args(conan_api, root, product, target, build_type):
    """Root, lockfile, options and profiles of a product variant for 'conan install/build'."""
    products = discover_products(root)
    check_choice("product", product, list(products))
    variant = products[product]
    check_choice("target", target, product_targets(conan_api, variant))
    check_choice("build type", build_type, profile_values(conan_api, "build_type"))
    if not os.path.isfile(variant["lock"]):
        raise ConanException(f"Missing lockfile for {product}. "
                             f"Run 'conan maturity:lock-update --product {product}'")
    return [root, f"--lockfile={variant['lock']}", *option_args(variant), *conf_args(variant),
            *profile_args(target, build_type)]


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


def run(conan_api, cmd, raise_on_errors=True):
    ConanOutput().info("Running: conan " + " ".join(cmd))
    return conan_api.command.run(cmd, raise_on_errors=raise_on_errors)
