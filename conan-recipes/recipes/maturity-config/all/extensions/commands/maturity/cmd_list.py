import os

from conan.api.output import cli_out_write
from conan.cli.command import conan_command
from conan.cli.formatters import default_json_formatter

from _maturity import (add_path_argument, check_choice, discover_products, product_targets,
                       profile_values)


def _text(data):
    for name, product in data["products"].items():
        cli_out_write(f"{name}: {product['description'] or '(no description)'}")
        cli_out_write(f"  targets:  {', '.join(product['targets'])}")
        options = ", ".join(f"{k}={v}" for k, v in product["options"].items())
        cli_out_write(f"  options:  {options or '-'}")
        if product["conf"]:
            cli_out_write("  conf:     " + ", ".join(f"{k}={v}" for k, v in product["conf"].items()))
        cli_out_write(f"  coverage: fail_under={product['coverage']['fail_under']}")
        cli_out_write(f"  release:  latest={product['release']['latest']}")


@conan_command(group="Maturity", formatters={"text": _text, "json": default_json_formatter})
def list(conan_api, parser, *args):  # noqa: A001 (the command is named after the function)
    """
    List the product variants in products/ with their validated manifests (merged over the
    shipped defaults), for people (text) and CI (--format=json).
    """
    add_path_argument(parser)
    parser.add_argument("--product", help="Only this product variant")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    products = discover_products(root)
    if args.product:
        check_choice("product", args.product, sorted(products))
        products = {args.product: products[args.product]}
    listed = {}
    for name, product in products.items():
        manifest = {k: v for k, v in product.items() if k not in ("name", "lock", "manifest")}
        manifest["targets"] = product_targets(conan_api, product)
        listed[name] = manifest
    return {"products": listed, "targets": profile_values(conan_api, "target"),
            "build_types": profile_values(conan_api, "build_type")}
