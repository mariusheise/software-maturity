"""Layer 2: the maturity:* commands, loaded from the source folder into a throwaway Conan home."""

import json
import os
import stat
import textwrap

from conftest import (COMMANDS, FIXTURE_CONANFILE, OTHER_CONFIG_REF, TestClient, recipe_profiles,
                      save_project)

# The fixture with the folder layout maturity:coverage expects; build() runs no tests, so
# gcovr finds no data and reports 100%.
COVERAGE_CONANFILE = FIXTURE_CONANFILE.replace(
    "from conan import ConanFile\n",
    "from conan import ConanFile\nfrom conan.tools.cmake import cmake_layout\n") + (
    "\n    def layout(self):\n        cmake_layout(self)\n")


def lock(client, product):
    with open(os.path.join(client.current_folder, "products", f"{product}.lock"),
              encoding="utf-8") as f:
        return json.load(f)


def test_commands_are_listed(client):
    client.run("-h")
    for command in ("maturity:install", "maturity:lock-update", "maturity:config-lock-update",
                    "maturity:coverage", "maturity:build", "maturity:tidy", "maturity:list", "maturity:audit"):
        assert command in client.out


def test_lock_update_creates_a_lock_per_product(client):
    client.run("maturity:lock-update")
    assert lock(client, "productA")["requires"] == []
    assert lock(client, "productB")["config_requires"] == []


def test_lock_update_limits_to_one_product(client):
    client.run("maturity:lock-update --product productB")
    assert not os.path.exists(os.path.join(client.current_folder, "products", "productA.lock"))
    assert os.path.exists(os.path.join(client.current_folder, "products", "productB.lock"))


def test_lock_update_covers_every_build_type(client):
    client.run("maturity:lock-update --product productA")
    assert "-pr:h=maturity/build_type/debug" in client.out
    assert "-pr:h=maturity/build_type/release" in client.out


def test_install_composes_lock_options_and_profiles(client):
    client.run("maturity:lock-update")
    client.run("maturity:install --product=productB --target=linux-x86_64 --build-type=debug")
    assert "--lockfile=" + os.path.join(client.current_folder, "products", "productB.lock") in client.out
    assert "-o=&:product=productB" in client.out
    assert "-pr:h=maturity/target/linux-x86_64 -pr:h=maturity/build_type/debug" in client.out
    assert "build_type=Debug" in client.out
    assert "compiler.cppstd=20" in client.out


def test_install_defaults_to_release(client):
    client.run("maturity:lock-update --product productA")
    client.run("maturity:install --product=productA --target=linux-x86_64")
    assert "build_type=Release" in client.out


def test_install_rejects_unknown_values(client):
    client.run("maturity:lock-update")
    for args, message in [
        ("--product=nope --target=linux-x86_64", "Unknown product 'nope'. Available: productA, productB"),
        ("--product=productA --target=win", "Unknown target 'win'. Available: linux-x86_64"),
        ("--product=productA --target=linux-x86_64 --build-type=relwithdebinfo",
         "Unknown build type 'relwithdebinfo'. Available: debug, release"),
    ]:
        client.run(f"maturity:install {args}", assert_error=True)
        assert message in client.out


def test_install_needs_the_product_lock(client):
    client.run("maturity:install --product=productA --target=linux-x86_64", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out


def test_lock_update_pins_the_installed_config(client):
    client.save_home({"config_version.json": json.dumps({"config_version": [OTHER_CONFIG_REF]})})
    client.run("maturity:lock-update --product productA")
    assert lock(client, "productA")["config_requires"] == [OTHER_CONFIG_REF]


def test_install_fails_when_the_installed_config_differs_from_the_lock(client):
    client.save_home({"config_version.json": json.dumps({"config_version": [OTHER_CONFIG_REF]})})
    client.run("maturity:lock-update --product productA")
    installed = "maturity-config/0.1.0#" + "1" * 32
    client.save_home({"config_version.json": json.dumps({"config_version": [installed]})})
    client.run("maturity:install --product=productA --target=linux-x86_64", assert_error=True)
    assert "not in the lockfile" in client.out


# The fixture with a build() that reports Conan's test flag.
BUILD_CONANFILE = FIXTURE_CONANFILE + (
    "\n    def build(self):\n"
    "        self.output.info(f\"skip_test={self.conf.get('tools.build:skip_test')}\")\n")


def test_build_runs_conan_build_with_lock_options_and_profiles(client):
    client.save({"conanfile.py": BUILD_CONANFILE})
    client.run("maturity:lock-update --product productB")
    client.run("maturity:build --product=productB --target=linux-x86_64")
    assert "Running: conan build " in client.out
    assert "--lockfile=" + os.path.join(client.current_folder, "products", "productB.lock") in client.out
    assert "-o=&:product=productB" in client.out
    assert "-pr:h=maturity/target/linux-x86_64 -pr:h=maturity/build_type/release" in client.out
    assert "build_type=Release" in client.out
    assert "skip_test=None" in client.out
    assert "tools.build:skip_test" not in client.out.split("Running: ")[1].splitlines()[0]


def test_build_skip_test_sets_the_conan_test_flag(client):
    client.save({"conanfile.py": BUILD_CONANFILE})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:build --product=productA --target=linux-x86_64 --build-type=debug --skip-test")
    assert "-c tools.build:skip_test=True" in client.out
    assert "build_type=Debug" in client.out
    assert "skip_test=True" in client.out


def test_build_passes_the_version_through(client):
    # The project recipe has no version; CI passes it from the release tag.
    unversioned = BUILD_CONANFILE.replace('    version = "1.0"\n', "") + (
        "        self.output.info(f\"version={self.version}\")\n")
    client.save({"conanfile.py": unversioned})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:build --product=productA --target=linux-x86_64 --version=1.2.3-rc.1")
    assert "--version 1.2.3-rc.1" in client.out
    assert "version=1.2.3-rc.1" in client.out
    client.run("maturity:build --product=productA --target=linux-x86_64")
    assert "version=None" in client.out


# The fixture whose build() writes a JUnit file where maturity:build asks for it, like ctest.
JUNIT_CONANFILE = FIXTURE_CONANFILE.replace(
    "from conan import ConanFile\n", "from conan import ConanFile\nfrom conan.tools.files import save\n") + (
    "\n    def build(self):\n"
    "        junit = self.conf.get('user.maturity:junit')\n"
    "        self.output.info(f'junit={junit}')\n"
    "        status = 'fail' if self.options.product == 'productB' else 'run'\n"
    "        if junit:\n"
    "            save(self, junit, '<testsuite><testcase name=\"t1\" time=\"0.5\" '\n"
    "                 f'status=\"{status}\"/></testsuite>')\n"
    "        if status == 'fail':\n"
    "            raise Exception('tests failed')\n")


def test_build_writes_the_test_report(client):
    client.save({"conanfile.py": JUNIT_CONANFILE})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:build --product=productA --target=linux-x86_64")
    stem = os.path.join(client.current_folder, "build", "test-report", "productA-release")
    assert f"junit={stem}.xml" in client.out
    for ext in (".html", ".md", ".json"):
        assert os.path.isfile(stem + ext)
    with open(stem + ".json", encoding="utf-8") as f:
        assert json.load(f)["passed"] == 1
    assert "### Tests: productA, release" in client.out
    assert f"Test report: file://{stem}.html" in client.out


def test_build_writes_the_report_even_when_tests_fail(client):
    client.save({"conanfile.py": JUNIT_CONANFILE})
    client.run("maturity:lock-update --product productB")
    client.run("maturity:build --product=productB --target=linux-x86_64", assert_error=True)
    assert "tests failed" in client.out
    stem = os.path.join(client.current_folder, "build", "test-report", "productB-release")
    with open(stem + ".json", encoding="utf-8") as f:
        assert json.load(f)["failed"] == 1


def test_build_skip_test_writes_no_report(client):
    client.save({"conanfile.py": JUNIT_CONANFILE})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:build --product=productA --target=linux-x86_64 --skip-test")
    assert "junit=None" in client.out
    assert not os.path.exists(os.path.join(client.current_folder, "build", "test-report"))


def test_build_rejects_unknown_values_and_needs_the_lock(client):
    client.run("maturity:build --product=nope --target=linux-x86_64", assert_error=True)
    assert "Unknown product 'nope'" in client.out
    client.run("maturity:build --product=productA --target=linux-x86_64", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out


def test_coverage_builds_with_the_coverage_profile_and_writes_reports(client):
    client.save({"conanfile.py": COVERAGE_CONANFILE})
    client.run("maturity:lock-update --product productB")
    client.run("maturity:coverage --product=productB --target=linux-x86_64")
    assert "Running: conan build " in client.out
    assert "--lockfile=" + os.path.join(client.current_folder, "products", "productB.lock") in client.out
    assert "-o=&:product=productB" in client.out
    assert "-pr:h=maturity/build_type/debug" in client.out
    assert "-pr:h=maturity/coverage" in client.out
    assert "build_type=Debug" in client.out
    assert "&:tools.build:cxxflags" in client.out
    reports = os.path.join(client.current_folder, "build", "coverage-report")
    for name in ("coverage.json", "coverage.xml", "coverage-report.html", "coverage-summary.md"):
        assert os.path.isfile(os.path.join(reports, name))
    assert "Line coverage 100.0% meets the gate of 90%" in client.out
    assert os.path.isdir(os.path.join(client.current_folder, "build", "coverage", "Debug"))
    client.run("maturity:coverage --product=productB --target=linux-x86_64 --fail-under=101",
               assert_error=True)
    assert "Line coverage 100.0% is below the gate of 101%" in client.out


def test_coverage_needs_the_coverage_build_folder(client):
    client.run("maturity:lock-update --product productA")
    client.run("maturity:coverage --product=productA --target=linux-x86_64", assert_error=True)
    assert "No build folder build/coverage" in client.out


def test_coverage_rejects_unknown_values_and_needs_the_lock(client):
    client.run("maturity:coverage --product=nope --target=linux-x86_64", assert_error=True)
    assert "Unknown product 'nope'" in client.out
    client.run("maturity:coverage --product=productA --target=win", assert_error=True)
    assert "Unknown target 'win'" in client.out
    client.run("maturity:coverage --product=productA --target=linux-x86_64", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out


def test_coverage_needs_gcovr(client, monkeypatch):
    client.run("maturity:lock-update --product productA")
    monkeypatch.setenv("PATH", "")
    client.run("maturity:coverage --product=productA --target=linux-x86_64", assert_error=True)
    assert "gcovr not found" in client.out


def test_config_lock_update_builds_the_revision_install_pkg_will_pick(tmp_path):
    """The remote has a newer config revision without a binary, the cache an older one with a
    binary. The build step must resolve the remote's revision, as install-pkg does."""
    c = TestClient(custom_commands_folder=COMMANDS, default_server_user=True)
    c.save_home(recipe_profiles())
    save_project(c, conanconfig="packages:\n  - cfg/[>=0.1 <1]\n")
    recipe = textwrap.dedent("""\
        from conan import ConanFile
        from conan.tools.files import save

        class Cfg(ConanFile):
            name = "cfg"
            package_type = "configuration"

            def package(self):
                save(self, self.package_folder + "/cfg.txt", "{content}")
        """)
    c.save({"cfg/conanfile.py": recipe.format(content="old")})
    c.run("create cfg --version 0.1.0")
    c.run("upload cfg/0.1.0 -r default -c")
    c.save({"cfg/conanfile.py": recipe.format(content="new")})
    c.run("export cfg --version 0.1.0")
    new_rev = c.exported_recipe_revision()
    c.run("upload cfg/0.1.0 -r default -c --only-recipe")
    c.run(f"remove cfg/0.1.0#{new_rev} -c")

    c.run("maturity:config-lock-update")
    assert "--update=cfg" in c.out
    with open(os.path.join(c.current_folder, "conan.lock"), encoding="utf-8") as f:
        assert json.load(f)["config_requires"] == [f"cfg/0.1.0#{new_rev}"]


def fake_tools(folder, finding=False):
    """Stand-ins for cmake (writes a compile database) and clang-tidy (echoes a finding)."""
    tools = {
        "cmake": textwrap.dedent("""\
            #!/bin/sh
            echo "cmake $*" >> build/tidy/fake.log
            printf '[{"directory": "%s", "file": "src/a.cpp"},
                     {"directory": "%s", "file": "build/tidy/Debug/gen.cpp"},
                     {"directory": "/elsewhere", "file": "dep.cpp"}]' \\
                "$PWD" "$PWD" > build/tidy/Debug/compile_commands.json
            """),
        "clang-tidy": textwrap.dedent(f"""\
            #!/bin/sh
            [ "$1" = "--version" ] && echo "LLVM version 23.1.3" && exit 0
            echo "clang-tidy $*" >> build/tidy/fake.log
            {'echo "$PWD/src/a.cpp:1:1: error: bad [modernize-x]"; exit 1' if finding else 'exit 0'}
            """),
    }
    for name, script in tools.items():
        path = os.path.join(folder, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def tidy_client(client, monkeypatch, tmp_path, finding=False):
    client.save({"conanfile.py": COVERAGE_CONANFILE})
    client.run("maturity:lock-update --product productA")
    fake_tools(str(tmp_path), finding)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    return os.path.join(client.current_folder, "build", "tidy")


def test_tidy_configures_its_own_folder_and_checks_project_sources(client, monkeypatch, tmp_path):
    folder = tidy_client(client, monkeypatch, tmp_path)
    client.run("maturity:tidy --product=productA --target=linux-x86_64")
    assert "-pr:h=maturity/tidy" in client.out
    assert "LLVM version 23.1.3" in client.out
    with open(os.path.join(folder, "fake.log"), encoding="utf-8") as f:
        calls = f.read().splitlines()
    assert calls[0] == "cmake --preset conan-tidy-debug"
    assert calls[1] == "clang-tidy -p " + os.path.join(folder, "Debug") + " src/a.cpp"
    reports = os.path.join(client.current_folder, "build", "tidy-report")
    assert os.path.isfile(os.path.join(reports, "clang-tidy.log"))
    assert os.path.isfile(os.path.join(reports, "clang-tidy.sarif"))
    assert "clang-tidy: no findings in 1 file(s)" in client.out


def test_tidy_fails_on_findings_and_writes_sarif(client, monkeypatch, tmp_path):
    tidy_client(client, monkeypatch, tmp_path, finding=True)
    client.run("maturity:tidy --product=productA --target=linux-x86_64", assert_error=True)
    assert "clang-tidy reported 1 finding(s) in 1 file(s)" in client.out
    with open(os.path.join(client.current_folder, "build", "tidy-report", "clang-tidy.sarif"),
              encoding="utf-8") as f:
        assert json.load(f)["runs"][0]["results"][0]["ruleId"] == "modernize-x"


def test_tidy_fix_applies_then_checks(client, monkeypatch, tmp_path):
    folder = tidy_client(client, monkeypatch, tmp_path)
    client.run("maturity:tidy --product=productA --target=linux-x86_64 --fix")
    with open(os.path.join(folder, "fake.log"), encoding="utf-8") as f:
        calls = [c for c in f.read().splitlines() if c.startswith("clang-tidy")]
    debug = os.path.join(folder, "Debug")
    assert calls == [f"clang-tidy -p {debug} --fix src/a.cpp", f"clang-tidy -p {debug} src/a.cpp"]


def test_tidy_needs_clang_tidy_and_the_lock(client, monkeypatch):
    client.run("maturity:tidy --product=productA --target=linux-x86_64", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out
    client.run("maturity:lock-update --product productA")
    monkeypatch.setenv("PATH", "")
    client.run("maturity:tidy --product=productA --target=linux-x86_64", assert_error=True)
    assert "clang-tidy not found" in client.out


def test_list_prints_the_products(client):
    client.save({"products/productB.yml": "description: B with zlib\noptions:\n  product: productB\n"
                                          "coverage:\n  fail_under: 85\n"})
    client.run("maturity:list")
    assert "productA" in client.out and "productB" in client.out
    assert "B with zlib" in client.out
    assert "linux-x86_64" in client.out


def test_list_json_has_the_merged_manifests(client):
    client.save({"products/productB.yml": "options:\n  product: productB\ncoverage:\n  fail_under: 85\n"})
    client.run("maturity:list --format=json")
    data = json.loads(client.stdout)
    assert sorted(data["products"]) == ["productA", "productB"]
    b = data["products"]["productB"]
    assert b["options"] == {"product": "productB"}
    assert b["coverage"] == {"fail_under": 85} and b["release"] == {"latest": None}
    assert b["targets"] == ["linux-x86_64"]
    assert data["targets"] == ["linux-x86_64"] and data["build_types"] == ["debug", "release"]
    client.run("maturity:list --product productA --format=json")
    assert list(json.loads(client.stdout)["products"]) == ["productA"]


def test_list_rejects_a_broken_manifest(client):
    client.save({"products/productB.yml": "options:\n  product: productB\ncolour: red\n"})
    client.run("maturity:list", assert_error=True)
    assert "products/productB.yml: unknown key 'colour'" in client.out
    client.run("maturity:list --product nope", assert_error=True)


# The fixture whose build() reports the product conf it received.
CONF_CONANFILE = FIXTURE_CONANFILE + (
    "\n    def build(self):\n"
    "        self.output.info(f\"log_level={self.conf.get('user.maturity.product:log_level')}\")\n")


def test_manifest_conf_reaches_the_recipe(client):
    client.save({"conanfile.py": CONF_CONANFILE,
                 "products/productA.yml": "options:\n  product: productA\nconf:\n  log_level: debug\n"})
    client.run("maturity:lock-update --product productA")
    assert "-c user.maturity.product:log_level=debug" in client.out
    client.run("maturity:build --product=productA --target=linux-x86_64")
    assert "-c user.maturity.product:log_level=debug" in client.out
    assert "log_level=debug" in client.out


def two_targets(client):
    """A second target profile next to linux-x86_64."""
    profiles = recipe_profiles()
    armv8 = profiles[os.path.join("profiles", "maturity", "target", "linux-x86_64")].replace(
        "arch=x86_64", "arch=armv8")
    client.save_home({os.path.join("profiles", "maturity", "target", "linux-armv8"): armv8})


def test_lock_update_locks_only_the_product_targets(client):
    two_targets(client)
    client.save({"products/productA.yml": "options:\n  product: productA\ntargets: [linux-x86_64]\n"})
    client.run("maturity:lock-update")
    runs = [line for line in client.out.splitlines() if line.startswith("Running: conan lock create")]
    a = [r for r in runs if "product=productA" in r]
    b = [r for r in runs if "product=productB" in r]
    assert a and not any("linux-armv8" in r for r in a)
    assert any("target/linux-armv8" in r for r in b) and any("target/linux-x86_64" in r for r in b)


def test_commands_reject_a_target_the_product_does_not_list(client):
    two_targets(client)
    client.save({"products/productA.yml": "options:\n  product: productA\ntargets: [linux-x86_64]\n"})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:build --product=productA --target=linux-armv8", assert_error=True)
    assert "Unknown target 'linux-armv8'. Available: linux-x86_64" in client.out


def test_coverage_gate_comes_from_the_manifest(client):
    client.save({"conanfile.py": COVERAGE_CONANFILE,
                 "products/productA.yml": "options:\n  product: productA\ncoverage:\n  fail_under: 100\n"})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:coverage --product=productA --target=linux-x86_64")
    assert "meets the gate of 100% (products/productA.yml)" in client.out
    client.run("maturity:coverage --product=productA --target=linux-x86_64 --fail-under=50")
    assert "meets the gate of 50% (--fail-under)" in client.out
    client.run("maturity:coverage --product=productB --target=linux-x86_64", assert_error=True)
    client.run("maturity:lock-update --product productB")
    client.run("maturity:coverage --product=productB --target=linux-x86_64")
    assert "meets the gate of 90% (defaults.yml)" in client.out


def test_lock_update_with_a_target_the_product_does_not_list(client):
    two_targets(client)
    client.save({"products/productA.yml": "options:\n  product: productA\ntargets: [linux-x86_64]\n"})
    client.run("maturity:lock-update --product productA --target linux-armv8", assert_error=True)
    assert "productA does not support target 'linux-armv8'. Supported: linux-x86_64" in client.out
    client.run("maturity:lock-update --target linux-armv8")
    assert "productA does not support target 'linux-armv8', skipped" in client.out
    assert os.path.exists(os.path.join(client.current_folder, "products", "productB.lock"))
    assert not os.path.exists(os.path.join(client.current_folder, "products", "productA.lock"))


def scan_result(score=None, unscanned=False):
    """A 'conan audit scan' result: zlib with one vulnerability of <score>, or none."""
    edges = [] if score is None else [{"node": {"name": "CVE-2026-0001", "severity": "High",
                                                "cvss": {"preferredBaseScore": score}}}]
    data = {"zlib/1.3.1": {"vulnerabilities": {"totalCount": len(edges), "edges": edges}}}
    if unscanned:
        data["private/1.0"] = {"error": {"details": "Not found."}}
    return {"data": data, "provider_url": "https://audit.example"}


def fake_audit(monkeypatch, result):
    """Replace the audit provider, so no token or network is needed; returns the scan calls."""
    from conan.api.subapi.audit import AuditAPI
    calls = []
    monkeypatch.setattr(AuditAPI, "get_provider", lambda self, name: name)

    def scan(deps_graph, provider, context=None):
        calls.append(provider)
        return result
    monkeypatch.setattr(AuditAPI, "scan", staticmethod(scan))
    return calls


def test_audit_scans_every_product_and_writes_reports(client, monkeypatch):
    calls = fake_audit(monkeypatch, scan_result(score=5.3, unscanned=True))
    client.run("maturity:lock-update")
    client.run("maturity:audit")
    assert calls == ["conancenter", "conancenter"]
    assert "-o=&:product=productB" in client.out
    assert "-pr:h=maturity/build_type/release" in client.out
    assert "1 known vulnerabilities** in 2 package(s), 0 at or above the gate of CVSS 7" in client.out
    assert "Not scanned: private/1.0 (Not found.)" in client.out
    reports = os.path.join(client.current_folder, "build", "audit-report")
    for ext in ("json", "html", "md"):
        assert os.path.isfile(os.path.join(reports, f"productA-linux-x86_64.{ext}"))
    with open(os.path.join(reports, "productB-linux-x86_64.html"), encoding="utf-8") as f:
        assert "CVE-2026-0001" in f.read()


def test_audit_fails_at_the_gate_from_the_manifest_or_the_flag(client, monkeypatch):
    fake_audit(monkeypatch, scan_result(score=7.5))
    client.save({"products/productA.yml": "options:\n  product: productA\naudit:\n  severity_level: 8\n"})
    client.run("maturity:lock-update")
    client.run("maturity:audit --product productA")
    assert "No known vulnerabilities at or above the gate" in client.out
    client.run("maturity:audit", assert_error=True)
    assert "productB (linux-x86_64): zlib/1.3.1 CVE-2026-0001 CVSS 7.5 (gate 7)" in client.out
    assert "productA (linux-x86_64)" not in client.out.split("at or above the gate:")[-1]
    client.run("maturity:audit --product productA --severity-level 7.5", assert_error=True)


def test_audit_reports_a_failed_scan(client, monkeypatch):
    fake_audit(monkeypatch, {"data": {}, "conan_error": "Authentication error (401)."})
    client.run("maturity:lock-update --product productA")
    client.run("maturity:audit --product productA", assert_error=True)
    assert "Audit of productA (linux-x86_64) failed: Authentication error (401)." in client.out


def test_audit_rejects_unknown_values_and_needs_the_lock(client, monkeypatch):
    fake_audit(monkeypatch, scan_result())
    client.run("maturity:audit --product nope", assert_error=True)
    assert "Unknown product 'nope'" in client.out
    client.run("maturity:audit --product productA", assert_error=True)
    assert "Run 'conan maturity:lock-update --product productA'" in client.out
    client.run("maturity:lock-update --product productA")
    client.run("maturity:audit --product productA --target win", assert_error=True)
    assert "Unknown target 'win'" in client.out
