#include "maturity/stats.hpp"

#include <gtest/gtest.h>

#include <array>
#include <span>
#include <vector>

TEST(Mean, EmptyInputYieldsNullopt) {
  const std::vector<double> empty;
  EXPECT_FALSE(maturity::mean(empty).has_value());
}

TEST(Mean, SingleValue) {
  const std::array<double, 1> v{42.0};
  EXPECT_DOUBLE_EQ(maturity::mean(v).value(), 42.0);
}

TEST(Mean, MultipleValues) {
  const std::array<double, 4> v{1.0, 2.0, 3.0, 4.0};
  EXPECT_DOUBLE_EQ(maturity::mean(v).value(), 2.5);
}

TEST(Range, EmptyInputIsZero) {
  const std::span<const double> empty;
  EXPECT_DOUBLE_EQ(maturity::range(empty), 0.0);
}

TEST(Range, SpreadOfMultipleValues) {
  const std::array<double, 4> v{3.0, 9.0, 1.0, 4.0};
  EXPECT_DOUBLE_EQ(maturity::range(v), 8.0);
}
