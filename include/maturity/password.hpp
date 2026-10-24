#pragma once

#include <string_view>

namespace maturity {

// Strong means at least 12 characters with a lower-case letter, an upper-case
// letter, a digit and a symbol.
bool is_strong_password(std::string_view password);

}  // namespace maturity
