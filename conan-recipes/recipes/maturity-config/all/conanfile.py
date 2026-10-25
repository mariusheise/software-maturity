from conan import ConanFile
from conan.tools.files import copy


class MaturityConfigConan(ConanFile):
    name = "maturity-config"
    description = "Shared Conan configuration (profiles) for the maturity products"
    package_type = "configuration"
    exports_sources = "profiles/*"

    def package(self):
        copy(self, "profiles/*", self.source_folder, self.package_folder)
