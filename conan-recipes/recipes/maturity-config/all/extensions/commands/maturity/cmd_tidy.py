import json
import os
import shutil
import subprocess

from conan.api.output import ConanOutput
from conan.cli.command import conan_command
from conan.errors import ConanException

from _coverage import changed_lines
from _maturity import add_path_argument, graph_args, run
from _sarif import write_sarif

# Set by the maturity/tidy profile (build_folder_vars=["const.tidy"]).
BUILD_FOLDER = os.path.join("build", "tidy", "Debug")
PRESET = "conan-tidy-debug"
REPORT_FOLDER = os.path.join("build", "tidy-report")


def source_files(root, build_folder):
    """Translation units of the project: compile database entries under <root>, not in build/."""
    with open(os.path.join(build_folder, "compile_commands.json"), encoding="utf-8") as f:
        entries = json.load(f)
    build = os.path.join(root, "build", "")
    files = set()
    for entry in entries:
        path = os.path.normpath(os.path.join(entry["directory"], entry["file"]))
        if path.startswith(os.path.join(root, "")) and not path.startswith(build):
            files.add(os.path.relpath(path, root))
    return sorted(files)


@conan_command(group="Maturity")
def tidy(conan_api, parser, *args):
    """
    Run clang-tidy on the project's sources for a product variant, with the project's
    .clang-tidy, write the log and SARIF to build/tidy-report/ and fail on findings.
    """
    add_path_argument(parser)
    parser.add_argument("--product", required=True, help="Product variant from products/")
    parser.add_argument("--target", required=True, help="Target profile, e.g. linux-x86_64")
    parser.add_argument("--diff-base", help="Only check files changed since the merge base with "
                                            "this revision, e.g. origin/main")
    parser.add_argument("--fix", action="store_true", help="Apply clang-tidy's fixes")
    parser.add_argument("--build", default="missing", help="Conan --build policy (default: missing)")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    install_args = graph_args(conan_api, root, args.product, args.target, "debug")
    tools = {name: shutil.which(name) for name in ("clang-tidy", "cmake")}
    for name, exe in tools.items():
        if not exe:
            raise ConanException(f"{name} not found. Install it, e.g. "
                                 "'pip install -r .devcontainer/requirements.txt'")
    version = subprocess.run([tools["clang-tidy"], "--version"], check=True, capture_output=True,
                             text=True).stdout
    ConanOutput().info(" ".join(version.split()))

    # Configure only: the compile database is all clang-tidy needs.
    run(conan_api, ["install", *install_args, "-pr:h=maturity/tidy", f"--build={args.build}"])
    subprocess.run([tools["cmake"], "--preset", PRESET], cwd=root, check=True,
                   stdout=subprocess.DEVNULL)

    build_folder = os.path.join(root, BUILD_FOLDER)
    files = source_files(root, build_folder)
    if args.diff_base:
        changed = changed_lines(root, args.diff_base)
        files = [f for f in files if f in changed]
    reports = os.path.join(root, REPORT_FOLDER)
    os.makedirs(reports, exist_ok=True)
    log_path = os.path.join(reports, "clang-tidy.log")
    sarif_path = os.path.join(reports, "clang-tidy.sarif")

    def clang_tidy(extra=()):
        cmd = [tools["clang-tidy"], "-p", build_folder, *extra, *files]
        ConanOutput().info("Running: " + " ".join(cmd))
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        ConanOutput().info(result.stdout + result.stderr)
        return result.stdout + result.stderr, result.returncode

    log, status = "", 0
    if files:
        if args.fix:
            # clang-tidy reports the findings it fixes; the check after it reports what is left.
            clang_tidy(["--fix"])
        log, status = clang_tidy()
    else:
        ConanOutput().info("No changed source files to check")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log)
    findings = write_sarif(log, root, sarif_path)

    ConanOutput().info(f"Report: {log_path}, {sarif_path}")
    if status or findings:
        raise ConanException(f"clang-tidy reported {findings} finding(s) in {len(files)} file(s)")
    ConanOutput().success(f"clang-tidy: no findings in {len(files)} file(s)")
