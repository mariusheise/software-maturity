import glob
import os
import shutil
import subprocess

from conan.api.output import ConanOutput
from conan.cli.command import conan_command
from conan.errors import ConanException

from _coverage import write_summary
from _maturity import add_path_argument, graph_args, run

# Set by the maturity/coverage profile (build_folder_vars=["const.coverage"]).
BUILD_FOLDER = os.path.join("build", "coverage")
REPORT_FOLDER = os.path.join("build", "coverage-report")


@conan_command(group="Maturity")
def coverage(conan_api, parser, *args):
    """
    Build and test a product variant with coverage instrumentation, write the gcovr reports to
    build/coverage-report/ and enforce the line-coverage gate.
    """
    add_path_argument(parser)
    parser.add_argument("--product", required=True, help="Product variant from products/")
    parser.add_argument("--target", required=True, help="Target profile, e.g. linux-x86_64")
    parser.add_argument("--fail-under", type=float, default=90.0,
                        help="Minimum line coverage in percent (default: 90)")
    parser.add_argument("--diff-base", help="Also report coverage of the lines changed since the "
                                            "merge base with this revision, e.g. origin/main")
    parser.add_argument("--build", default="missing", help="Conan --build policy (default: missing)")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    build_args = graph_args(conan_api, root, args.product, args.target, "debug")
    gcovr = shutil.which("gcovr")
    if not gcovr:
        raise ConanException("gcovr not found. Install it, e.g. "
                             "'pip install -r .devcontainer/requirements.txt'")

    # Counters from earlier runs would add up with this one.
    for stale in glob.glob(os.path.join(root, BUILD_FOLDER, "**", "*.gcda"), recursive=True):
        os.remove(stale)

    run(conan_api, ["build", *build_args, "-pr:h=maturity/coverage", f"--build={args.build}"])
    if not os.path.isdir(os.path.join(root, BUILD_FOLDER)):
        raise ConanException(f"No build folder {BUILD_FOLDER}. The recipe needs cmake_layout() "
                             "and a build() that builds and runs the tests")

    reports = os.path.join(root, REPORT_FOLDER)
    os.makedirs(reports, exist_ok=True)
    json_path = os.path.join(reports, "coverage.json")
    html_path = os.path.join(reports, "coverage-report.html")
    # Filters and exclusions come from the project's gcovr.cfg, found in the working directory.
    cmd = [gcovr, "--print-summary",
           "--xml-pretty", "--output", os.path.join(reports, "coverage.xml"),
           "--json", json_path,
           "--html-details", html_path, "--html-single-page", "--html-self-contained",
           os.path.join(root, BUILD_FOLDER)]
    ConanOutput().info("Running: " + " ".join(cmd))
    subprocess.run(cmd, cwd=root, check=True)

    pct, text = write_summary(json_path, os.path.join(reports, "coverage-summary.md"), root,
                              args.diff_base)
    ConanOutput().info(text)
    ConanOutput().info(f"Report: file://{html_path}")
    if pct < args.fail_under:
        raise ConanException(f"Line coverage {pct:.1f}% is below the gate of {args.fail_under:g}%")
    ConanOutput().success(f"Line coverage {pct:.1f}% meets the gate of {args.fail_under:g}%")
