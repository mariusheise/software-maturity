from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class MaturityConan(ConanFile):
    name = "maturity"
    version = "0.1.0"
    settings = "os", "compiler", "build_type", "arch"
    options = {"product": ["ANY"]}
    default_options = {"product": "productA"}
    generators = "CMakeDeps"

    def requirements(self):
        self.test_requires("gtest/1.14.0")
        if self.options.product == "productB":
            self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Conan only sets BUILD_TESTING=OFF for tools.build:skip_test; set it both ways so an OFF
        # cached by a skip-test build does not leave later builds without (rebuilt) tests.
        skip_test = self.conf.get("tools.build:skip_test", default=False, check_type=bool)
        tc.cache_variables["BUILD_TESTING"] = "OFF" if skip_test else "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])
