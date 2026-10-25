#include <array>
#include <iostream>
#include <span>
#include <string_view>

#include "maturity/stats.hpp"
#include "maturity/version.hpp"

int main(int argc, char* argv[]) {
  const std::span args(argv, static_cast<std::size_t>(argc));
  if (args.size() == 2 && std::string_view(args[1]) == "--version") {
    std::cout << "maturity_app " << maturity::version << '\n';
    return 0;
  }
  const std::array<double, 4> values{1.0, 2.0, 3.0, 4.0};
  if (const auto m = maturity::mean(values)) {
    std::cout << "mean = " << *m << '\n';
  }
  return 0;
}
