from conan import ConanFile
from conan.tools.files import copy


class MaturityConfigConan(ConanFile):
    name = "maturity-config"
    description = "Shared Conan configuration (profiles, custom commands) for the maturity products"
    package_type = "configuration"
    exports_sources = "profiles/*", "extensions/*"

    def package(self):
        for pattern in ("profiles/*", "extensions/*"):
            copy(self, pattern, self.source_folder, self.package_folder, excludes="*.pyc")
