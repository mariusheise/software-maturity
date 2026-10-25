#include "maturity/stats.hpp"

#include <gtest/gtest.h>

#include <array>
#include <vector>

TEST(Mean, EmptyInputYieldsNullopt) {
  const std::vector<double> empty;
  EXPECT_FALSE(maturity::mean(empty).has_value());
}

TEST(Mean, SingleValue) {
  const std::array<double, 1> v{42.0};
  const auto m = maturity::mean(v);
  ASSERT_TRUE(m.has_value());
  EXPECT_DOUBLE_EQ(*m, 42.0);
}

TEST(Mean, MultipleValues) {
  const std::array<double, 4> v{1.0, 2.0, 3.0, 4.0};
  const auto m = maturity::mean(v);
  ASSERT_TRUE(m.has_value());
  EXPECT_DOUBLE_EQ(*m, 2.5);
}
