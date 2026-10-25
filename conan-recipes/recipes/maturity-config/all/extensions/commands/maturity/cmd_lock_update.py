import os

from conan.api.output import ConanOutput
from conan.cli.command import conan_command
from conan.errors import ConanException

from _maturity import (add_path_argument, check_choice, conf_args, discover_products,
                       installed_config_refs, option_args, product_targets, profile_args,
                       profile_values, run)


@conan_command(group="Maturity")
def lock_update(conan_api, parser, *args):
    """
    Regenerate products/<product>.lock from conanfile.py for every target and build type, and pin
    the installed config packages in it.
    """
    add_path_argument(parser)
    parser.add_argument("--product", help="Product variant from products/ (default: all)")
    parser.add_argument("--target", help="Target profile (default: all)")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    products = discover_products(root)
    targets = profile_values(conan_api, "target")
    build_types = profile_values(conan_api, "build_type")
    if args.product:
        check_choice("product", args.product, list(products))
    if args.target:
        check_choice("target", args.target, targets)
        targets = [args.target]

    for name, product in products.items():
        if args.product and name != args.product:
            continue
        supported = [t for t in product_targets(conan_api, product) if t in targets]
        if not supported:
            message = (f"{name} does not support target '{args.target}'. Supported: "
                       f"{', '.join(product_targets(conan_api, product))}")
            if args.product:
                raise ConanException(message)
            ConanOutput().warning(f"{name} does not support target '{args.target}', skipped")
            continue
        lock = product["lock"]
        # Start from scratch, then merge each further target and build type into the same lock.
        lock_in = ["--lockfile="]
        for target in supported:
            for build_type in build_types:
                run(conan_api, ["lock", "create", root, *lock_in, f"--lockfile-out={lock}",
                                *option_args(product), *conf_args(product),
                                *profile_args(target, build_type)])
                lock_in = [f"--lockfile={lock}", "--lockfile-partial"]
        for ref in installed_config_refs(conan_api):
            run(conan_api, ["lock", "add", f"--lockfile={lock}", f"--lockfile-out={lock}",
                            f"--config-requires={ref}"])
