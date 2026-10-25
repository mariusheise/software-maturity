import os

from conan.cli.command import conan_command

from _maturity import add_path_argument, graph_args, run


@conan_command(group="Maturity")
def build(conan_api, parser, *args):
    """
    Build a product variant for a target and build type with 'conan build' (install, generate
    and the recipe's build(), which runs the unit tests), using the product's lockfile and the
    maturity profiles.
    """
    add_path_argument(parser)
    parser.add_argument("--product", required=True, help="Product variant from products/")
    parser.add_argument("--target", required=True, help="Target profile, e.g. linux-x86_64")
    parser.add_argument("--build-type", default="release", help="Build type profile (default: release)")
    parser.add_argument("--skip-test", action="store_true",
                        help="Do not build or run the unit tests (tools.build:skip_test=True)")
    parser.add_argument("--version", help="Version of the build, e.g. from a release tag "
                                          "(the recipe has none)")
    parser.add_argument("--build", default="missing", help="Conan --build policy (default: missing)")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    cmd = ["build", *graph_args(conan_api, root, args.product, args.target, args.build_type),
           f"--build={args.build}"]
    if args.version:
        cmd += ["--version", args.version]
    if args.skip_test:
        # Conan's own test switch: CMake.test()/ctest() do nothing and BUILD_TESTING is OFF.
        cmd += ["-c", "tools.build:skip_test=True"]
    run(conan_api, cmd)
