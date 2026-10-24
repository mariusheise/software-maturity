#pragma once

#include <optional>
#include <span>

namespace maturity {

// Arithmetic mean; std::nullopt for an empty input.
std::optional<double> mean(std::span<const double> values);

// Spread between the largest and smallest value; 0 for an empty input.
double range(std::span<const double> values);

}  // namespace maturity
