#include "maturity/stats.hpp"

#include <algorithm>
#include <numeric>

namespace maturity {

std::optional<double> mean(std::span<const double> values) {
  if (values.empty()) {
    return std::nullopt;
  }
  const double sum = std::accumulate(values.begin(), values.end(), 0.0);
  return sum / static_cast<double>(values.size());
}

double range(std::span<const double> values) {
  if (values.empty()) {
    return 0.0;
  }
  return std::ranges::max(values) - std::ranges::min(values);
}

}  // namespace maturity
