#include <array>
#include <iostream>

#include "maturity/stats.hpp"

int main() {
  const std::array<double, 4> values{1.0, 2.0, 3.0, 4.0};
  if (const auto m = maturity::mean(values)) {
    std::cout << "mean = " << *m << '\n';
  }
  return 0;
}
