#include "maturity/password.hpp"

#include <algorithm>
#include <cctype>

namespace maturity {

namespace {
constexpr std::size_t kMinLength = 12;

template <typename Predicate>
bool contains(std::string_view s, Predicate pred) {
  return std::any_of(s.begin(), s.end(),
                     [&](char c) { return pred(static_cast<unsigned char>(c)); });
}
}  // namespace

bool is_strong_password(std::string_view password) {
  return password.size() >= kMinLength && contains(password, ::islower) &&
         contains(password, ::isupper) && contains(password, ::isdigit) &&
         contains(password, ::ispunct);
}

}  // namespace maturity
