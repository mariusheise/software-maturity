#include "maturity/stats.hpp"

#include <numeric>

namespace maturity {

std::optional<double> mean(std::span<const double> values) {
  if (values.empty()) {
    return std::nullopt;
  }
  const double sum = std::accumulate(values.begin(), values.end(), 0.0);
  return sum / static_cast<double>(values.size());
}

}  // namespace maturity

namespace maturity {
int demo_uncovered(int x) {
  if (x > 0) {
    return x * 2;
  }
  return 0;
}
}  // namespace maturity
