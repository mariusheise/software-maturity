import os

from conan.cli.command import conan_command

from _maturity import add_path_argument, graph_args, run


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
    run(conan_api, ["install", *graph_args(conan_api, root, args.product, args.target,
                                           args.build_type), f"--build={args.build}"])
