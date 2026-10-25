import os

from conan.api.output import ConanOutput
from conan.cli.command import conan_command
from conan.errors import ConanException

from _audit import write_report
from _maturity import (add_path_argument, check_choice, discover_products, graph_args,
                       product_targets, run)

REPORT_FOLDER = os.path.join("build", "audit-report")
TOKEN_VARIABLE = "CONAN_AUDIT_PROVIDER_TOKEN_CONANCENTER"


@conan_command(group="Maturity")
def audit(conan_api, parser, *args):
    """
    Scan the locked dependencies of every product variant (or one) for known vulnerabilities
    with 'conan audit scan', write the reports to build/audit-report/ and fail on a
    vulnerability at or above the product's CVSS gate that its audit.ignore doesn't accept.
    """
    add_path_argument(parser)
    parser.add_argument("--product", help="Product variant from products/ (default: all)")
    parser.add_argument("--target", help="Target profile (default: every target of the product)")
    parser.add_argument("--severity-level", type=float,
                        help="Fail on a vulnerability with this CVSS score or higher (default: the "
                             "product's audit.severity_level, 7.0 unless the manifest sets it)")
    parser.add_argument("--provider", default="conancenter",
                        help="Audit provider (default: conancenter, token in "
                             f"{TOKEN_VARIABLE} or 'conan audit provider auth')")
    args = parser.parse_args(*args)

    root = os.path.abspath(args.path)
    products = discover_products(root)
    if args.product:
        check_choice("product", args.product, list(products))
        products = {args.product: products[args.product]}

    failing = []
    for name, product in products.items():
        threshold = (args.severity_level if args.severity_level is not None
                     else product["audit"]["severity_level"])
        ignore = product["audit"].get("ignore") or {}
        seen = set()
        targets = product_targets(conan_api, product)
        if args.target:
            check_choice("target", args.target, targets)
            targets = [args.target]
        for target in targets:
            # The gate is applied here, per product, so Conan's own threshold is switched off.
            result = run(conan_api, ["audit", "scan",
                                     *graph_args(conan_api, root, name, target, "release"),
                                     f"--provider={args.provider}", "--severity-level=100"],
                         raise_on_errors=False)
            if error := result.get("conan_error"):
                raise ConanException(f"Audit of {name} ({target}) failed: {error}")
            stem = os.path.join(root, REPORT_FOLDER, f"{name}-{target}")
            rows, above, text = write_report(result, stem, f"Audit: {name} ({target})", threshold,
                                             ignore)
            seen.update(r["id"] for r in rows)
            ConanOutput().info(text)
            ConanOutput().info(f"Report: file://{stem}.html")
            failing += [f"{name} ({target}): {r['package']} {r['id']} CVSS {r['score']:g} "
                        f"(gate {threshold:g})" for r in above]
        # An accepted id the provider no longer reports was fixed or withdrawn: drop it.
        for stale in sorted(set(ignore) - seen):
            ConanOutput().warning(f"products/{name}.yml: audit.ignore lists {stale}, which no "
                                  "longer affects it; remove the entry")
    if failing:
        raise ConanException("Vulnerabilities failing the gate (accept one with audit.ignore in the "
                             "product manifest):\n  " + "\n  ".join(failing))
    ConanOutput().success("No vulnerabilities fail the gate")
