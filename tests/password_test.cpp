#include "maturity/password.hpp"

#include <gtest/gtest.h>

#include <string_view>

namespace {
// Dummy password for tests only. Secret scanners are told to ignore exactly this
// value in .betterleaks.toml and .gitleaks.toml; changes there need Code Owner review.
constexpr std::string_view kDummyPassword = "Tr0ub4dor&3xK9#mQ2vL";
}  // namespace

TEST(Password, AcceptsStrongPassword) { EXPECT_TRUE(maturity::is_strong_password(kDummyPassword)); }

TEST(Password, RejectsShortPassword) { EXPECT_FALSE(maturity::is_strong_password("Ab1!")); }

TEST(Password, RejectsPasswordMissingCharacterClasses) {
  EXPECT_FALSE(maturity::is_strong_password("alllowercaseletters"));
  EXPECT_FALSE(maturity::is_strong_password("NoDigitsOrSymbolsHere"));
}
