# Copyright: 2025 by MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

from __future__ import annotations


def parse_bool(value: str) -> bool:
    value_ = value.lower()
    if value_ in ("true", "yes", "y", "on", "1"):
        return True
    if value_ in ("false", "no", "n", "off", "0"):
        return False
    raise ValueError(f"Not a boolean value: {value}")
