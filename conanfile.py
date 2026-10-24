from conan import ConanFile
from conan.tools.cmake import cmake_layout


class MaturityConan(ConanFile):
    name = "maturity"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.test_requires("gtest/1.14.0")

    def layout(self):
        cmake_layout(self)
