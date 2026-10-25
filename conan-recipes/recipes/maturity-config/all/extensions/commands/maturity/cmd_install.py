import os

from conan.cli.command import conan_command
from conan.errors import ConanException

from _maturity import (add_path_argument, check_choice, discover_products, option_args,
                       profile_args, profile_values, run)


@conan_command(group="Maturity")
def install(conan_api, parser, *args):
    """
    Install the dependencies of a product variant for a target and build type, using the
    product's lockfile and the maturity profiles.
    """
    add_path_argument(parser)
    parser.add_argument("--product", required=True, help="Product variant from products/")
    parser.add_argument("--target", required=True, help="Target profile, e.g. linux-x86_64")
    parser.add_argument("--build-type", default="release", help="Build type profile (default: release)")
    parser.add_argument("--build", default="missing", help="Conan --build policy (default: missing)")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    products = discover_products(root)
    check_choice("product", args.product, list(products))
    check_choice("target", args.target, profile_values(conan_api, "target"))
    check_choice("build type", args.build_type, profile_values(conan_api, "build_type"))
    product = products[args.product]
    if not os.path.isfile(product["lock"]):
        raise ConanException(f"Missing lockfile for {args.product}. "
                             f"Run 'conan maturity:lock-update --product {args.product}'")

    run(conan_api, ["install", root, f"--lockfile={product['lock']}", *option_args(product),
                    *profile_args(args.target, args.build_type), f"--build={args.build}"])
