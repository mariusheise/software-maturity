cmake_minimum_required(VERSION 3.23)
project(maturity VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(MATURITY_COVERAGE "Instrument for gcov/gcovr coverage" OFF)

add_library(maturity src/stats.cpp src/password.cpp)
target_include_directories(maturity PUBLIC include)
target_compile_options(maturity PRIVATE
  $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic -Werror>)

if(MATURITY_COVERAGE)
  target_compile_options(maturity PUBLIC --coverage -O0)
  target_link_options(maturity PUBLIC --coverage)
endif()

add_executable(maturity_app src/main.cpp)
target_link_libraries(maturity_app PRIVATE maturity)

include(CTest)
if(BUILD_TESTING)
  find_package(GTest REQUIRED)
  add_executable(maturity_tests tests/stats_test.cpp tests/password_test.cpp)
  target_link_libraries(maturity_tests PRIVATE maturity GTest::gtest_main)
  include(GoogleTest)
  gtest_discover_tests(maturity_tests)
endif()
