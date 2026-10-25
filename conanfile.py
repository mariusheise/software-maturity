from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class MaturityConan(ConanFile):
    name = "maturity"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"
    options = {"product": ["ANY"]}
    default_options = {"product": "productA"}
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.test_requires("gtest/1.14.0")
        if self.options.product == "productB":
            self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.ctest(cli_args=["--output-on-failure"])
