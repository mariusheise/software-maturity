cmake_minimum_required(VERSION 3.23)

# Set by conanfile.py from "conan maturity:build --version" (the release tag); builds without a
# version are 0.0.0-dev. project() takes only the numeric part, version.hpp the full string.
set(MATURITY_VERSION "0.0.0-dev" CACHE STRING "Version, e.g. 1.2.3 or 1.2.3-rc.1")
string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" MATURITY_VERSION_NUMERIC "${MATURITY_VERSION}")
if(NOT MATURITY_VERSION_NUMERIC)
  message(FATAL_ERROR "MATURITY_VERSION '${MATURITY_VERSION}' does not start with <major>.<minor>.<patch>")
endif()
project(maturity VERSION ${MATURITY_VERSION_NUMERIC} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(maturity src/stats.cpp src/password.cpp)
target_include_directories(maturity PUBLIC include)
target_compile_options(maturity PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic -Werror>)

configure_file(src/version.hpp.in ${CMAKE_CURRENT_BINARY_DIR}/generated/maturity/version.hpp @ONLY)

add_executable(maturity_app src/main.cpp)
target_include_directories(maturity_app PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/generated)
target_link_libraries(maturity_app PRIVATE maturity)

include(CTest)
if(BUILD_TESTING)
  find_package(GTest REQUIRED)
  add_executable(maturity_tests tests/stats_test.cpp tests/password_test.cpp)
  target_link_libraries(maturity_tests PRIVATE maturity GTest::gtest_main)
  include(GoogleTest)
  gtest_discover_tests(maturity_tests)

  # The version passed to the build reaches the binary.
  string(REPLACE "." "\\." version_regex "${MATURITY_VERSION}")
  add_test(NAME maturity_app.version COMMAND maturity_app --version)
  set_tests_properties(maturity_app.version PROPERTIES
    PASS_REGULAR_EXPRESSION "^maturity_app ${version_regex}\n$")
endif()
