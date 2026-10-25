from conan import ConanFile
from conan.tools.files import copy


class MaturityConfigConan(ConanFile):
    name = "maturity-config"
    description = "Shared Conan configuration (profiles, custom commands) for the maturity products"
    package_type = "configuration"
    # test/ (the tests of the custom commands) and bytecode stay out of the recipe revision
    exports_sources = "profiles/*", "extensions/*", "!*.pyc"

    def package(self):
        for pattern in ("profiles/*", "extensions/*"):
            copy(self, pattern, self.source_folder, self.package_folder)
