#pragma once

#include <optional>
#include <span>

namespace maturity {

// Arithmetic mean; std::nullopt for an empty input.
std::optional<double> mean(std::span<const double> values);

}  // namespace maturity
