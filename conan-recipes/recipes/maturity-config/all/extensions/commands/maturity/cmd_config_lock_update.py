import os

from conan.cli.command import conan_command

from _maturity import (BUILD_TARGET, PRODUCTS_DIR, add_path_argument, config_packages,
                       installed_config_refs, profile_args, run)


@conan_command(group="Maturity")
def config_lock_update(conan_api, parser, *args):
    """
    Re-resolve the config packages in conanconfig.yml, install them, and pin them in conan.lock
    and in every products/*.lock.
    """
    add_path_argument(parser)
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    packages = config_packages(root)

    # install-pkg never builds; build config packages whose remote has a recipe but no binary.
    for ref in packages:
        run(conan_api, ["install", f"--requires={ref}", "--build=missing", "--lockfile=",
                        f"--output-folder={os.path.join(root, 'build', 'conan-config')}",
                        *profile_args(BUILD_TARGET, "release")])
    run(conan_api, ["config", "install-pkg", root, "--lockfile="])

    products_dir = os.path.join(root, PRODUCTS_DIR)
    locks = [os.path.join(root, "conan.lock")] + sorted(
        os.path.join(products_dir, f) for f in os.listdir(products_dir) if f.endswith(".lock"))
    pins = [f"--config-requires={ref}" for ref in installed_config_refs(conan_api)]
    for lock in locks:
        lock_in = f"--lockfile={lock}"
        if os.path.isfile(lock):
            run(conan_api, ["lock", "remove", lock_in, f"--lockfile-out={lock}",
                            *[f"--config-requires={ref.split('/')[0]}/*" for ref in packages]])
        else:
            lock_in = "--lockfile="
        run(conan_api, ["lock", "add", lock_in, f"--lockfile-out={lock}", *pins])
